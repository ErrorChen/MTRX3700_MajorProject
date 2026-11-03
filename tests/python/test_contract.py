"""MODEL evidence for C v3. Actual RTL benches are separate CLI manifest entries."""
from __future__ import annotations
import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
import json
from pathlib import Path
import unittest

from contract_model import (
    ACTIVE_BAY_MASK, CONTRACT_VERSION, FIELD_LAYOUTS, LEGACY_V2_FIELD_LAYOUTS, ReferenceConsumer,
    MARKER_BAY, MARKER_FUNCTION, MARKER_REFERENCE, markerEnabled,
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
        self.assertEqual(packPayload("targetRequest", {"operation": 1, "requestTag": 0x1234, "markerType": 1, "digit": 6}), 0x448D16)

    def test_no_silent_truncation(self):
        with self.assertRaises(ValueError):
            packPayload("targetRequest", {"operation": 1, "requestTag": 65536, "markerType": 1, "digit": 1})
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
        consumer.requestAccepted(dict(operation=1, requestTag=7, markerType=1, digit=3))
        report = {name: 0 for name, _ in FIELD_LAYOUTS["targetReport"]}
        report.update(requestTag=7, frameId=65535, captureStartUs=0xFFFFFFF0,
                      markerType=1, digit=3, frameGood=1, observed=1, locked=1, targetSelected=1,
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
            consumer.requestAccepted(dict(operation=1, requestTag=7, markerType=1, digit=bayId))
            self.assertTrue(consumer.reportAccepted(report | dict(configVersion=1, digit=bayId)))
            self.assertFalse(consumer.usable(32))


    def test_explicit_legacy_layout_does_not_relabel_history(self):
        fields = {"operation": 1, "requestTag": 0x1234, "bayId": 6}
        value = packPayload("targetRequest", fields, contractVersion=2)
        self.assertEqual(value, 0x112346)
        self.assertEqual(unpackPayload("targetRequest", value, contractVersion=2), fields)
        self.assertEqual(sum(bits for _, bits in LEGACY_V2_FIELD_LAYOUTS["targetReport"]), 139)
        with self.assertRaises(ValueError):
            packPayload("targetRequest", fields)
        with self.assertRaises(ValueError):
            packPayload("targetRequest", fields, contractVersion=4)
        with self.assertRaises(ValueError):
            unpackPayload("targetReport", 0, contractVersion=1)

    def test_exact_typed_identity_domain(self):
        for vector in VECTORS["identity"]:
            with self.subTest(vector=vector):
                self.assertEqual(markerEnabled(vector["markerType"], vector["digit"]), vector["enabled"])
        self.assertNotEqual(packPayload("targetRequest", dict(operation=1, requestTag=1, markerType=1, digit=1)),
                            packPayload("targetRequest", dict(operation=1, requestTag=1, markerType=2, digit=1)))

    def test_red_and_reference_tracking_queries_preserve_cache(self):
        for markerType, digit in ((MARKER_FUNCTION, 1), (MARKER_FUNCTION, 2), (MARKER_REFERENCE, 15)):
            with self.subTest(markerType=markerType, digit=digit):
                consumer = ReferenceConsumer(maxAgeUs=100)
                request = dict(operation=1, requestTag=8, markerType=markerType, digit=digit)
                consumer.requestAccepted(request)
                report = {name: 0 for name, _ in FIELD_LAYOUTS["targetReport"]}
                report.update(requestTag=8, frameId=1, captureStartUs=100, markerType=markerType,
                              digit=digit, frameGood=1, observed=1, locked=1, targetSelected=1,
                              centreU=22, centreV=307, boxWidth=5, boxHeight=4, quality=220)
                self.assertTrue(consumer.reportAccepted(report))
                for operation in (2, 3):
                    consumer.requestAccepted(dict(operation=operation, requestTag=90 + operation,
                                                  markerType=MARKER_BAY, digit=1))
                    self.assertEqual(consumer.currentRequest, request)
                    self.assertEqual(consumer.cachedReport, report)
                    self.assertEqual(consumer.lastFrame, 1)
                    self.assertTrue(consumer.usable(120))
                self.assertFalse(consumer.reportAccepted(report | dict(frameId=2, markerType=MARKER_BAY)))
                self.assertTrue(consumer.usable(120))
                self.assertTrue(consumer.reportAccepted(report | dict(frameId=2, observed=0, locked=0,
                    ambiguous=1, centreU=0, centreV=0, boxWidth=0, boxHeight=0, quality=0, reason=4)))
                self.assertFalse(consumer.usable(120))
                consumer.requestAccepted(dict(operation=0, requestTag=100, markerType=0, digit=15))
                self.assertIsNone(consumer.cachedReport)
                self.assertFalse(consumer.usable(120))

    def test_query_result_layout_and_strict_unsigned_boundaries(self):
        fields = {name: 0 for name, _ in FIELD_LAYOUTS["queryResult"]}
        fields.update(requestTag=0x1234, frameId=65535, captureStartUs=0xFFFFFFFE,
                      configVersion=65535, reason=1, count=16, index=15, last=1,
                      markerType=MARKER_FUNCTION, digit=1, centreU=239, centreV=319,
                      boxWidth=240, boxHeight=320, quality=220)
        self.assertEqual(unpackPayload("queryResult", packPayload("queryResult", fields)), fields)
        with self.assertRaises(ValueError):
            packPayload("queryResult", fields | dict(index=16))
        with self.assertRaises(ValueError):
            packPayload("targetReport", {name: -1 for name, _ in FIELD_LAYOUTS["targetReport"]})


if __name__ == "__main__":
    unittest.main()
