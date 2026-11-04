"""Render ECHO-7's operating guide plus a separate one-page formal R5 sheet.

Run from any directory: python tools/render_integrated_datasheet.py
Dependencies: reportlab, pypdf. The integrated PDF contains the product page
and the formal R5 page. Pass the separate R5 PDF to export_submission --datasheet.
Missing measurements/claimed grade remain PENDING, never inferred from tests.
"""
from io import BytesIO
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/ECHO7_Integrated_Datasheet.pdf"
R5_OUT = ROOT / "docs/ECHO7_R5_Datasheet.pdf"
R5_SPEC = ROOT / "tools/data/echo7_r5_targets.json"
header = (ROOT / "rtl/common/memberBBuildId.svh").read_text(encoding="utf-8")
BUILD_ID = re.search(r"MEMBER_B_BUILD_ID\s+32'h([0-9A-Fa-f]{8})", header).group(1).upper()
NAVY, TEAL, GRAY = map(colors.HexColor, ("#17324D", "#117C86", "#4E6070"))
LINE, PALE, AMBER = map(colors.HexColor, ("#D7E1E7", "#F1F6F8", "#FFF3D9"))
# SimpleDocTemplate's frame has 6 pt internal padding on each side.
WIDTH, GAP = A4[0] - 68, 18
COL = (WIDTH - GAP) / 2
STYLES = {
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.0,
        leading=11.1, textColor=NAVY, spaceAfter=4),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8.0,
        leading=9.7, textColor=GRAY, spaceAfter=3),
    "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=10,
        leading=12, textColor=TEAL, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.8,
        leading=10.7, textColor=NAVY),
    "head": ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8.8,
        leading=10.7, textColor=colors.white),
}


def p(text, kind="body"):
    return Paragraph(text, STYLES[kind])


def table(rows, widths, header=False, padding=4):
    data = [[p(str(value), "head" if header and index == 0 else "cell")
             for value in row] for index, row in enumerate(rows)]
    result = Table(data, colWidths=widths, hAlign="LEFT")
    commands = [("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE)]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), NAVY),
                     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE])]
    result.setStyle(TableStyle(commands))
    return result


def signal_path():
    drawing = Drawing(WIDTH, 43)
    nodes = [(0, 130, "OV7670 camera", "Live colour image"),
        (153, 232, "DE1-SoC FPGA", "Cyclone V 5CSEMA5F31C6 | vision + control"),
        (408, WIDTH - 408, "UGV02 chassis", "Differential-wheel motion")]
    for x, width, title, subtitle in nodes:
        drawing.add(Rect(x, 4, width, 36, rx=4, ry=4,
                         fillColor=PALE, strokeColor=LINE, strokeWidth=0.6))
        drawing.add(String(x + width / 2, 25, title, textAnchor="middle",
                           fontName="Helvetica-Bold", fontSize=9.5, fillColor=NAVY))
        drawing.add(String(x + width / 2, 12, subtitle, textAnchor="middle",
                           fontName="Helvetica", fontSize=7.2, fillColor=GRAY))
    for x1, x2 in ((132, 151), (387, 406)):
        drawing.add(Line(x1, 22, x2 - 4, 22, strokeColor=TEAL, strokeWidth=1.5))
        drawing.add(Polygon([x2 - 5, 25, x2, 22, x2 - 5, 19], fillColor=TEAL, strokeColor=TEAL))
    return drawing


def display_example():
    drawing = Drawing(COL, 42)
    for x, width, value, caption in [(0, 39, "d", "page"), (45, 39, "1", "mode"),
                                    (90, COL - 90, "0520", "four data digits")]:
        drawing.add(Rect(x, 13, width, 27, rx=3, ry=3, fillColor=NAVY, strokeColor=None))
        drawing.add(String(x + width / 2, 20, value, textAnchor="middle",
                           fontName="Courier-Bold", fontSize=17, fillColor=colors.white))
        drawing.add(String(x + width / 2, 3, caption, textAnchor="middle",
                           fontName="Helvetica", fontSize=7.4, fillColor=GRAY))
    return drawing


story = [
    p("Choose a blue bay marker and start a task. ECHO-7 searches, confirms the marker, aligns, "
      "approaches and parks, with live VGA feedback, remote stop and front sonar protection."),
    signal_path(),
    p("<b>Also fitted:</b> J3 RCWL-1601 sonar, NEC IR receiver/remote, VGA monitor, switches, keys, LEDs "
      "and six-digit display. USB-Blaster provides PC download/debug. Chassis UART: 115200 8N1, "
      "3.3 V logic, common ground.", "small"),
    Spacer(1, 3), p("THREE OPERATING MODES", "label"),
    table([
        ["MODE / DISPLAY CODE", "PURPOSE"],
        ["<b>0 - INTEGRATED</b>", "Camera-guided driving. Choose one bay; POWER or red2 starts a new task. "
         "Default after power-up/reset, with motion disarmed."],
        ["<b>1 - VISION_ONLY</b>", "Live recognition, tracking, calibration and VGA; wheel commands stay zero. "
         "Use for marker and camera setup."],
        ["<b>2 - CHASSIS_INJECT</b>", "PC/JTAG virtual targets test the same controller. Real IR and sonar stay active; "
         "loss of the PC injection session stops motion."],
    ], [133, WIDTH - 133], header=True),
    p("Choose modes with the JTAG debug tool. Changing mode stops the task. "
      "INTEGRATED needs no PC heartbeat.", "small"), Spacer(1, 5),
]

left = [
    p("RED AND BLUE MARKERS", "label"),
    p('<font color="#205AA7"><b>Blue 1-6: destination bays.</b></font> '
      "SW0-SW5 choose one number to follow. Keep its complete border and white anchor visible."),
    p('<font color="#AF3939"><b>Red1: colour calibration.</b></font> '
      "Hold red1 and its paired blue reference stripe steady. Motion pauses until calibration finishes: <b>CAL:Y</b>. "
      "The stripe label <b>BJ</b> is not a bay."),
    p('<font color="#AF3939"><b>Red2: reselect and start.</b></font> '
      "Re-read switches, relock and request a task. Remove it, then present it beside the target. "
      "It cannot choose a bay or restart an active task. Keep hands/cards clear of J3."),
    Spacer(1, 4), p("SWITCHES AND BUTTONS", "label"),
    table([
        ["<b>SW0-SW5</b>", "SW0/1/2/3/4/5 select blue 1/2/3/4/5/6. <b>Exactly one ON</b> to start. "
         "Changing selection cancels motion."],
        ["<b>SW6</b>", "Candidate colour/number diagnostics."],
        ["<b>SW7</b>", "Centre colour sample and marker identity."],
        ["<b>SW8</b>", "0: normal perspective handling.<br/>1: bounding-box recognition bypass."],
        ["<b>SW9</b>", "Camera-only display; cancels motion. OFF requires a new start to move again."],
        ["<b>KEY0 / KEY1</b>", "KEY0: full reset. KEY1: next display page."],
    ], [64, COL - 64], padding=3), Spacer(1, 5),
    p("<b>Remote POWER:</b> start. <b>A:</b> latched emergency stop. After A, one fresh POWER releases it; "
      "release and press again to start. Holding POWER cannot do both."),
    p("<b>PC/JTAG:</b> In stopped, disarmed VISION_ONLY, use <b>tune</b> for speeds/centring and <b>pulse</b> "
      "for short turns; <b>policy</b> sets corridor, dwell and normal stop/slow distances. Commands: README.", "small"),
]

right = [
    p("WHAT THE VGA IMAGE SHOWS", "label"),
    p("Upright camera image with red/blue contours and labels <b>R1/R2</b>, <b>B1-B6</b> or <b>BJ</b>. "
      "<b>CAL:W/B/Y</b> = waiting/calibrating/calibrated. <b>FRAME:GOOD/BAD/STALE</b> = image health. "
      "<b>STATE</b> = calibration interaction, not navigation."),
    p("<b>SW6:</b> RGB/HSV, colour, number or UNKNOWN, rejection code E. PAGE:1/2 alternates every "
      "2 s across 16 slots, identified by yellow sample marks."),
    p("<b>SW7:</b> white 8 x 8 centre sample: RGB/HSV and the complete marker covering it. "
      "<b>SW8:</b> BYPASS:1 changes recognition, not camera view or safety. <b>SW9:</b> hides overlays."),
    Spacer(1, 4), p("READING THE SIX-DIGIT DISPLAY", "label"), display_example(),
    p("<b>d1 0520</b> = distance page, VISION_ONLY, <b>520 mm</b>. "
      "The second digit is the mode code above, not the bay number.", "small"),
    table([
        ["<b>d</b>", "Millimetres. <b>FAr</b> = valid out-of-range, not measured 4 m. "
         "Four blank digits = invalid distance."],
        ["<b>H</b>", "Last IR word, upper half in hexadecimal. Right pair <b>12</b> = POWER, <b>0F</b> = A "
         "(examples ED12 / F00F)."],
        ["<b>L</b>", "Last IR word, lower/address half in hexadecimal. H/L are blank until a complete valid IR word arrives."],
    ], [23, COL - 23], padding=3),
    p("<b>KEY1:</b> d - H - L - d. Left digit <b>n</b> = stable no-selection; <b>C</b> = stable "
      "multi-switch conflict, replacing the page letter. No ARM or driving-state page.", "small"),
    p("<b>LEDs:</b> 0 motion permitted; 1 IR stop latched; 3 docked; 8 target locked and fresh.", "small"),
]

columns = Table([[left, right]], colWidths=[COL + GAP / 2, COL + GAP / 2])
columns.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), GAP / 2),
    ("LEFTPADDING", (1, 0), (1, 0), GAP / 2), ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ("LINEBEFORE", (1, 0), (1, 0), 0.5, LINE),
]))
story.extend([columns, Spacer(1, 3)])
limits = table([
    ["<b>APPROACH / STOP</b>  Boot: 5 cm/s far, 4 cm/s near 500 mm; centre tolerance +/-30 px. "
     "Normal dock &lt;=350 mm requires a new task to move again. Stationary <b>policy</b>: corridor45-70 px, "
     "dwell500-2000 ms, stop300-400 mm, slow500-1000 mm; boot45/1500/350/500. "
     "Fixed obstacle HOLD &lt;=250 mm; release after three fresh &gt;=300 mm readings. Invalid/stale range and IR A stop."],
    ["<b>ADJUSTABLE SHORT TURN</b>  ALIGN kick3-8 cm/s for0-100 ms, then cruise3-5 cm/s. "
     "Total min/max20-300 ms includes kick; time steps10 ms. E14 boot: total200/200 ms, kick60 ms at6 cm/s, cruise4. "
     "A qualified gap may finish the original &lt;=200 ms turn, without extension/re-kick. Faults, IR/J3 and a trusted crossing stop it. "
     "APPROACH loss stops; new-frame confirmation follows zero dwell."],
    ["<b>SEARCH / RESET</b>  Boot scan3 cm/s,15.1 s is a historical plastic-floor time profile, not exact360 degrees. "
     "Up to three150 ms reverse steps share its budget. Search-speed changes invalidate qualification. "
     "KEY0 restores production values, colour calibration and zero-then-T131 initialization. Red2 must leave then re-enter. "
     "PC tune/pulse --defaults restore older generic values, not this boot profile. See README for exact ranges/steps."],
], [WIDTH], padding=7)
limits.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMBER),
    ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#E5CF9E"))]))
story.append(limits)


def decorate(canvas, doc):
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 65, A4[0], 65, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 25)
    canvas.drawString(28, A4[1] - 31, "ECHO-7")
    canvas.setFont("Helvetica", 10.5)
    canvas.drawString(28, A4[1] - 49, "Visual bay finding and docking | Product & operating guide")
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(A4[0] - 28, A4[1] - 29, "DE1-SoC / OV7670 / UGV02")
    canvas.setStrokeColor(LINE)
    canvas.line(28, 24, A4[0] - 28, 24)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(28, 13, "Source guide " + BUILD_ID + " | Commands and limitations: project README | Formal R5 follows")
    canvas.drawRightString(A4[0] - 28, 13, "Product guide")


product_buffer = BytesIO()
doc = SimpleDocTemplate(product_buffer, pagesize=A4, rightMargin=28, leftMargin=28,
    topMargin=76, bottomMargin=32, title="ECHO-7 Product and Operating Guide",
    author="ECHO-7 project team; AI-assisted documentation")
doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
product = PdfReader(product_buffer)
assert len(product.pages) == 1, f"Product guide overflowed to {len(product.pages)} pages"


def render_r5():
    spec = json.loads(R5_SPEC.read_text(encoding="utf-8"))
    assert spec["schema"] == "echo7-r5-target-specification-v1"
    assert spec["sourceBuildId"] == BUILD_ID, "Update R5 source/evidence scope before changing its build label"
    targets = spec["targets"]
    assert 3 <= len(targets) <= 5
    fields = [("Quantity + unit", "quantityUnit"), ("Test conditions", "conditions"),
              ("Three-trial scoring rule", "threeTrialRule"), ("Threshold", "threshold"),
              ("Goal", "goal"), ("Predicted value", "predictedValue"),
              ("Measured value", "measuredValue"), ("Claimed grade level", "claimedGradeLevel")]
    for target in targets:
        assert all(isinstance(target[key], str) and target[key].strip() for _, key in fields)
        if not target["currentTrials"]:
            assert target["acceptanceStatus"] == "PENDING"
            assert "PENDING" in target["measuredValue"]
    width = A4[0] - 52
    r5_title = ParagraphStyle("r5title", fontName="Helvetica-Bold", fontSize=17, leading=20,
                              textColor=NAVY, spaceAfter=5)
    r5_body = ParagraphStyle("r5body", fontName="Helvetica", fontSize=8.3, leading=10.5,
                             textColor=NAVY, spaceAfter=5)
    r5_small = ParagraphStyle("r5small", parent=r5_body, fontSize=7.6, leading=9.6, spaceAfter=4)
    r5_cell = ParagraphStyle("r5cell", parent=r5_body, fontSize=8.2, leading=10.4, spaceAfter=0)
    r5_head = ParagraphStyle("r5head", parent=r5_cell, fontName="Helvetica-Bold", textColor=colors.white)
    r5_label = ParagraphStyle("r5label", parent=r5_cell, fontName="Helvetica-Bold", textColor=TEAL)
    rp = lambda value, style=r5_body: Paragraph(value, style)
    items = [rp("ECHO-7 | R5 MEASURABLE TARGETS", r5_title),
             rp(f"Source <b>{BUILD_ID}</b> | Prospective acceptance specification | {escape(spec['declaredDate'])}"),
             rp("<b>Robot:</b> OV7670 pixels -> DE1-SoC recognition/calibration -> target qualification and motion FSM "
                "-> UGV02 UART. SW0-SW5 choose a blue bay; IR A and J3 protect motion.", r5_small),
             rp("<b>Claimed grade level: " + escape(spec["claimedGradeLevel"]) + ".</b> "
                "Current three-trial scores are pending. Historical E4/E12 observations below do not certify this revision.", r5_body)]
    rows = [[rp("Required field", r5_head)] +
            [rp(escape(t["id"] + " - " + t["shortName"]), r5_head) for t in targets]]
    for label, key in fields:
        row = [rp(escape(label), r5_label)]
        for target in targets:
            value = escape(target[key]).replace("PENDING", "<b>PENDING</b>")
            row.append(rp(value, r5_cell))
        rows.append(row)
    matrix = Table(rows, colWidths=[68] + [(width - 68) / len(targets)] * len(targets), repeatRows=1)
    matrix.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    items += [matrix, Spacer(1, 6),
              rp("<b>Common rule:</b> The tutor chooses within each range. Record all three trials; never select the best. "
                 "T1/T2 may share captures. Use first distinct reports, retain failed/missing results and reject duplicate frame IDs. "
                 "Plan about 90 s per target; T4 has a 25 s/run cap. Demonstrate IR safety before driving.", r5_small),
              rp("<b>Prediction / scope:</b> Estimates are prospective, not historical predictions. T2 excludes scene-to-UART and mechanical latency. "
                 "T4 covers already-visible targets only; a complete outside-view search-to-dock demonstration remains separate and unpassed. "
                 "Do not join partial runs or treat command speeds as measured wheel speeds.", r5_small),
              rp("<b>Contribution / R9:</b> T1/T2 cover the projective/anchor reader and perception pipeline; T3 covers real-pixel calibration; "
                 "T4 covers target qualification and motion decisions. Repeat T1 with SW8=1 under matched conditions. "
                 "If bypass also meets threshold, this target does not establish that stage's necessity.", r5_small),
              rp("<b>Sources:</b> Major_Project_Brief_2026.pdf: pp 3-4 R5/2.3 (target rules), pp 4/6 2.4/4 (level and evidence), "
                 "p 7 submission. All numeric thresholds/goals are project choices: T1-T3 retained from render_member_b_datasheet.py; "
                 "T4 newly declares 350 mm +/-50 mm threshold /+/-20 mm goal. Detailed provenance: docs/R5_TARGETS.md; "
                 "editable specification: tools/data/echo7_r5_targets.json.", r5_small)]

    def r5_footer(canvas, document):
        canvas.setStrokeColor(LINE)
        canvas.line(20, 22, A4[0] - 20, 22)
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(20, 12, "ECHO-7 | " + BUILD_ID + " | Formal definition is not hardware acceptance")
        canvas.drawRightString(A4[0] - 20, 12, "R5 - one page")

    r5_buffer = BytesIO()
    r5_doc = SimpleDocTemplate(r5_buffer, pagesize=A4, leftMargin=20, rightMargin=20,
                              topMargin=20, bottomMargin=28, title="ECHO-7 R5 Measurable Targets",
                              author="ECHO-7 project team; AI-assisted documentation")
    r5_doc.build(items, onFirstPage=r5_footer, onLaterPages=r5_footer)
    data = r5_buffer.getvalue()
    r5_reader = PdfReader(BytesIO(data))
    assert len(r5_reader.pages) == 1, f"Formal R5 sheet overflowed to {len(r5_reader.pages)} pages"
    return data


r5_data = render_r5()
R5_OUT.write_bytes(r5_data)
combined = PdfWriter()
combined.add_page(product.pages[0])
combined.add_page(PdfReader(BytesIO(r5_data)).pages[0])
combined.add_metadata({"/Title": "ECHO-7 Product Guide and Formal R5 Targets",
                       "/Author": "ECHO-7 project team; AI-assisted documentation"})
with OUT.open("wb") as stream:
    combined.write(stream)
assert len(PdfReader(OUT).pages) == 2
print(f"Created {OUT}; pages=2; source={BUILD_ID}")
print(f"Created {R5_OUT}; pages=1; formal measurements/grade remain pending")
