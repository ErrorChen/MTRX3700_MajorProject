"""Validate JTAG snapshot transactions independently of 16-bit frame ordering.

Host times only decide whether modular frame comparison is applicable. They
never replace the FPGA's captureStartUs or measure its processing latency.
"""

# At the configured 25 fps the half-range is about 21.8 minutes. Ten minutes is
# deliberately conservative even at 50 fps, with ample request/transport margin.
FRAME_COMPARISON_WINDOW_MS = 600_000
STATE_FIELDS = ("count", "ack", "busy", "ready", "mode", "source")


def _integer(value, name, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise RuntimeError("invalid snapshot transaction field: " + name)
    return value


def validateSnapshotTransaction(metadata, target, held, dumpBytes):
    if metadata.get("schema") != "echo7-snapshot-transaction-v1":
        raise RuntimeError("missing/unsupported snapshot transaction schema")
    if metadata.get("verified") is not True:
        raise RuntimeError("snapshot transaction was not verified by the transport")
    expectedMode = "held" if held else "fresh"
    if metadata.get("mode") != expectedMode:
        raise RuntimeError("held/fresh snapshot transaction mode mismatch")
    expectedTarget = {key: target[key] for key in ("cable", "device")}
    if metadata.get("target") != expectedTarget:
        raise RuntimeError("snapshot transaction target differs from the selected FPGA")
    states = []
    for name in ("requestBefore", "accepted", "readBefore", "readAfter"):
        state = metadata.get(name)
        if not isinstance(state, dict):
            raise RuntimeError("missing snapshot transaction state: " + name)
        for field in STATE_FIELDS:
            maximum = 65535 if field == "count" else 3 if field == "mode" else 1
            _integer(state.get(field), name + "." + field, maximum)
        states.append({field: state[field] for field in STATE_FIELDS})
    before, accepted, readBefore, readAfter = states
    if before["busy"] or before["ack"] != before["source"]:
        raise RuntimeError("snapshot request began before the preceding request became idle")
    if accepted["busy"] or not accepted["ready"] or accepted["ack"] != accepted["source"]:
        raise RuntimeError("snapshot completion lacks idle/ready/matching acknowledgement")
    if accepted != readBefore or readBefore != readAfter:
        raise RuntimeError("snapshot replaced before or during memory read")
    countDelta = (accepted["count"] - before["count"]) & 0xffff
    if held:
        if metadata.get("requestedToggle") is not None or before != accepted:
            raise RuntimeError("held snapshot unexpectedly contains a new request")
    else:
        requested = _integer(metadata.get("requestedToggle"), "requestedToggle", 1)
        if requested != 1 - before["source"] or accepted["ack"] != requested:
            raise RuntimeError("fresh snapshot acknowledgement does not match the request toggle")
        if not 0 < countDelta < 0x8000:
            raise RuntimeError("fresh snapshot count did not advance within this transaction")
    times = [_integer(metadata.get(name), name, 2**63 - 1) for name in
             ("startedHostMs", "acceptedHostMs", "readStartedHostMs", "readFinishedHostMs")]
    if times != sorted(times):
        raise RuntimeError("snapshot host transaction times are not monotonic")
    words = _integer(metadata.get("memoryWords"), "memoryWords", 2**31 - 1)
    if words * 2 != dumpBytes:
        raise RuntimeError("snapshot metadata memory length differs from the actual dump")
    return {"status": "PASS", "fresh": not held, "countDelta": countDelta,
            "snapshotCount": accepted["count"], "hostObservedMs": times[1],
            "proof": "request toggle, changed GCTL count, matching ack and stable pre/post memory state",
            "hostTimeMeaning": "Host transaction chronology only; not the FPGA capture timestamp"}


def validateFrameProgress(frameId, previous, target, epoch, hostObservedMs):
    """Use modular ordering only when history is recent and in the same epoch."""
    _integer(frameId, "nativeFrameId", 65535)
    if not previous or previous.get("target") != target or previous.get("programmingEpoch") != epoch:
        return {"comparison": "NO_COMPARABLE_EPOCH", "hostElapsedMs": None}
    priorHostMs = previous.get("hostObservedMs")
    if type(priorHostMs) is not int:
        return {"comparison": "HISTORY_HAS_NO_HOST_INTERVAL", "hostElapsedMs": None}
    elapsed = hostObservedMs - priorHostMs
    if not 0 <= elapsed <= FRAME_COMPARISON_WINDOW_MS:
        return {"comparison": "INTERVAL_OUTSIDE_MODULAR_COMPARISON_WINDOW", "hostElapsedMs": elapsed}
    _integer(previous.get("frameId"), "previousNativeFrameId", 65535)
    delta = (frameId - previous["frameId"]) & 0xffff
    if not 0 < delta < 0x8000:
        raise RuntimeError("fresh capture did not advance native frameId within the short comparison interval")
    return {"comparison": "SHORT_INTERVAL_FORWARD", "hostElapsedMs": elapsed, "nativeFrameDelta": delta}
