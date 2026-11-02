"""Check explicit synchroniser coverage in a real Quartus metastability report.

This verifies named register stages, not a numerical MTBF claim. Quartus may
include a downstream consumer as a third register; the first two stages are the
physical synchroniser contract. The caller must separately establish whether
the report came from a post-map or a fitted timing netlist and verify timing.
"""
import argparse
import json
import re
from pathlib import Path


def expectedSynchronisers():
    """Return the 57 actual first-stage -> second-stage register names."""
    bridge = "perceptionCore:core|cameraStreamBridge:cameraBridge|"
    fifo = bridge + "asyncPixelFifo:fifo|"
    result = {}
    for prefix, stem, count in [(fifo, "readGray", 9), (fifo, "writeGray", 9),
                                (bridge, "timeGray", 32)]:
        for bit in range(count):
            result[f"{prefix}{stem}Meta[{bit}]"] = f"{prefix}{stem}Sync[{bit}]"
    for instance in ["heldBusCdc:resultToCamera|", "heldBusCdc:resultToDisplay|",
                     bridge + "heldBusCdc:requestCdc|"]:
        for stem in ["requestSync", "acknowledgeSync"]:
            result[instance + stem + "[0]"] = instance + stem + "[1]"
    result[bridge + "faultSync[0]"] = bridge + "faultSync[1]"
    return result


def validateSynchronisers(reportText, expectedHeads=None):
    expected = expectedSynchronisers() if expectedHeads is None else expectedHeads
    records = {}
    errors = []
    for block in re.split(r"Synchronizer Chain #\d+:", reportText)[1:]:
        def field(label):
            match = re.search(r"; " + re.escape(label) + r"\s*;\s*(.*?)\s*;", block)
            return match.group(1) if match else None

        first = field("Synchronization Node")
        if first not in expected:
            continue
        if first in records:
            errors.append("Duplicate synchroniser chain: " + first)
            continue
        registerTable = re.split(r"; Synchronization Registers\s*;", block, maxsplit=1)
        registers = []
        outputSlacks = []
        if len(registerTable) == 2:
            for line in registerTable[1].splitlines()[1:]:
                cells = [cell.strip() for cell in line.split(";")]
                if len(cells) > 3 and cells[1]:
                    registers.append(cells[1])
                    try:
                        outputSlacks.append(float(cells[-2]))
                    except ValueError:
                        outputSlacks.append(None)
        length = field("Number of Synchronization Registers in Chain")
        record = {"firstStage": first, "secondStage": expected[first],
                  "method": field("Method of Synchronizer Identification"),
                  "reportedChainLength": int(length) if length and length.isdigit() else None,
                  "registers": registers, "outputSlackNs": outputSlacks}
        records[first] = record
        if record["method"] != "User Specified":
            errors.append("Synchroniser is not explicitly identified: " + first)
        if registers[:2] != [first, expected[first]]:
            errors.append("First two synchroniser stages differ: " + first)
        if record["reportedChainLength"] != len(registers):
            errors.append("Incomplete synchroniser register table: " + first)
    missing = sorted(set(expected) - set(records))
    errors.extend("Missing synchroniser chain: " + first for first in missing)
    return {"schema": "echo7-synchroniser-coverage-v1",
            "coverageStatus": "FAIL" if errors else "PASS",
            "expectedChainCount": len(expected), "reportedChainCount": len(records),
            "errors": errors, "chains": [records[name] for name in sorted(records)],
            "evidenceLevel": "REPORT_CONTENT_ONLY",
            "mtbfAcceptance": "NOT_ASSESSED",
            "limitations": ["Source build and post-fit report provenance must be checked separately.",
                            "Coverage does not establish routed settling slack or numerical MTBF.",
                            "A third downstream consumer is permitted after the two required stages."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validateSynchronisers(args.report.read_text(encoding="utf-8", errors="replace"))
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["coverageStatus"] == "PASS" else 1)
