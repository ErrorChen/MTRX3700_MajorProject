"""Synthetic protocol faults only; these fixtures are not camera evidence."""
import argparse
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/lib"))
from trial_stream import parseTrialStream, TrialRecordReader

BUILD = 0x12345678


def record(serial=0, phase="INITIAL", trial=0, bay=0, actionMeta=0x04028060):
    words = [0] * 96
    words[0], words[1], words[92], words[93] = 0x45425031, 0x00040002, BUILD, (8 << 16) | (12 << 8)
    lines = [f"ECHO7_TRIAL_BEGIN\t{serial}\t{phase}\t{trial}\t{bay}"]
    if phase in ("SELECT", "CLEAR"):
        opcode = 1 if phase == "SELECT" else 2
        lines += [f"ECHO7_TRIAL_ACTION\t{serial}\t{opcode}\t{actionMeta:032b}"]
    lines += [f"ECHO7_TRIAL_HEADER\t{serial}\t{0x42444247:032b}{BUILD:032b}{0x04028060:032b}"]
    lines += [f"ECHO7_TRIAL_WORD\t{serial}\t{i}\t{word:032b}" for i, word in enumerate(words)]
    lines += [f"ECHO7_TRIAL_END\t{serial}"]
    return "\n".join(lines) + "\n"


class TrialStreamTests(unittest.TestCase):
    def testCompleteWordsAndRejectedDataAreNotFiltered(self):
        text = record() + record(1, "SELECT", 1, 1) + record(2, "STATUS", 1, 1) + record(3, "CLEAR")
        rows, done = parseTrialStream(text + "ECHO7_TRIAL_DONE\t1\t1\t2500\n", BUILD)
        self.assertEqual(len(rows), 4)
        self.assertFalse(rows[2]["decoded"]["frameGood"])
        self.assertEqual(done["elapsedMs"], 2500)
        fixture = argparse.Namespace(args=argparse.Namespace(timeout=10), out=Path("."), result={})
        reader = TrialRecordReader(fixture, rows)
        for command in (0, (1 << 24) | 1, 0, 2 << 24):
            reader.control(command)
        self.assertEqual(reader.position, 4)

    def testMissingReorderedAndDuplicateWordsFail(self):
        text = record()
        line = next(line for line in text.splitlines() if line.startswith("ECHO7_TRIAL_WORD\t0\t10\t"))
        for broken in (text.replace(line + "\n", ""), text.replace(line, line + "\n" + line),
                       text.replace("ECHO7_TRIAL_WORD\t0\t10\t", "ECHO7_TRIAL_WORD\t0\t11\t")):
            with self.subTest(broken=broken[-40:]), self.assertRaises(ValueError):
                parseTrialStream(broken, BUILD)

    def testOldBuildAndRejectedActionsFail(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            parseTrialStream(record(), BUILD + 1)
        with self.assertRaisesRegex(ValueError, "rejected"):
            parseTrialStream(record(0, "SELECT", 1, 1, 0x0402e060), BUILD)

    def testIncompleteTransactionCannotPretendComplete(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            parseTrialStream(record().replace("ECHO7_TRIAL_END\t0\n", ""), BUILD)
        with self.assertRaisesRegex(ValueError, "serial/order"):
            parseTrialStream(record().replace("ECHO7_TRIAL_WORD\t0\t4\t", "ECHO7_TRIAL_WORD\t1\t4\t"), BUILD)

    def testSelectionAndTrialLabelsAreCheckedIndependently(self):
        rows, _ = parseTrialStream(record() + record(1, "SELECT", 2, 1), BUILD)
        reader = TrialRecordReader(argparse.Namespace(args=None, out=None, result={}), rows)
        reader.control()
        with self.assertRaisesRegex(RuntimeError, "out of order"):
            reader.control((1 << 24) | 1)


if __name__ == "__main__":
    unittest.main()
