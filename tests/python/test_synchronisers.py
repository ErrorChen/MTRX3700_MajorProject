"""Actual Quartus report excerpts and focused missing/wrong-stage counterexamples."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/lib"))
from synchronisers import expectedSynchronisers, validateSynchronisers


class SynchroniserReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = (ROOT / "tests/fixtures/quartus_sync_chains.txt").read_text()
        allHeads = expectedSynchronisers()
        cls.expected = {name: second for name, second in allHeads.items()
                        if name in cls.report}

    def testActualTwoAndThreeRegisterChains(self):
        result = validateSynchronisers(self.report, self.expected)
        self.assertEqual(result["coverageStatus"], "PASS", result["errors"])
        self.assertEqual(result["reportedChainCount"], 3)
        self.assertEqual({item["reportedChainLength"] for item in result["chains"]}, {2, 3})
        self.assertEqual(result["mtbfAcceptance"], "NOT_ASSESSED")

    def testMissingChainFailsEvenWithLargeMtbfHeadline(self):
        result = validateSynchronisers(self.report, expectedSynchronisers())
        self.assertEqual(result["coverageStatus"], "FAIL")
        self.assertEqual(len(result["errors"]), len(expectedSynchronisers()) - 3)

    def testWrongSecondStageAndAutomaticIdentificationFail(self):
        changed = self.report.replace("readGraySync[0]", "readGraySync[1]")
        result = validateSynchronisers(changed, self.expected)
        self.assertEqual(result["coverageStatus"], "FAIL")
        self.assertTrue(any("First two" in item for item in result["errors"]))
        changed = self.report.replace("User Specified", "Automatic")
        result = validateSynchronisers(changed, self.expected)
        self.assertEqual(result["coverageStatus"], "FAIL")
        self.assertEqual(len(result["errors"]), 3)


if __name__ == "__main__":
    unittest.main()
