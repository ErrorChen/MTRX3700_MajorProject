"""Host transaction/safety behaviour; mock sessions are never hardware evidence."""
import contextlib
import io
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import chassis_debug as client


class FakeSession:
    def __init__(self, selected=True, accepts_arm=True):
        self.events = []
        self.selected = selected
        self.accepts_arm = accepts_arm
        self.armed = False

    def status(self, maintain_lease=False):
        self.events.append(("status", maintain_lease))
        return {"mode": "CHASSIS_INJECT", "selection": "VALID" if self.selected else "NO_SELECTION",
                "sourceHealthyFresh": True, "distanceValid": True, "sonarHold": False,
                "irEstop": False, "fatal": False, "taskArmed": self.armed, "state": "IDLE"}

    def tx(self, op, value=0):
        self.events.append(("tx", op, value))
        if op == 3: self.armed = self.accepts_arm
        if op == 4: self.armed = False

    def observation(self, **values):
        self.events.append(("observation", values))


class TuningSession:
    """Protocol model only; RTL tests independently enforce the write boundary."""
    def __init__(self):
        self.events = []
        self.words = [0] * 16
        self.words[8] = 1 << 15
        self.words[10] = (0x2d << 26) | (client.policy_word(**client.POLICY_DEFAULTS) << 9)
        self.words[13] = 0xa1000000 | client.tuning_word(**client.TUNING_DEFAULTS)
        self.words[15] = 1 | (1 << 29) | (0xa2 << 20) | (client.pulse_word(**client.PULSE_DEFAULTS) << 2)

    def __enter__(self): return self
    def __exit__(self, *_): pass

    def status(self, maintain_lease=False):
        self.events.append(("status", maintain_lease))
        return client.decode_status(self.words)

    def tx(self, op, value=0):
        self.events.append(("tx", op, value))
        if op == 11:
            if (self.words[13] & 15) != (value & 15): self.words[15] &= ~(1 << 29)
            self.words[13] = 0xa1000000 | value
        elif op == 12:
            self.words[15] = (self.words[15] & 0xf0000003) | (0xa2 << 20) | (value << 2)
        elif op == 13:
            self.words[10] = (self.words[10] & 0x1ff) | (0x2d << 26) | (value << 9)
        else:
            raise AssertionError("tuning must never send mode/ARM/lease commands")


class ChassisToolsTests(unittest.TestCase):
    def test_chassis_init_capability_is_local_and_backward_compatible(self):
        words = [0] * 16
        for unsupported in (0, 1 << 8):
            words[10] = unsupported
            state = client.decode_status(words)
            self.assertFalse(state["chassisInitSupported"])
            self.assertIsNone(state["chassisInitSent"])
        words[10] = (1 << 7) | (1 << 5) | (1 << 6)
        state = client.decode_status(words)
        self.assertTrue(state["chassisInitSupported"])
        self.assertFalse(state["chassisInitSent"])
        self.assertTrue(state["fatal"] and state["pendingVisualStart"])
        words[10] |= 1 << 8
        self.assertTrue(client.decode_status(words)["chassisInitSent"])

    def test_tuning_word_limits_and_capability_decode(self):
        self.assertEqual(client.tuning_word(**client.TUNING_DEFAULTS), 0x001e3544)
        for changes in ({"search": 2}, {"turn": 6}, {"approach": 9}, {"fine": 2},
                        {"tolerance": 41}, {"tolerance": 9}, {"fine": 4, "approach": 4},
                        {"search": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                client.tuning_word(**(client.TUNING_DEFAULTS | changes))
        state = TuningSession().status()
        self.assertTrue(state["tuningSupported"])
        self.assertEqual(state["tuning"], client.TUNING_DEFAULTS)
        self.assertFalse(client.decode_status([0] * 16)["tuningSupported"])

    def test_tuning_read_only_and_old_firmware_never_write(self):
        session = TuningSession()
        client.tune(session)
        self.assertEqual(session.events, [("status", False)])
        session.words[13] = 0
        with self.assertRaisesRegex(RuntimeError, "does not support"):
            client.tune(session, search=3)
        self.assertFalse(any(event[0] == "tx" for event in session.events))

    def test_tuning_atomically_merges_fields_and_retains_safety(self):
        session = TuningSession()
        session.words[0] = (1 << 29) | (1 << 30)
        session.words[11] = 4
        state = client.tune(session, turn=5, tolerance=40)
        expected = client.TUNING_DEFAULTS | {"turn": 5, "tolerance": 40}
        self.assertEqual(state["tuning"], expected)
        self.assertEqual(session.events, [("status", False), ("tx", 11, client.tuning_word(**expected)),
                                          ("status", False)])
        self.assertTrue(state["irEstop"] and state["sonarHold"] and state["colourCalibrated"])
        self.assertTrue(state["scanCalibrated"])
        self.assertFalse(client.tune(session, search=3)["scanCalibrated"])
        self.assertEqual(client.tune(session, defaults=True)["tuning"], client.TUNING_DEFAULTS)

    def test_tuning_rejects_each_nonstationary_boundary(self):
        for index, value in ((15, 0), (15, 2), (0, 1 << 20), (0, 1 << 28),
                             (7, 3), (7, 125 << 8), (8, 0)):
            session = TuningSession()
            session.words[index] = value
            with self.subTest(index=index, value=value), self.assertRaisesRegex(RuntimeError, "requires VISION_ONLY"):
                client.tune(session, search=3)
            self.assertFalse(any(event[0] == "tx" for event in session.events))

    def test_tuning_readback_is_checked_not_just_ack(self):
        session = TuningSession()
        with patch.object(session, "tx"), self.assertRaisesRegex(RuntimeError, "readback mismatch"):
            client.tune(session, search=3)
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            client.tune(session, defaults=True, turn=3)

    def test_tuning_cli_routes_one_transaction_and_rejects_bad_input_before_jtag(self):
        for args in (("tune", "--search", "2"), ("tune", "--defaults", "--turn", "3")):
            with patch.object(client, "Session") as factory, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(client.main(args), 1)
                factory.assert_not_called()
        session = TuningSession()
        with patch.object(client, "Session", return_value=session), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client.main(["tune", "--search", "3", "--tolerance", "35"]), 0)
        self.assertEqual([event[1] for event in session.events if event[0] == "tx"], [11])

    def test_pulse_encoding_limits_units_and_capability_preserve_old_fields(self):
        self.assertEqual(client.pulse_word(**client.PULSE_DEFAULTS), 0x00015420)
        for changes in ({"min_ms": 10}, {"min_ms": 21}, {"max_ms": 310}, {"max_ms": 99},
                        {"min_ms": 110}, {"kick_ms": -10}, {"kick_ms": 110}, {"kick_ms": 1},
                        {"kick_speed": 2}, {"kick_speed": 9}, {"kick_ms": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                client.pulse_word(**(client.PULSE_DEFAULTS | changes))
        # A kick longer than the total is legal: RTL clips it to that total.
        self.assertEqual(client.pulse_word(min_ms=20, max_ms=20, kick_ms=100, kick_speed=8), 0x2042a)
        state = TuningSession().status()
        self.assertEqual(state["alignTiming"], {"minMs": 20, "maxMs": 100, "kickMs": 0, "kickSpeed": 5})
        self.assertTrue(state["alignTimingSupported"] and state["scanCalibrated"])
        self.assertEqual(state["mode"], "VISION_ONLY")
        self.assertEqual(state["tuning"], client.TUNING_DEFAULTS)

    def test_pulse_read_only_and_old_or_unknown_capability_never_write(self):
        session = TuningSession()
        client.pulse(session)
        self.assertEqual(session.events, [("status", False)])
        for cap in (0, 0xa3):
            session = TuningSession()
            session.words[15] = (session.words[15] & 0xf0000003) | (cap << 20)
            self.assertFalse(session.status()["alignTimingSupported"])
            with self.assertRaisesRegex(RuntimeError, "does not support"):
                client.pulse(session, kick_ms=60)
            self.assertFalse(any(event[0] == "tx" for event in session.events))
            # E11's speed protocol remains available even without pulse support.
            self.assertEqual(client.tune(session, turn=5)["tuning"]["turn"], 5)

    def test_pulse_atomic_partial_merge_defaults_and_independent_settings(self):
        session = TuningSession()
        session.words[0] = (1 << 29) | (1 << 30)
        session.words[6] = 15100000
        session.words[11] = 4
        session.words[15] |= 1 << 28
        state = client.pulse(session, kick_ms=60, kick_speed=4, max_ms=200)
        expected = client.PULSE_DEFAULTS | {"kick_ms": 60, "kick_speed": 4, "max_ms": 200}
        self.assertEqual(session.events, [("status", False), ("tx", 12, client.pulse_word(**expected)),
                                          ("status", False)])
        self.assertEqual(state["alignTiming"], {"minMs": 20, "maxMs": 200, "kickMs": 60, "kickSpeed": 4})
        self.assertTrue(state["irEstop"] and state["sonarHold"] and state["colourCalibrated"] and state["framesEnabled"])
        self.assertTrue(state["scanCalibrated"])
        self.assertEqual(state["scanBudgetUs"], 15100000)
        self.assertEqual(state["tuning"], client.TUNING_DEFAULTS)
        # Changing speeds must not rewrite the independently stored pulse word.
        self.assertEqual(client.tune(session, turn=3)["alignTiming"], state["alignTiming"])
        self.assertEqual(client.pulse(session, defaults=True)["alignTiming"],
                         {"minMs": 20, "maxMs": 100, "kickMs": 0, "kickSpeed": 5})

    def test_pulse_rejects_every_nonstationary_boundary_without_write(self):
        for index, value in ((15, 0), (15, 2), (0, 1 << 20), (0, 1 << 28),
                             (7, 3), (7, 125 << 8), (8, 0)):
            session = TuningSession()
            session.words[index] = ((session.words[15] & ~3) | value) if index == 15 else value
            with self.subTest(index=index, value=value), self.assertRaisesRegex(RuntimeError, "requires VISION_ONLY"):
                client.pulse(session, max_ms=200)
            self.assertFalse(any(event[0] == "tx" for event in session.events))

    def test_pulse_readback_and_unrelated_settings_are_verified_after_ack(self):
        session = TuningSession()
        with patch.object(session, "tx"), self.assertRaisesRegex(RuntimeError, "readback mismatch"):
            client.pulse(session, kick_ms=50)
        original = session.tx
        def corrupt_scan(op, value):
            original(op, value)
            session.words[6] += 1
        with patch.object(session, "tx", side_effect=corrupt_scan), self.assertRaisesRegex(RuntimeError, "unrelated"):
            client.pulse(session, kick_ms=50)
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            client.pulse(session, defaults=True, max_ms=200)

    def test_pulse_cli_rejects_bad_inputs_before_jtag_and_routes_only_opcode12(self):
        for args in (("pulse", "--kick-ms", "1"), ("pulse", "--max-ms", "301"),
                     ("pulse", "--min-ms", "200", "--max-ms", "100"),
                     ("pulse", "--kick-speed", "9"), ("pulse", "--defaults", "--kick-ms", "0")):
            with patch.object(client, "Session") as factory, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(client.main(args), 1)
                factory.assert_not_called()
        session = TuningSession()
        with patch.object(client, "Session", return_value=session), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client.main(["pulse", "--min-ms", "80", "--max-ms", "200",
                                          "--kick-ms", "60", "--kick-speed", "4"]), 0)
        self.assertEqual([event[1] for event in session.events if event[0] == "tx"], [12])

    def test_policy_word_units_limits_and_status_preserve_low_flags(self):
        self.assertEqual(client.policy_word(**client.POLICY_DEFAULTS), 0xaf9)
        values = {"corridor_px": 70, "settle_ms": 2000, "stop_mm": 400, "slow_mm": 1000}
        payload = client.policy_word(**values)
        self.assertEqual(payload, 14 | (20 << 4) | (10 << 9) | (10 << 13))
        self.assertLess(payload, 1 << 17)
        session = TuningSession()
        session.words[10] = (0x2d << 26) | (payload << 9) | 0x1ff
        state = session.status()
        self.assertEqual(state["motionPolicy"], {"corridorPx": 70, "settleMs": 2000,
                                                 "stopMm": 400, "slowMm": 1000})
        self.assertTrue(state["fatal"] and state["pendingVisualStart"] and
                        state["chassisInitSupported"] and state["chassisInitSent"])
        for changes in ({"corridor_px": 40}, {"corridor_px": 46}, {"corridor_px": 75},
                        {"settle_ms": 400}, {"settle_ms": 550}, {"settle_ms": 2100},
                        {"stop_mm": 290}, {"stop_mm": 355}, {"stop_mm": 410},
                        {"slow_mm": 450}, {"slow_mm": 525}, {"slow_mm": 1050},
                        {"corridor_px": True}, {"stop_mm": 350.0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                client.policy_word(**(client.POLICY_DEFAULTS | changes))
        with self.assertRaises(ValueError): client.policy_word(corridor_px=45)

    def test_policy_read_only_and_old_or_unknown_magic_never_write(self):
        session = TuningSession()
        state = client.policy(session)
        self.assertTrue(state["motionPolicySupported"])
        self.assertEqual(session.events, [("status", False)])
        for magic in (0, 0x2c, 0x2e, 0x3f):
            session = TuningSession()
            session.words[10] = (magic << 26) | (0xaf9 << 9) | 0x1ff
            state = client.policy(session)
            self.assertFalse(state["motionPolicySupported"])
            self.assertIsNone(state["motionPolicy"])
            with self.assertRaisesRegex(RuntimeError, "does not support"):
                client.policy(session, corridor_px=55)
            self.assertFalse(any(event[0] == "tx" for event in session.events))

    def test_policy_merges_actual_values_atomically_and_preserves_other_settings(self):
        session = TuningSession()
        initial = {"corridor_px": 50, "settle_ms": 1200, "stop_mm": 330, "slow_mm": 700}
        session.words[10] = (0x2d << 26) | (client.policy_word(**initial) << 9) | 0x1ff
        session.words[0] = (1 << 29) | (1 << 30)
        session.words[6] = 15100000
        session.words[11] = 4
        before = session.words.copy()
        state = client.policy(session, corridor_px=60, stop_mm=360)
        expected = initial | {"corridor_px": 60, "stop_mm": 360}
        self.assertEqual(session.events, [("status", False), ("tx", 13, client.policy_word(**expected)),
                                         ("status", False)])
        self.assertEqual(state["motionPolicy"], {"corridorPx": 60, "settleMs": 1200,
                                                 "stopMm": 360, "slowMm": 700})
        self.assertEqual(session.words[10] & 0x1ff, 0x1ff)
        self.assertEqual(session.words[:10] + session.words[11:], before[:10] + before[11:])
        self.assertTrue(state["irEstop"] and state["sonarHold"] and state["colourCalibrated"])
        self.assertEqual(client.tune(session, turn=3)["motionPolicy"], state["motionPolicy"])
        self.assertEqual(client.pulse(session, kick_ms=60)["motionPolicy"], state["motionPolicy"])
        self.assertEqual(client.policy(session, defaults=True)["motionPolicy"],
                         {"corridorPx": 45, "settleMs": 1500, "stopMm": 350, "slowMm": 500})

    def test_policy_rejects_every_nonstationary_boundary_without_write(self):
        for index, value in ((15, 0), (15, 2), (0, 1 << 20), (0, 1 << 28),
                             (7, 3), (7, 125 << 8), (8, 0)):
            session = TuningSession()
            session.words[index] = ((session.words[15] & ~3) | value) if index == 15 else value
            with self.subTest(index=index, value=value), self.assertRaisesRegex(RuntimeError, "requires VISION_ONLY"):
                client.policy(session, corridor_px=55)
            self.assertFalse(any(event[0] == "tx" for event in session.events))

    def test_policy_verifies_readback_stationary_boundary_and_unrelated_settings(self):
        session = TuningSession()
        with patch.object(session, "tx"), self.assertRaisesRegex(RuntimeError, "readback mismatch"):
            client.policy(session, corridor_px=55)
        for index, mask in ((6, 1), (13, 1 << 4), (15, 1 << 29), (15, 1 << 6)):
            session = TuningSession()
            original = session.tx
            def corrupt_other(op, value):
                original(op, value)
                session.words[index] ^= mask
            with self.subTest(index=index, mask=mask), patch.object(session, "tx", side_effect=corrupt_other), \
                    self.assertRaisesRegex(RuntimeError, "unrelated"):
                client.policy(session, corridor_px=55)
        session = TuningSession()
        original = session.tx
        def arm_after_ack(op, value):
            original(op, value)
            session.words[0] |= 1 << 20
        with patch.object(session, "tx", side_effect=arm_after_ack), \
                self.assertRaisesRegex(RuntimeError, "stationary boundary changed"):
            client.policy(session, corridor_px=55)
        self.assertEqual([event[1] for event in session.events if event[0] == "tx"], [13])

    def test_policy_cli_and_api_reject_invalid_inputs_before_any_jtag(self):
        for changes in ({"corridor_px": 46}, {"settle_ms": 550}, {"stop_mm": 355},
                        {"slow_mm": 1050}, {"unknown": 1}, {"corridor_px": True}):
            session = TuningSession()
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                client.policy(session, **changes)
            self.assertEqual(session.events, [])
        session = TuningSession()
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            client.policy(session, defaults=True, stop_mm=350)
        self.assertEqual(session.events, [])
        for args in (("policy", "--corridor-px", "46"), ("policy", "--settle-ms", "550"),
                     ("policy", "--stop-mm", "410"), ("policy", "--slow-mm", "525"),
                     ("policy", "--defaults", "--corridor-px", "45")):
            with patch.object(client, "Session") as factory, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(client.main(args), 1)
                factory.assert_not_called()
        session = TuningSession()
        with patch.object(client, "Session", return_value=session), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client.main(["policy", "--corridor-px", "55", "--settle-ms", "1700",
                                         "--stop-mm", "360", "--slow-mm", "650"]), 0)
        self.assertEqual([event[1:] for event in session.events if event[0] == "tx"],
                         [(13, client.policy_word(corridor_px=55, settle_ms=1700, stop_mm=360, slow_mm=650))])

    def test_no_target_search_uses_current_budget_plus_final_dwell_margin(self):
        self.assertEqual(client.no_target_search_rows({"scanBudgetUs": 10000000}),
                         [{"visible": False, "hold": 13.0}])
        self.assertEqual(client.no_target_search_rows({"scanBudgetUs": 120000000})[0]["hold"], 123)
        with self.assertRaises(ValueError): client.no_target_search_rows({"scanBudgetUs": 0})

    def test_injection_records_state_while_renewing_in_the_same_session(self):
        session = FakeSession()
        now = [0.0]
        def sleep(seconds): now[0] += seconds
        output = io.StringIO()
        with patch.object(client.time, "monotonic", side_effect=lambda: now[0]), \
                patch.object(client.time, "sleep", side_effect=sleep), \
                contextlib.redirect_stdout(output):
            client.inject(session, [{"visible": False, "hold": 0.25}], True)
        self.assertGreaterEqual(session.events.count(("status", True)), 5)
        self.assertIn('"state": {', output.getvalue())
        self.assertEqual(session.events[-1], ("tx", 4, 0))

    def test_observe_retains_held_bad_unlocked_and_separate_frames_without_writes(self):
        class ReadOnly:
            def __init__(self): self.events = []
            def status(self):
                self.events.append("STATUS")
                return {"mode": "VISION_ONLY", "digit": 2, "frameId": 5,
                        "requestTag": 9, "configVersion": 1, "sourceHealthyFresh": False,
                        "targetLockedFresh": False}
            def bstatus(self):
                self.events.append("BSTATUS")
                return {"buildId": 0xE7070004, "frameId": 8, "configVersion": 1,
                        "captureStartUs": 40000, "frameGood": False, "bypassPerspective": False,
                        "redMinimum": 41, "blueMinimum": 37}
        client.echo7.WORK.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=client.echo7.WORK) as directory:
            path = Path(directory) / "observation.json"
            session = ReadOnly()
            with contextlib.redirect_stdout(io.StringIO()):
                client.observe(session, path, "synthetic host test", samples=3, interval=0)
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(session.events, ["STATUS", "BSTATUS"] * 3)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["summary"]["completePairs"], 3)
            self.assertEqual(result["summary"]["bctlDistinctFrames"], 1)
            self.assertEqual(result["summary"]["bctlBadFrameSamples"], 3)
            self.assertEqual(result["summary"]["cctlLockedSamples"], 0)
            self.assertEqual(result["samples"][0]["cctl"]["state"]["frameId"], 5)
            self.assertEqual(result["samples"][0]["bctl"]["state"]["frameId"], 8)
            self.assertLessEqual(result["samples"][0]["cctl"]["readEndSeconds"],
                                 result["samples"][0]["bctl"]["readStartSeconds"])

    def test_observe_transport_failure_keeps_partial_cctl_sample(self):
        class Partial:
            def status(self):
                return {"mode": "VISION_ONLY", "digit": 1, "frameId": 5}
            def bstatus(self): raise RuntimeError("BCTL failed")
        client.echo7.WORK.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=client.echo7.WORK) as directory:
            path = Path(directory) / "partial.json"
            with self.assertRaisesRegex(RuntimeError, "BCTL failed"):
                client.observe(Partial(), path, "synthetic partial", samples=1)
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["summary"]["completePairs"], 0)
            self.assertEqual(result["samples"][0]["cctl"]["state"]["frameId"], 5)

    def test_persistent_file_replies_work_before_buffered_stdout_closes(self):
        # A real subprocess models Quartus's buffered stdout. The session must
        # receive READY/command replies while that process remains alive.
        peer = '''import pathlib,sys
print("BUFFERED_NATIVE_BANNER")
with pathlib.Path(sys.argv[1]).open("w", encoding="utf-8") as responses:
    responses.write("CCTL_READY\\tfake\\tfake\\n"); responses.flush()
    for line in sys.stdin:
        serial, operation, *values = line.strip().split("\\t")
        responses.write("CCTL_OK\\t" + serial + "\\t" + operation + "\\n"); responses.flush()
        if operation == "QUIT": break
'''
        actual_popen = subprocess.Popen
        commands = []
        def start_peer(command, **options):
            commands.append(command)
            return actual_popen([sys.executable, "-c", peer, command[-1]], **options)
        args = argparse.Namespace(quartus_bin=None, cable=None, device=None, timeout=3)
        client.echo7.WORK.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="transport_test_", dir=client.echo7.WORK) as directory, \
                patch.object(client.echo7, "WORK", Path(directory)), \
                patch.object(client.echo7, "discover", return_value=sys.executable), \
                patch.object(client.echo7, "quartusEnvironment", return_value=os.environ.copy()), \
                patch.object(client.subprocess, "Popen", side_effect=start_peer), \
                contextlib.redirect_stdout(io.StringIO()):
            session = client.Session(args)
            with session:
                process = session.process
                self.assertIsNone(process.poll())
                self.assertEqual(session.call("STATUS"), "STATUS")
                self.assertEqual(session.call("BSTATUS"), "BSTATUS")
                self.assertEqual(commands[0][-3:-1], ["AUTO", "AUTO"])
            self.assertEqual(process.returncode, 0)
            self.assertFalse(session.responseThread.is_alive())

    def test_out_of_range_is_rejected_before_jtag(self):
        for values in ({"x": 240}, {"x": -1}, {"y": 320}, {"quality": 256}, {"width": 0}):
            with self.assertRaises(ValueError): client.observation_words(**values)

    def test_selected_template_and_live_status_precede_start(self):
        session = FakeSession()
        with contextlib.redirect_stdout(io.StringIO()):
            client.inject(session, [{"x": 80, "hold": 0}], True)
        ops = session.events
        start = ops.index(("tx", 3, 0))
        self.assertTrue(any(item[0] == "observation" for item in ops[:start]))
        self.assertIn(("status", True), ops[:start])
        self.assertIn(("status", True), ops[start+1:])
        self.assertEqual(ops[-1], ("tx", 4, 0))
        self.assertFalse(session.armed)

    def test_invalid_physical_selection_never_arms_and_still_stops(self):
        session = FakeSession(selected=False)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "physical SW"):
            client.inject(session, [{"hold": 0}], True)
        self.assertNotIn(("tx", 3, 0), session.events)
        self.assertEqual(session.events[-1], ("tx", 4, 0))

    def test_ack_is_not_reported_as_actual_arm(self):
        session = FakeSession(accepts_arm=False)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "did not arm"):
            client.inject(session, [{"hold": 0}], True)
        self.assertEqual(session.events[-1], ("tx", 4, 0))

    def test_no_arm_option_never_sends_start(self):
        session = FakeSession()
        with contextlib.redirect_stdout(io.StringIO()):
            client.inject(session, [{"hold": 0}], False)
        self.assertNotIn(("tx", 3, 0), session.events)

    def test_status_preserves_real_safety_and_signed_wheel_fields(self):
        words = [0] * 16
        words[0] = (1 << 15) | (1 << 29) | (1 << 30)
        words[7] = 124 | (4 << 8)
        words[8] = 245 | (1 << 12)
        words[12] = 19 | (125 << 16) | (1 << 24)
        words[15] = 2 | (1 << 31)
        state = client.decode_status(words)
        self.assertEqual(state["mode"], "CHASSIS_INJECT")
        self.assertEqual(state["selection"], "SELECTION_CONFLICT")
        self.assertEqual((state["leftCmS"], state["rightCmS"]), (-4, 4))
        self.assertTrue(state["irEstop"] and state["sonarHold"] and state["distanceValid"])
        self.assertEqual(state["chassisRxCount"], 19)

    def test_far_sentinel_never_relabels_invalid_sonar_as_clear(self):
        words = [0] * 16
        words[8] = 4000
        invalid = client.decode_status(words)
        self.assertEqual(invalid["distanceKind"], "INVALID")
        self.assertFalse(invalid["distanceFar"])
        words[8] |= 1 << 12
        far = client.decode_status(words)
        self.assertEqual(far["distanceKind"], "FAR")
        self.assertTrue(far["distanceValid"] and far["distanceFar"])
        self.assertEqual(far["distanceMm"], 4000)
        words[8] = 350 | (1 << 12)
        measured = client.decode_status(words)
        self.assertEqual(measured["distanceKind"], "MEASURED")
        self.assertFalse(measured["distanceFar"])


if __name__ == "__main__": unittest.main()
