"""Member C contract v2 reference: integer geometry, wire layout and consumers.

This model consumes reported observations. It never infers a bay from a scene slot
and does not constitute RTL or hardware evidence. All ages use the shared board
microsecond time, not host receive time.
"""
from __future__ import annotations

from dataclasses import dataclass

CONTRACT_VERSION = 2
ACTIVE_BAY_MASK = 0x07E
FIELD_LAYOUTS = {
    "targetRequest": (("operation", 2), ("requestTag", 16), ("bayId", 4)),
    "targetReport": (
        ("requestTag", 16), ("frameId", 16), ("captureStartUs", 32),
        ("configVersion", 16), ("bayId", 4), ("frameGood", 1),
        ("observed", 1), ("locked", 1), ("ambiguous", 1),
        ("targetSelected", 1), ("centreU", 8), ("centreV", 9),
        ("boxWidth", 8), ("boxHeight", 9), ("quality", 8), ("reason", 8),
    ),
    "userEvent": (
        ("eventId", 16), ("eventType", 4), ("bayId", 4), ("quality", 8),
        ("issuedAtUs", 32), ("configVersion", 16), ("reason", 8), ("interactionId", 16),
    ),
    "status": (
        ("interactionBusy", 1), ("kind", 2), ("state", 4),
        ("calibrated", 1), ("audioReady", 1), ("perceptionReady", 1),
        ("activeCfgVersion", 16), ("reportDropCount", 16), ("eventOverflow", 1),
        ("faultFlags", 16), ("interactionId", 16), ("speechArmed", 1),
    ),
}


def packPayload(kind: str, fields: dict[str, int]) -> int:
    """Strict unsigned packing; reject unknown/missing fields and overflow."""
    layout = FIELD_LAYOUTS[kind]
    if set(fields) != {name for name, _ in layout}:
        raise ValueError(f"{kind}: fields differ from contract v2")
    value = 0
    for name, width in layout:
        field = fields[name]
        if not isinstance(field, int) or not 0 <= field < (1 << width):
            raise ValueError(f"{name}: does not fit unsigned {width} bits")
        value = (value << width) | field
    return value


def unpackPayload(kind: str, value: int) -> dict[str, int]:
    layout = FIELD_LAYOUTS[kind]
    width = sum(bits for _, bits in layout)
    if not 0 <= value < (1 << width):
        raise ValueError(f"{kind}: does not fit {width} bits")
    fields = {}
    for name, bits in reversed(layout):
        fields[name] = value & ((1 << bits) - 1)
        value >>= bits
    return fields


def rotateBbox(xMin: int, xMax: int, yMin: int, yMax: int) -> dict[str, int]:
    if not (0 <= xMin <= xMax < 320 and 0 <= yMin <= yMax < 240):
        raise ValueError("bbox is outside the inclusive native 320 x 240 frame")
    uMin, uMax = yMin, yMax
    vMin, vMax = 319 - xMax, 319 - xMin
    return dict(centreU=(uMin + uMax) // 2, centreV=(vMin + vMax) // 2,
                boxWidth=uMax - uMin + 1, boxHeight=vMax - vMin + 1)


def freshTime(nowUs: int, capturedUs: int, maxAgeUs: int) -> bool:
    if not 0 <= maxAgeUs < 0x80000000:
        raise ValueError("age budget must be below half the time counter range")
    age = (nowUs - capturedUs) & 0xFFFFFFFF
    return age < 0x80000000 and age <= maxAgeUs


def newerSequence(nextId: int, previousId: int) -> bool:
    delta = (nextId - previousId) & 0xFFFF
    return 0 < delta < 0x8000


@dataclass
class ReferenceConsumer:
    """No-motion C receiver; re-check usable() whenever a cached value is used."""

    maxAgeUs: int = 150000
    currentRequest: dict | None = None
    cachedReport: dict | None = None
    lastFrame: int | None = None
    configVersion: int = 0

    def requestAccepted(self, request: dict) -> None:
        packPayload("targetRequest", request)
        self.currentRequest = request.copy()
        self.cachedReport = None
        self.lastFrame = None

    def configChanged(self, configVersion: int) -> None:
        if configVersion != self.configVersion:
            self.configVersion = configVersion
            self.cachedReport = None
            self.lastFrame = None

    def reportAccepted(self, report: dict) -> bool:
        packPayload("targetReport", report)
        request = self.currentRequest
        if request is None or report["requestTag"] != request["requestTag"]:
            return False
        if report["configVersion"] != self.configVersion:
            return False
        if self.lastFrame is not None and not newerSequence(report["frameId"], self.lastFrame):
            return False
        self.lastFrame = report["frameId"]
        self.cachedReport = report.copy()
        return True

    def usable(self, nowUs: int, *, perceptionReady: bool = True,
               interactionBusy: bool = False) -> bool:
        request, report = self.currentRequest, self.cachedReport
        if request is None or report is None:
            return False
        return bool(
            request["operation"] == 1 and 1 <= request["bayId"] <= 6
            and report["requestTag"] == request["requestTag"]
            and report["bayId"] == request["bayId"]
            and report["configVersion"] == self.configVersion
            and report["targetSelected"] and report["frameGood"]
            and report["observed"] and report["locked"] and not report["ambiguous"]
            and perceptionReady and not interactionBusy
            and freshTime(nowUs, report["captureStartUs"], self.maxAgeUs)
        )
