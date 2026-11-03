"""Host orchestration tests with synthetic observations; no board is contacted."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib"), str(ROOT / "tests/python")]
import echo7
from hardware_measurement import measureTrials
from test_duplicate_scene import DuplicateRunner, truthFixture
from test_hardware_measurement import FixtureRunner


class AutodebugTests(unittest.TestCase):
    def runPipeline(self, folder, arguments, failStage=None, duplicateFault=None):
        """Exercise real CLI/dispatch/assessor with mocked build/JTAG boundaries.

        The fake transport produces complete synthetic records. Keep both the
        CLI JSON and the assessor's failed observations so a nonzero exit cannot
        conceal a denominator change. Nothing here proves camera recognition.
        """
        calls = []

        def stage(name):
            def invoke(runner):
                calls.append(name)
                runner.result.setdefault("syntheticStages", []).append(name)
                if failStage == name:
                    raise RuntimeError("synthetic " + name + " failure")
            return invoke

        def liveTrials(runner, trials, buildId):
            calls.append("hardware")
            self.assertEqual(buildId, "12345678")
            if runner.args.truth_regions:
                # Preserve the declared path, including spaces, through CLI,
                # hardware dispatch and the unmodified scoring implementation.
                fixture = DuplicateRunner(runner.out, fault=duplicateFault, uniqueAcquire=True)
            else:
                fixture = FixtureRunner(runner.out)
            fixture.args = runner.args
            fixture.result = runner.result
            try:
                measureTrials(fixture, trials)
            finally:
                runner.result["level"] = "HOST_MOCK_ONLY"
                runner.result["inputSource"] = "SYNTHETIC_STATUS_FIXTURES"
                runner.result["syntheticTransportCleared"] = fixture.cleared

        output = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(echo7, "WORK", Path(folder) / "runs"))
            stack.enter_context(patch.object(echo7, "sourceIdentity", return_value={"buildId": "12345678"}))
            for name in ("replay", "rtl", "build", "program", "capture"):
                stack.enter_context(patch.object(echo7.Runner, name, stage(name)))
            stack.enter_context(patch("trial_stream.measureLiveTrials", side_effect=liveTrials))
            stack.enter_context(redirect_stdout(output))
            code = echo7.main(arguments)
        result = json.loads(output.getvalue())
        persisted = json.loads((Path(result["outputDirectory"]) / "result.json").read_text())
        self.assertEqual(result, persisted)
        return code, result, calls

    def testDefaultUsesOneCompleteTrialAndEightSignScene(self):
        with tempfile.TemporaryDirectory() as folder:
            code, result, calls = self.runPipeline(folder, ["autodebug"])
            self.assertEqual(code, 0)
            self.assertEqual(calls, ["replay", "rtl", "build", "program", "capture", "hardware"])
            self.assertEqual(len(result["observations"]), 30)
            self.assertEqual(result["expectedScene"]["printedRegionCount"], 8)
            self.assertEqual(len(result["trials"]), 1)
            self.assertTrue(result["syntheticTransportCleared"])

    def testDuplicateTruthAndThreeTrialsReachTheSameAssessor(self):
        with tempfile.TemporaryDirectory() as folder:
            truthPath = Path(folder) / "declared duplicate signs.json"
            truthPath.write_text(json.dumps(truthFixture()))
            code, result, calls = self.runPipeline(folder, ["--timeout", "10", "autodebug",
                "--trials", "3", "--truth-regions", str(truthPath)])
            self.assertEqual(code, 0)
            self.assertEqual(calls[-1], "hardware")
            self.assertEqual(result["truthRegions"]["path"], str(truthPath))
            self.assertEqual(len(result["observations"]), 90)
            self.assertEqual(result["expectedScene"]["blueMatchesByBay"],
                             {"1": 2, "2": 2, "3": 1, "4": 1, "5": 1, "6": 1})
            self.assertEqual([trial["printedDigitScore"]["correct"] for trial in result["trials"]], [300] * 3)
            self.assertEqual([trial["expectedAmbiguousSamples"] for trial in result["trials"]], [10] * 3)

    def testBadDuplicateObservationIsRetainedAndReturnsNonzero(self):
        def fault(state, frame, bay):
            if frame == 2:
                state["targetReport"].update(observed=True, locked=True, ambiguous=False, reason=0)
        with tempfile.TemporaryDirectory() as folder:
            truthPath = Path(folder) / "truth.json"
            truthPath.write_text(json.dumps(truthFixture()))
            code, result, _ = self.runPipeline(folder, ["autodebug", "--trials", "1",
                "--truth-regions", str(truthPath)], duplicateFault=fault)
            self.assertEqual(code, 1)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["exitCode"], 1)
            self.assertEqual(len(result["observations"]), 30)
            self.assertIn("expected_target_ambiguity", result["observations"][0]["issues"])
            self.assertTrue(result["syntheticTransportCleared"])
            retained = json.loads((Path(result["outputDirectory"]) / "trial_observations.json").read_text())
            self.assertEqual(retained, result["observations"])

    def testEarlierFailureStopsBeforeProgrammingOrMeasurement(self):
        with tempfile.TemporaryDirectory() as folder:
            code, result, calls = self.runPipeline(folder, ["autodebug", "--trials", "3"], failStage="build")
            self.assertEqual(code, 1)
            self.assertEqual(calls, ["replay", "rtl", "build"])
            self.assertEqual(result["reason"], "synthetic build failure")
            self.assertNotIn("observations", result)

    def testStandaloneHardwareRetainsTheSameTrialOption(self):
        with tempfile.TemporaryDirectory() as folder:
            code, result, calls = self.runPipeline(folder, ["test", "--hardware", "--trials", "2"])
            self.assertEqual(code, 0)
            self.assertEqual(calls, ["hardware"])
            self.assertEqual(len(result["observations"]), 60)

    def testInvalidOptionsFailBeforeCreatingARunner(self):
        cases = [
            ["autodebug", "--trials", "0"],
            ["autodebug", "--trials", "4"],
            ["autodebug", "--truth-regions", "truth.json"],
            ["test", "--hardware", "--truth-regions", "truth.json"],
            ["test", "--replay", "--trials", "1"],
            ["test", "--rtl", "--trials", "1", "--truth-regions", "truth.json"],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), patch.object(echo7, "Runner") as runner, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    echo7.main(arguments)
                self.assertEqual(error.exception.code, 2)
                runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
