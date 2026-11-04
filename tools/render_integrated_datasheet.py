"""Render the one-page ECHO-7 product and operating guide.

Run from any directory: python tools/render_integrated_datasheet.py
Dependencies: reportlab, pypdf. Build/test evidence remains in the README and
repair record; this page explains the product, controls and displays.
"""
from pathlib import Path
import re

from pypdf import PdfReader
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/ECHO7_Integrated_Datasheet.pdf"
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
      "The matching switch selects the number to follow. Keep the complete border and white anchor visible."),
    p('<font color="#AF3939"><b>Red1: colour calibration.</b></font> '
      "Show red1 with its paired blue reference stripe, steadily. Motion pauses during calibration; wait for <b>CAL:Y</b>. "
      "The stripe is labelled <b>BJ</b>; it is not a bay."),
    p('<font color="#AF3939"><b>Red2: reselect and start.</b></font> '
      "Re-read the switches, relock and request a task. Move it out, then present it once beside the target. "
      "It does not choose a bay or restart an active task. Keep hands/cards clear of J3."),
    Spacer(1, 4), p("SWITCHES AND BUTTONS", "label"),
    table([
        ["<b>SW0-SW5</b>", "SW0/1/2/3/4/5 select blue 1/2/3/4/5/6. <b>Exactly one ON.</b> "
         "No selection/multiple selections cannot start. Changing selection cancels motion."],
        ["<b>SW6</b>", "Candidate colour/number diagnostics."],
        ["<b>SW7</b>", "Centre colour sample and marker identity."],
        ["<b>SW8</b>", "0: normal perspective handling.<br/>1: bounding-box recognition bypass."],
        ["<b>SW9</b>", "Camera-only display; cancels motion. OFF requires a new start to move again."],
        ["<b>KEY0 / KEY1</b>", "KEY0: full reset. KEY1: next display page."],
    ], [64, COL - 64], padding=3), Spacer(1, 5),
    p("<b>Remote POWER:</b> start. <b>A:</b> latched emergency stop. After A, the first fresh POWER only "
      "releases the stop; release the key, then press POWER again to start. Holding POWER does not do both."),
]

right = [
    p("WHAT THE VGA IMAGE SHOWS", "label"),
    p("Upright camera image, red/blue colour contours and accepted labels <b>R1/R2</b>, <b>B1-B6</b>, "
      "or <b>BJ</b>. <b>CAL:W/B/Y</b> = waiting/calibrating/calibrated. "
      "<b>FRAME:GOOD/BAD/STALE</b> reports image health. <b>STATE</b> is the calibration interaction state, not driving state."),
    p("<b>SW6:</b> RGB/HSV, colour, number or UNKNOWN, and rejection code E. "
      "PAGE:1/2 alternates about every 2 s across 16 slots; yellow sample marks identify slots."),
    p("<b>SW7:</b> white 8 x 8 centre sample with RGB/HSV and the identity of a complete marker covering it. "
      "<b>SW8:</b> BYPASS:1 changes recognition, not the camera view or safety. <b>SW9:</b> removes overlays."),
    Spacer(1, 4), p("READING THE SIX-DIGIT DISPLAY", "label"), display_example(),
    p("<b>d1 0520</b> = distance page, VISION_ONLY, <b>520 mm</b>. "
      "The second digit is the mode code above, not the bay number.", "small"),
    table([
        ["<b>d</b>", "Decimal millimetres. <b>FAr</b> = valid out-of-range indication, not a measured 4 m. "
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
story.extend([columns, Spacer(1, 6)])
limits = table([
    ["<b>APPROACH / STOP</b>  Nominally 5 cm/s, slowing to 3 cm/s inside 500 mm. A centred, locked target "
     "at 350 mm or closer ends the task; a new start is needed to move again. At 250 mm or less, invalid/stale range, "
     "or IR A, motion stops. Obstacle HOLD can recover after three new readings at least 300 mm; losing the target stops forward travel."],
    ["<b>SEARCH / RESET</b>  An unseen target uses bounded low-speed search. After a search sighting: stop, wait and reconfirm. "
     "If confirmation fails after losing the target, up to three 150 ms reverse steps may recover it; each stops to reconfirm "
     "and spends the same scan budget. Reset/power loss clears colour and floor scan calibration: restore the scan setting from the PC before "
     "unseen-target search. Visible, locked targets can still be approached. Search is approximate, not an angle-controlled 360-degree guarantee."],
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
    canvas.drawString(28, 13, "Firmware guide " + BUILD_ID + " | Setup commands and limitations: project README")
    canvas.drawRightString(A4[0] - 28, 13, "1 / 1")


doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=28, leftMargin=28,
    topMargin=76, bottomMargin=32, title="ECHO-7 Product and Operating Guide",
    author="ECHO-7 project team; AI-assisted documentation")
doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
reader = PdfReader(str(OUT))
assert len(reader.pages) == 1, f"Expected one page, got {len(reader.pages)}"
print(f"Created {OUT}; pages={len(reader.pages)}; firmwareGuide={BUILD_ID}")
