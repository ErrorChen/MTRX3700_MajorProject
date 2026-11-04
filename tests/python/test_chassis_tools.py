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
        self.words[13] = 0xa1000000 | client.tuning_word(**client.TUNING_DEFAULTS)
        self.words[15] = 1 | (1 << 29)

    def __enter__(self): return self
    def __exit__(self, *_): pass

    def status(self, maintain_lease=False):
        self.events.append(("status", maintain_lease))
        return client.decode_status(self.words)

    def tx(self, op, value=0):
        self.events.append(("tx", op, value))
        if op != 11: raise AssertionError("tuning must never send mode/ARM/lease commands")
        if (self.words[13] & 15) != (value & 15): self.words[15] &= ~(1 << 29)
        self.words[13] = 0xa1000000 | value


class ChassisToolsTests(unittest.TestCase):
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
