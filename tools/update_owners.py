#!/usr/bin/env python3
"""Regenerate the reviewed R8 inventory; identities come from user confirmation.

This assigns maintenance responsibility, not sole authorship or human sign-off.
Original file notices override the coarse provenance category below.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
TEAM_FILES = {
    "rtl/capture/clock_divider.sv", "rtl/capture/i2c_master.sv",
    "rtl/capture/ov7670_config.sv", "rtl/capture/ov7670_capture.sv",
    "rtl/common/camera_pkg.sv", "rtl/common/video_pll.sv",
    "rtl/display/frame_buffer.sv", "rtl/display/camera_display.sv",
    "quartus/vga_sink.qsys",
}
STAFF_FILES = {
    "rtl/debug/frame_snap.sv", "rtl/debug/snapshot_ram.sv",
    "rtl/debug/snapshot_probes.sv", "tools/capture/grab.py", "tools/tcl/grab_jtag.tcl",
}

# Member A (Hajin Paek) Part A front end; ownership confirmed by Hajin Paek on 4 November 2026.
# Each origin records what Member B changed during integration, from the git history.
MEMBER_A_SID = "540287235"
PART_A = "Member A (Hajin Paek) Part A front end, AI-assisted (OpenAI Codex)"
PART_A_FILES = {
    "rtl/vision/causalMaskCleanup.sv": PART_A + "; unchanged from Part A",
    "tools/lib/candidates_model.py": PART_A + "; unchanged from Part A",
    "tools/lib/analyse_capture.py": PART_A + "; unchanged from Part A",
    "rtl/vision/candidate_pkg.sv": PART_A + "; Member B renamed it and raised MAX_CANDIDATES from 8 to 16",
    "rtl/vision/boundedCandidates.sv": PART_A + "; Member B extended it to a shared 16-slot pool with a 15-handle active cap",
    "tests/rtl/boundedCandidates_tb.sv": PART_A + "; Member B extended it for the shared 16-slot pool",
    "tools/lib/candidates_reclaimed_model.py": PART_A + "; Member B extended it for the shared 16-slot pool",
    "tests/python/test_reclaimed_model.py": PART_A + "; Member B added repository imports and one adversarial-union test",
}


INTEGRATION_FILES = {
    "rtl/top/echo7IntegratedTop.sv", "rtl/debug/chassisDebug.sv", "rtl/debug/syntheticPerception.sv",
    "quartus/MemberCIntegration.sdc", "tools/chassis_debug.py", "tools/tcl/chassis_session.tcl",
    "tools/echo7.py", "tools/check_repository.py", "tools/export_submission.py",
    "tools/compare_observations.py", "tests/python/test_observation_comparison.py",
    "tests/python/test_autodebug.py", "tests/python/test_submission.py",
    "tools/lib/verilator_suite.py", "tools/run_r6_windows.py", "run_all_tests.sh",
    "tools/render_integrated_datasheet.py",
    "tools/update_owners.py", "tools/validate_member_c_interface.py",
    "tests/python/test_chassis_debug.py", "tests/python/test_chassis_tcl.py", "tests/python/test_chassis_tools.py",
}


def maintainer(name):
    if name in PART_A_FILES:
        return MEMBER_A_SID, PART_A_FILES[name]
    if name.startswith(("rtl/member_c/", "tests/member_c/")):
        return "Member C SID pending", "Inherited Member C/teacher driver notices retained; control repairs and tests AI-assisted"
    if name in INTEGRATION_FILES or name.startswith(("tests/integration/", "tests/scheme_c/")):
        return "B 540207680; A/C SID pending", "B+C integration/JTAG/test adaptation, AI-assisted; no unconfirmed human identity or hardware sign-off"
    return "540207680", None


def main():
    manifest = json.loads((ROOT / "tests/rtl/manifest.json").read_text())
    paths = []
    for folder in ("rtl", "tools", "tests", "quartus", "assets/markers"):
        paths += [p for p in (ROOT / folder).rglob("*") if p.is_file() and
                  p.suffix in (".sv", ".svh", ".py", ".tcl", ".qpf", ".qsf", ".sdc", ".qsys", ".json")
                  and "__pycache__" not in p.parts and not any(part in ("db", "incremental_db", "output_files", "vga_sink") for part in p.parts)]
    paths += [ROOT / name for name in ("run_all_tests.sh", "requirements.txt", ".gitignore", ".gitattributes", ".editorconfig")]
    paths += list((ROOT / "tests/fixtures/camera").rglob("*.png"))
    lines = ["# ECHO-7 ownership and provenance", "",
        "Member A is Hajin Paek, SID **540287235**, owner of the Part A front-end files listed below.",
        "SID **540207680** is the user-confirmed Member B maintainer. The Member C SID is **pending**.",
        "The preliminary repository was built by same-group students Hajin and Jiaze Sun.",
        "Origin is separate from maintenance responsibility. Original source/IP notices",
        "remain applicable. B additions and adaptations are AI-assisted; named human",
        "review/sign-off is **pending**, not certified by this generated inventory.", "",
        "Source: user statement on 3 November 2026; Member A identity and Part A ownership",
        "confirmed by Hajin Paek on 4 November 2026; original notices and",
        "ROOT README.md / VERSION_README.md preserve consolidated provenance. Regenerate with",
        "`python tools/update_owners.py` after adding a maintained source or test.", "",
        "| File | Maintainer / SID | Origin / adaptation | Verification entry (not an execution claim) |",
        "|---|---|---|---|"]
    for path in sorted(set(paths)):
        name = path.relative_to(ROOT).as_posix()
        if name in TEAM_FILES:
            origin = "Hajin + Jiaze Sun same-group preliminary code / course IP notices; B integration and selective adaptation"
        elif name in STAFF_FILES:
            origin = "Course FrameGrab V2026.1; notices retained; B schema/control/decoder integration"
        elif name.startswith("assets/"):
            origin = "User-supplied one-page PDF; B geometry/template recovery and generation"
        elif name.startswith("tests/fixtures/camera/"):
            origin = "Same-team recorded OV7670 pixels of user-provided physical signs; B host-only annotations/profile metadata, AI-assisted; per-input provenance in camera/manifest.json"
        else:
            origin = "Member B implementation/adaptation, AI-assisted; not a sole-human-authorship claim"
        owner, integrationOrigin = maintainer(name)
        if integrationOrigin: origin = integrationOrigin
        benches = [test["name"] for test in manifest["tests"] if name in test["sources"]]
        if benches:
            check = ", ".join(benches[:3]) + ("; full mapping: tests/rtl/manifest.json" if len(benches)>3 else "")
        elif name.startswith("tests/python/"):
            check = "python -m unittest discover -s tests/python"
        elif name.startswith("tests/rtl/"):
            check = "tests/rtl/manifest.json; standalone preview benches are not acceptance tests"
        elif name.startswith("quartus/") or name.startswith("rtl/"):
            check = "echo7.py build; post-fit timing/CDC/resource gate and board validation"
        else:
            check = "Python suite / check_repository.py; command execution evidence remains separate"
        lines.append(f"| `{name}` | {owner} | {origin} | {check} |")
    (ROOT / "OWNERS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Updated OWNERS.md: {len(set(paths))} individual files; human review pending")


if __name__ == "__main__":
    main()
