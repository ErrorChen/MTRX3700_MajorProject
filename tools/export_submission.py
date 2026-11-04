#!/usr/bin/env python3
"""Export the current integrated source/bitstream using relative archive paths.

No Git operation or remote upload occurs. Reproducible compiler databases,
private toolchains and unrelated runs are excluded. Export refuses a stale SOF.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile
import echo7
from export_ai_transcript import credentialReasons

AI_DATA_FILES = frozenset(("ai_transcript.txt", "ai_transcript.json"))
AI_MANIFEST_NAME = "ai_transcript_manifest.json"
AI_MESSAGE_FIELDS = frozenset(("sourceLine", "timestamp", "role", "phase", "textBlocks",
                              "visibleQuestions", "sourceFormat"))


def aiTranscriptBinding(path, root):
    """Validate one explicit visible export and return its immutable byte snapshot.

    This never reads a session log or searches an account/history directory.
    Fixed basenames prohibit both POSIX/Windows absolute paths, traversal and
    additional manifest entries. Archive writes use these already-checked bytes,
    so later filesystem changes cannot substitute unvalidated dialogue.
    """
    path = Path(path)
    if path.name != AI_MANIFEST_NAME or path.is_symlink():
        raise ValueError("AI transcript requires its explicit regular manifest file")
    manifestBytes = path.read_bytes()
    binding = json.loads(manifestBytes.decode("utf-8"))
    if (not isinstance(binding, dict) or binding.get("schema") != "member-b-visible-ai-transcript-v1"
            or binding.get("status") != "PASS"):
        raise ValueError("AI transcript schema/status is not a successful visible export")
    sessionId = binding.get("sessionId", "")
    if (not isinstance(sessionId, str)
            or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", sessionId)):
        raise ValueError("AI transcript source session identity is invalid")
    sourceName = binding.get("sourceFileName", "")
    if (not isinstance(sourceName, str) or not re.fullmatch(
            r"rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-" + re.escape(sessionId) + r"\.jsonl", sourceName)):
        raise ValueError("AI transcript source filename does not identify its declared session")
    workspace = binding.get("workspace")
    if (not isinstance(workspace, str)
            or os.path.normcase(str(Path(workspace).resolve())) != os.path.normcase(str(Path(root).resolve()))
            or not re.fullmatch(r"[0-9a-f]{64}", str(binding.get("sourceSnapshotSha256", "")))
            or type(binding.get("sourceSnapshotBytes")) is not int or binding["sourceSnapshotBytes"] <= 0):
        raise ValueError("AI transcript workspace/source snapshot provenance is invalid")
    if not isinstance(binding.get("files"), dict) or set(binding["files"]) != AI_DATA_FILES:
        raise ValueError("AI transcript files must contain exactly the two fixed TXT/JSON basenames")
    if (not isinstance(binding.get("selectionPolicy"), dict)
            or binding["selectionPolicy"].get("responseItemFallback") is not False
            or not isinstance(binding.get("scope"), str) or not binding["scope"]):
        raise ValueError("AI transcript must exclude internal response-item records")
    payloads = {}
    for name in sorted(AI_DATA_FILES):
        entry = binding["files"][name]
        if (not isinstance(entry, dict) or set(entry) != {"sha256", "bytes"}
                or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", "")))
                or type(entry.get("bytes")) is not int or entry["bytes"] < 0):
            raise ValueError("AI transcript file hash/size record is invalid")
        dataPath = path.parent / name
        if dataPath.is_symlink():
            raise ValueError("AI transcript data files must not be symbolic links")
        payload = dataPath.read_bytes()
        # Hash the bytes just read, not an earlier filesystem check or a name.
        if len(payload) != entry["bytes"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError("AI transcript file changed or does not match its manifest")
        if credentialReasons(payload.decode("utf-8")):
            raise ValueError("AI transcript contains a known credential-format match")
        payloads["course/" + name] = payload
    transcript = json.loads(payloads["course/ai_transcript.json"].decode("utf-8"))
    if (not isinstance(transcript, dict) or set(transcript) != {"metadata", "messages"}
            or transcript["metadata"] != {key: value for key, value in binding.items() if key != "files"}
            or not isinstance(transcript["messages"], list) or not transcript["messages"]):
        raise ValueError("AI transcript JSON does not match the manifest's session/provenance")
    counts = {}; previousLine = 0
    for message in transcript["messages"]:
        if (not isinstance(message, dict) or set(message) != AI_MESSAGE_FIELDS
                or message.get("role") not in ("user", "assistant")
                or message.get("sourceFormat") not in ("completed_ui_item", "legacy_visible_event")
                or type(message.get("sourceLine")) is not int or message["sourceLine"] <= previousLine
                or not isinstance(message.get("timestamp"), str)
                or not isinstance(message.get("textBlocks"), list)
                or not all(isinstance(text, str) for text in message["textBlocks"])
                or not isinstance(message.get("visibleQuestions"), list)):
            raise ValueError("AI transcript contains a non-whitelisted visible message")
        expectedPhases = ("user",) if message["role"] == "user" else ("commentary", "final_answer", "final", "visible_agent_message")
        if message.get("phase") not in expectedPhases:
            raise ValueError("AI transcript contains a non-visible message phase")
        for question in message["visibleQuestions"]:
            if (not isinstance(question, dict) or set(question) != {"title", "options"}
                    or not isinstance(question["title"], str)
                    or (question["options"] is not None and (not isinstance(question["options"], list)
                        or not all(isinstance(option, str) for option in question["options"])))):
                raise ValueError("AI transcript contains unsupported question metadata")
        previousLine = message["sourceLine"]
        counts[message["role"]] = counts.get(message["role"], 0) + 1
    if (counts != binding.get("messageCounts") or binding.get("visibleTimeRange") !=
            [transcript["messages"][0]["timestamp"], transcript["messages"][-1]["timestamp"]]):
        raise ValueError("AI transcript visible-message count/coverage is inconsistent")
    payloads["course/" + AI_MANIFEST_NAME] = manifestBytes
    provenance = {key: binding[key] for key in
                  ("schema", "status", "sessionId", "sourceSnapshotSha256", "sourceSnapshotBytes",
                   "visibleTimeRange", "messageCounts", "scope")}
    provenance["manifestSha256"] = hashlib.sha256(manifestBytes).hexdigest()
    provenance["archiveFiles"] = sorted(payloads)
    return provenance, payloads


def datasheetBinding(path, current):
    """Validate the explicitly selected PDF; a SHA sidecar is not required."""
    from pypdf import PdfReader
    pages = len(PdfReader(path).pages)
    if pages != 1:
        raise ValueError("course datasheet must have exactly one page")
    return {"path": str(path), "buildId": current["buildId"], "pages": pages,
            "meaning": "Explicit document; inclusion does not establish hardware acceptance"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--datasheet", type=Path,
                        help="Explicit current one-page PDF; no SHA sidecar required")
    parser.add_argument("--sof", type=Path, help="explicit SOF from the current successful build")
    parser.add_argument("--ai-transcript-manifest", type=Path,
                        help="Explicit reviewed visible-message export manifest; includes only its validated TXT/JSON/manifest under course/")
    args = parser.parse_args()
    root = echo7.ROOT
    build, sof = echo7.verifiedBuild(args.sof)
    current = echo7.sourceIdentity()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or echo7.WORK / (stamp + "_echo7_submission.zip")
    if out.exists():
        raise FileExistsError("refusing to overwrite an existing submission archive")
    out.parent.mkdir(parents=True, exist_ok=True)
    selected = {}
    for folder in ("rtl", "quartus", "tools", "tests", "assets", "docs"):
        for path in (root / folder).rglob("*"):
            if not path.is_file() or any(part in ("__pycache__", "db", "incremental_db", "output_files", "vga_sink") for part in path.parts):
                continue
            if path.suffix.lower() in (".pyc", ".qws", ".wlf", ".vcd", ".cdb", ".rdb", ".jsonl"):
                continue
            if path.name in AI_DATA_FILES | {AI_MANIFEST_NAME}:
                continue  # Dialogue is opt-in through the verified explicit manifest only.
            if (folder == "docs" and path.suffix.lower() not in (".pdf", ".md", ".txt")
                    and path.name != "integrated_datasheet_metrics.json"):
                continue
            selected[path.relative_to(root).as_posix()] = path
    for name in ("README.md", "README_EN.md", "VERSION_README.md", "OWNERS.md", "requirements.txt", "run_all_tests.sh",
                 ".gitignore", ".gitattributes", ".editorconfig"):
        selected[name] = root / name
    firmwarePath = f"firmware/{current['buildId']:08X}/PartBDebug.sof"
    selected[firmwarePath] = sof
    record = {"schema": "echo7-submission-v2", "scope": "Integrated B+C; physical switches; speech cancelled",
              "buildId": current["buildId"], "top": current["top"],
              "sof": firmwarePath, "sourceSof": build["sof"]["path"], "files": []}
    if args.datasheet:
        record["datasheet"] = datasheetBinding(args.datasheet, current)
        selected["echo7_datasheet.pdf"] = args.datasheet
    transcriptPayloads = {}
    if args.ai_transcript_manifest:
        record["aiTranscript"], transcriptPayloads = aiTranscriptBinding(args.ai_transcript_manifest, root)
    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(selected.items()):
            payload = path.read_bytes()
            archive.writestr(name, payload)
            record["files"].append(name)
        for name, payload in sorted(transcriptPayloads.items()):
            archive.writestr(name, payload)
            record["files"].append(name)
        archive.writestr("verified/build_record.json", json.dumps(record, indent=2) + "\n")
    with zipfile.ZipFile(out) as archive:
        if archive.testzip():
            raise RuntimeError("submission archive CRC failed")
    print(json.dumps({"status": "PASS", "path": str(out),
                      "files": len(selected) + len(transcriptPayloads), "scope": "ARCHIVE_INTEGRITY; does not add hardware acceptance"}, indent=2))


if __name__ == "__main__":
    main()
