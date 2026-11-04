"""Obsolete automatic target-owner trials must not run on the integrated top.

Historical scoring/duplicate/failure retention remains covered independently in
test_hardware_measurement.py and test_duplicate_scene.py. No board is contacted.
"""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib")]
import echo7


class AutodebugTests(unittest.TestCase):
    def test_legacy_hardware_and_autodebug_stop_before_any_board_or_build_action(self):
        cases = [["test", "--hardware"], ["test", "--hardware", "--trials", "3"],
                 ["autodebug"], ["autodebug", "--trials", "3", "--truth-regions", "unused.json"]]
        echo7.WORK.mkdir(parents=True, exist_ok=True)
        for arguments in cases:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory(dir=echo7.WORK) as folder:
                output = io.StringIO()
                with ExitStack() as stack:
                    stack.enter_context(patch.object(echo7, "WORK", Path(folder)))
                    actions = [stack.enter_context(patch.object(echo7.Runner, name)) for name in
                               ("replay", "rtl", "build", "program", "capture", "target", "control", "run")]
                    stack.enter_context(redirect_stdout(output))
                    code = echo7.main(arguments)
                result = json.loads(output.getvalue())
                self.assertEqual(code, 2)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn("physical SW0-SW5", result["reason"])
                self.assertIn("chassis_debug.py observe", result["reason"])
                self.assertNotIn("observations", result)
                for action in actions: action.assert_not_called()

    def test_invalid_options_fail_before_creating_runner(self):
        cases = [["autodebug", "--trials", "0"], ["autodebug", "--trials", "4"],
                 ["autodebug", "--truth-regions", "truth.json"],
                 ["test", "--hardware", "--truth-regions", "truth.json"],
                 ["test", "--replay", "--trials", "1"],
                 ["test", "--rtl", "--trials", "1", "--truth-regions", "truth.json"]]
        for arguments in cases:
            with self.subTest(arguments=arguments), patch.object(echo7, "Runner") as runner, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error: echo7.main(arguments)
                self.assertEqual(error.exception.code, 2)
                runner.assert_not_called()


if __name__ == "__main__": unittest.main()
