"""Strict QRP3 stream decoding; no image classification or fabricated replies."""
import re
from debug_decode import decodeQueryWords


def markerSelector(markerType, digit=None):
    """Validate the user-facing identity before issuing any board transaction."""
    kinds = {"bay": 1, "function": 2, "reference": 3}
    if markerType not in kinds:
        raise ValueError("marker type must be bay, function or reference")
    if markerType == "reference" and digit is None:
        digit = 15
    if (type(digit) is not int or
            (markerType == "bay" and digit not in range(1, 7)) or
            (markerType == "function" and digit not in (1, 2)) or
            (markerType == "reference" and digit != 15)):
        raise ValueError("bay requires digit1..6, function requires1/2, reference uses F with --digit omitted")
    return kinds[markerType], digit


def parseQueryStream(output, opcode, selector=None):
    """Verify complete bounded replies and retain abandoned replies separately.

    Recovery may start at a nonzero item index of the one old outstanding query.
    New responses must start at index0. Neither a transport ACK nor a collection
    of individually valid packets proves a complete transaction without LAST and
    the session's final count record.
    """
    if opcode not in (0, 8, 9):
        raise ValueError("query opcode must be drain, LIST or GET")
    records, current, action, session, done = [], None, None, None, None

    def header(bits, *, accepted=False):
        if not re.fullmatch("[01]{96}", bits):
            raise ValueError("malformed query transport header")
        magic, build, meta = [int(bits[index:index+32], 2) for index in (0, 32, 64)]
        if magic != 0x42444247 or meta >> 24 != 8 or (meta >> 16) & 255 != 3 or meta & 255 != 96:
            raise ValueError("unsupported query transport schema/contract/length")
        if session is not None and build != session["buildId"]:
            raise ValueError("query build identity changed during session")
        if accepted and meta & 0x7000:
            raise ValueError("query item was not acknowledged as accepted")
        return {"buildId": build, "meta": meta}

    for line in output.splitlines():
        if not line.startswith("ECHO7_QUERY_"):
            continue
        fields = line.split("\t")
        kind = fields[0].removeprefix("ECHO7_QUERY_")
        if done is not None:
            raise ValueError("query records appeared after completion")
        if kind == "SESSION":
            if session is not None or records or current or len(fields) != 2:
                raise ValueError("invalid query session boundary")
            session = header(fields[1])
            continue
        if session is None:
            raise ValueError("query record precedes session identity")
        if kind == "ACTION":
            if current is not None or action is not None or len(fields) != 3 or int(fields[1]) != opcode or opcode == 0:
                raise ValueError("unexpected query action acknowledgement")
            if not re.fullmatch("[01]{32}", fields[2]):
                raise ValueError("malformed query action metadata")
            meta = int(fields[2], 2)
            if meta >> 24 != 8 or (meta >> 16) & 255 != 3 or meta & 255 != 96 or meta & 0x7000:
                raise ValueError("query action rejected or has incompatible metadata")
            action = {"opcode": opcode, "transportAcknowledged": True, "accepted": True,
                      "meaning": "Accepted into Csim request queue; result packets prove completion."}
        elif kind == "BEGIN":
            if current is not None or len(fields) != 3 or int(fields[1]) != len(records) or len(records) >= 32:
                raise ValueError("query packet boundary/serial/bound is invalid")
            phase = fields[2]
            if phase not in ("DRAIN", "RESULT") or (phase == "DRAIN" and action) or (phase == "RESULT" and not action):
                raise ValueError("query drain/result action ordering is invalid")
            current = {"serial": len(records), "phase": phase, "words": []}
        elif kind in ("HEADER", "WORD", "END"):
            if current is None or len(fields) < 2 or int(fields[1]) != current["serial"]:
                raise ValueError("query packet record serial/order mismatch")
            if kind == "HEADER":
                if len(fields) != 3 or "header" in current or current["words"]:
                    raise ValueError("query header duplicated or reordered")
                current["header"] = header(fields[2], accepted=True)
            elif kind == "WORD":
                if (len(fields) != 4 or "header" not in current or int(fields[2]) != len(current["words"])
                        or len(current["words"]) >= 8 or not re.fullmatch("[01]{32}", fields[3])):
                    raise ValueError("query words missing, duplicated or reordered")
                current["words"].append(int(fields[3], 2))
            else:
                if len(fields) != 2 or "header" not in current:
                    raise ValueError("query packet has no complete header")
                current["decoded"] = decodeQueryWords(current["words"], session["buildId"])
                records.append(current)
                current = None
        elif kind == "DONE":
            if current is not None or len(fields) != 5 or int(fields[1]) != opcode:
                raise ValueError("query completion record is invalid")
            done = {"drainedCount": int(fields[2]), "resultCount": int(fields[3]), "elapsedMs": int(fields[4])}
            if any(value < 0 for value in done.values()):
                raise ValueError("negative query completion count/time")
        else:
            raise ValueError("unknown query stream record")
    if current is not None or session is None or done is None:
        raise ValueError("query transport ended before complete transaction; use markers --drain to recover")
    if (opcode != 0) != (action is not None):
        raise ValueError("query transaction lacks its action acceptance")
    groups = {phase: [row["decoded"] for row in records if row["phase"] == phase] for phase in ("DRAIN", "RESULT")}
    for phase, rows in groups.items():
        if len(rows) > 16 or len(rows) != done["drainedCount" if phase == "DRAIN" else "resultCount"]:
            raise ValueError("query completion counts differ from retained packets")
        if not rows:
            if phase == "RESULT" and opcode:
                raise ValueError("accepted query has no terminal result")
            continue
        first = rows[0]
        identity = tuple(first[name] for name in ("requestTag", "frameId", "captureStartUs", "configVersion", "count", "reason"))
        firstIndex = first["index"] if phase == "DRAIN" else 0
        for position, row in enumerate(rows):
            if (tuple(row[name] for name in ("requestTag", "frameId", "captureStartUs", "configVersion", "count", "reason")) != identity
                    or row["index"] != firstIndex+position or bool(row["last"]) != (position == len(rows)-1)):
                raise ValueError("query sequence changed tag/frame/time/config/count/reason or lost its last item")
            if phase == "RESULT" and row["count"]:
                if opcode == 8 and row["reason"] != 0:
                    raise ValueError("LIST items must have QUERY_OK")
                if opcode == 9 and (selector != (row["markerType"], row["digit"])
                        or row["reason"] != int(row["count"] > 1)):
                    raise ValueError("GET returned a different identity or incorrect multiplicity reason")
    if opcode == 0 and groups["RESULT"]:
        raise ValueError("drain-only transaction returned new query results")
    return {"schema": "echo7-query-transaction-v1", "buildId": session["buildId"],
            "contractVersion": 3, "debugSchemaVersion": 8, "completed": True,
            "commandAcceptance": action, "drainedReplies": groups["DRAIN"],
            "results": groups["RESULT"], "items": [row for row in groups["RESULT"] if row["count"]],
            "transportCompletion": done,
            "meaning": "FPGA query observations with original capture times; no tracking lock or present-time freshness is promised."}
