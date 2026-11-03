#!/usr/bin/env python3
"""Export the current verified B source/bitstream using relative archive paths.

No Git operation or remote upload occurs. Reproducible compiler databases,
private toolchains and unrelated runs are excluded. Export refuses a stale SOF.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile
import echo7


def datasheetBinding(path, current):
    """Accept only the explicit PDF's hash-bound renderer record for this build."""
    sidecar = path.with_suffix(path.suffix + ".json")
    binding = json.loads(sidecar.read_text(encoding="utf-8"))
    if (binding.get("schema") != "member-b-datasheet-generation-v1"
            or binding.get("status") != "PASS" or binding.get("pages") != 1
            or binding.get("sourceSha256") != current["sha256"]
            or binding.get("buildId") != current["buildId"]
            or binding.get("sha256") != echo7.digest(path)
            or len(binding.get("indexSha256", "")) != 64):
        raise ValueError("datasheet PDF/renderer record does not match the current verified source")
    return {key: binding[key] for key in
            ("schema", "sourceSha256", "buildId", "sha256", "indexSha256", "pages")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--datasheet", type=Path,
                        help="Explicit current one-page PDF; requires its adjacent .pdf.json renderer/source binding")
    args = parser.parse_args()
    root = echo7.ROOT
    build = json.loads((echo7.WORK / "last_build.json").read_text())
    current = echo7.sourceIdentity()
    if build.get("status") != "PASS" or build["source"]["sha256"] != current["sha256"]:
        raise RuntimeError("current sources do not have a successful fitted/timed build")
    sof = Path(build["sof"]["path"])
    if echo7.digest(sof) != build["sof"]["sha256"]:
        raise RuntimeError("verified SOF hash changed")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or echo7.WORK / (stamp + "_member_b_submission.zip")
    if out.exists():
        raise FileExistsError("refusing to overwrite an existing submission archive")
    out.parent.mkdir(parents=True, exist_ok=True)
    selected = {}
    for folder in ("rtl", "quartus", "tools", "tests", "assets", "docs"):
        for path in (root / folder).rglob("*"):
            if not path.is_file() or any(part in ("__pycache__", "db", "incremental_db", "output_files", "vga_sink") for part in path.parts):
                continue
            if path.suffix.lower() in (".pyc", ".qws", ".wlf", ".vcd", ".cdb", ".rdb"):
                continue
            if folder == "docs" and path.suffix.lower() != ".pdf":
                continue
            selected[path.relative_to(root).as_posix()] = path
    for name in ("README.md", "VERSION_README.md", "OWNERS.md", "requirements.txt", "run_all_tests.sh",
                 ".gitignore", ".gitattributes", ".editorconfig"):
        selected[name] = root / name
    selected["verified/PartBDebug.sof"] = sof
    record = {"schema": "echo7-submission-v1", "scope": "Member B only, microphone deferred",
              "sourceSha256": current["sha256"], "buildId": current["buildId"],
              "sofSha256": build["sof"]["sha256"], "files": {}}
    if args.datasheet:
        record["datasheet"] = datasheetBinding(args.datasheet, current)
        selected["member_b_datasheet.pdf"] = args.datasheet
    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(selected.items()):
            payload = path.read_bytes()
            if name == "member_b_datasheet.pdf" and hashlib.sha256(payload).hexdigest() != record["datasheet"]["sha256"]:
                raise ValueError("datasheet changed while creating the submission")
            archive.writestr(name, payload)
            record["files"][name] = hashlib.sha256(payload).hexdigest()
        archive.writestr("verified/manifest.json", json.dumps(record, indent=2) + "\n")
    with zipfile.ZipFile(out) as archive:
        if archive.testzip():
            raise RuntimeError("submission archive CRC failed")
    print(json.dumps({"status": "PASS", "path": str(out), "sha256": echo7.digest(out),
                      "files": len(selected), "scope": "ARCHIVE_INTEGRITY; does not add hardware acceptance"}, indent=2))


if __name__ == "__main__":
    main()
