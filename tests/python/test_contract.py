"""MODEL evidence for C v2. Actual RTL benches are separate CLI manifest entries."""
from __future__ import annotations
import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
import json
from pathlib import Path
import unittest

from contract_model import (
    ACTIVE_BAY_MASK, CONTRACT_VERSION, FIELD_LAYOUTS, ReferenceConsumer,
    freshTime, newerSequence, packPayload, rotateBbox, unpackPayload,
)

VECTORS = json.loads((Path(__file__).parents[2] / "tests/rtl/contract_vectors.json").read_text())


class ContractModelTests(unittest.TestCase):
    def test_public_layout(self):
        self.assertEqual(CONTRACT_VERSION, VECTORS["contractVersion"])
        self.assertEqual(ACTIVE_BAY_MASK, VECTORS["activeBayMask"])
        for kind, layout in FIELD_LAYOUTS.items():
            self.assertEqual(sum(width for _, width in layout), VECTORS["widths"][kind])
            fields = {name: (1 << width) - 1 for name, width in layout}
            self.assertEqual(unpackPayload(kind, packPayload(kind, fields)), fields)
        self.assertEqual(packPayload("targetRequest", {"operation": 1, "requestTag": 0x1234, "bayId": 6}), 0x112346)

    def test_no_silent_truncation(self):
        with self.assertRaises(ValueError):
            packPayload("targetRequest", {"operation": 1, "requestTag": 65536, "bayId": 1})
        with self.assertRaises(ValueError):
            packPayload("targetRequest", {"operation": 1, "requestTag": 0})
        with self.assertRaises(ValueError):
            unpackPayload("status", 1 << 76)

    def test_bbox_vectors(self):
        for vector in VECTORS["bbox"]:
            self.assertEqual(rotateBbox(*vector["native"]), vector["expected"])
        for bbox in ((0, 320, 0, 239), (10, 9, 1, 2), (0, 1, 0, 240)):
            with self.assertRaises(ValueError):
                rotateBbox(*bbox)

    def test_sequence_and_time_wrap(self):
        for vector in VECTORS["sequence"]:
            self.assertEqual(newerSequence(vector["next"], vector["previous"]), vector["newer"])
        for vector in VECTORS["time"]:
            self.assertEqual(freshTime(vector["now"], vector["stamp"], vector["budget"]), vector["fresh"])
        with self.assertRaises(ValueError):
            freshTime(0, 0, 0x80000000)

    def test_consumer_current_real_observations_only(self):
        consumer = ReferenceConsumer(maxAgeUs=100)
        consumer.requestAccepted(dict(operation=1, requestTag=7, bayId=3))
        report = {name: 0 for name, _ in FIELD_LAYOUTS["targetReport"]}
        report.update(requestTag=7, frameId=65535, captureStartUs=0xFFFFFFF0,
                      bayId=3, frameGood=1, observed=1, locked=1, targetSelected=1,
                      centreU=22, centreV=307, boxWidth=5, boxHeight=4, quality=220)
        self.assertTrue(consumer.reportAccepted(report))
        self.assertTrue(consumer.usable(32))
        self.assertFalse(consumer.usable(85))
        self.assertFalse(consumer.usable(32, interactionBusy=True))
        for stale in (dict(frameId=65535, observed=0), dict(requestTag=6, frameId=0),
                      dict(configVersion=1, frameId=0), dict(frameId=65534, observed=0)):
            self.assertFalse(consumer.reportAccepted(report | stale))
        self.assertTrue(consumer.usable(32))
        self.assertTrue(consumer.reportAccepted(report | dict(frameId=0, observed=0)))
        self.assertFalse(consumer.usable(32))
        consumer.configChanged(1)
        self.assertIsNone(consumer.cachedReport)
        for bayId in (0, 7, 8, 9):
            consumer.requestAccepted(dict(operation=1, requestTag=7, bayId=bayId))
            self.assertTrue(consumer.reportAccepted(report | dict(configVersion=1, bayId=bayId)))
            self.assertFalse(consumer.usable(32))


if __name__ == "__main__":
    unittest.main()
