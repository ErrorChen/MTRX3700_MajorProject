"""Assess actual BCTL calibration traces without confusing acceptance/completion."""

# Frozen Member B datasheet targets, not course-mandated limits. This measure is
# a conservative polling bound; exceeding it prevents a timing PASS but does not
# prove that the unobserved internal confirmation-to-commit interval exceeded it.
CALIBRATION_THRESHOLD_US = 2_000_000
CALIBRATION_GOAL_US = 1_000_000


def evaluateCalibration(trace, final, busyMeta):
    failures = []
    busyRejected = busyMeta is not None and bool(busyMeta & (1 << 14)) and (busyMeta >> 12) & 3 == 2
    if not busyRejected:
        failures.append("second request was not explicitly rejected as busy")
    versions = [row["configVersion"] for row in trace]
    committed = bool(versions) and ((final["configVersion"] - versions[0]) & 0xffff) == 1
    if not committed:
        failures.append("configuration version did not advance exactly once")
    if final["calibrationSampleFrames"] != 8:
        failures.append(f"only {final['calibrationSampleFrames']}/8 valid sample frames")
    elapsed = None
    if committed:
        committedRows = [row for row in trace if row["configVersion"] != versions[0]]
        if committedRows:
            elapsed = (committedRows[0]["boardTimeUs"] - trace[0]["boardTimeUs"]) & 0xffffffff
    # An IDLE snapshot after the acknowledged re-arm precedes the new three-
    # frame red1 confirmation. Ending at a later observed commit therefore
    # gives a conservative upper bound, not an invented exact start timestamp.
    preConfirmation = bool(trace) and ((trace[0]["statusUpper"] >> 5) & 15) == 0
    timingBound = elapsed if preConfirmation else None
    timingStatus = "NOT_MEASURED" if timingBound is None else (
        "PASS" if timingBound <= CALIBRATION_THRESHOLD_US else "FAIL")
    if timingStatus == "FAIL":
        failures.append("calibration conservative timing bound exceeds frozen 2000000 us threshold")
    return {"status": "FAIL" if failures else "PASS", "reason": "; ".join(failures),
            "busyRequestRejected": busyRejected, "configurationCommitted": committed,
            "validSampleFrames": final["calibrationSampleFrames"],
            "observedTraceToCommitUs": elapsed,
            "confirmedAttemptToCommitUpperBoundUs": timingBound,
            "timingTarget": {"status": timingStatus,
                             "thresholdUs": CALIBRATION_THRESHOLD_US,
                             "goalUs": CALIBRATION_GOAL_US,
                             "measuredUpperBoundUs": timingBound,
                             "goalMet": None if timingBound is None else timingBound <= CALIBRATION_GOAL_US,
                             "meaning": "Conservative observed bound; NOT_MEASURED is not a timing pass."},
            "timingMeaning": "Board-time polling interval; not an exact red1-confirmation timestamp.",
            "lastSample": final.get("calibrationLastSample"),
            "terminalEvent": final.get("userEvent") if final.get("userEventHeld") else None}
