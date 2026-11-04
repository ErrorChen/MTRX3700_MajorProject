"""Render the one-page integrated datasheet from the checked-in display metrics.

Run from any directory: python tools/render_integrated_datasheet.py
Dependencies: reportlab, pypdf. Pending measurements remain explicit.
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'ECHO7_Integrated_Datasheet.pdf'
METRICS = ROOT / 'docs' / 'integrated_datasheet_metrics.json'
metrics = json.loads(METRICS.read_text(encoding='utf-8')) if METRICS.exists() else {}
navy = colors.HexColor('#17324D')
teal = colors.HexColor('#137E88')
gray = colors.HexColor('#4E6070')
line = colors.HexColor('#D7E1E7')
light = colors.HexColor('#F2F6F8')
amber = colors.HexColor('#FFF3D9')
styles = {
 'body': ParagraphStyle('body', fontName='Helvetica', fontSize=8.4, leading=10.7, textColor=navy, spaceAfter=4),
 'small': ParagraphStyle('small', fontName='Helvetica', fontSize=7.6, leading=10, textColor=gray, spaceAfter=3),
 'label': ParagraphStyle('label', fontName='Helvetica-Bold', fontSize=9.6, leading=12, textColor=teal, spaceAfter=5),
 'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=8.1, leading=10.1, textColor=navy),
 'header': ParagraphStyle('header', fontName='Helvetica-Bold', fontSize=8.1, leading=10.1, textColor=colors.white),
}
def p(text, kind='body'): return Paragraph(text, styles[kind])
def field(key, fallback='PENDING - current hardware/build measurement'):
 return escape(str(metrics.get(key, fallback)))
def section(title, content):
 return [p(title,'label')] + [p(s) for s in content]
def table(rows, widths, header=False):
 data=[[p(str(c),'header' if header and n==0 else 'cell') for c in row] for n,row in enumerate(rows)]
 t=Table(data,colWidths=widths,hAlign='LEFT')
 commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('LINEBELOW',(0,0),(-1,-1),0.35,line)]
 if header: commands += [('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,light])]
 t.setStyle(TableStyle(commands));return t

width=A4[0]-72
story=[]
story.append(p('SYSTEM / CURRENT IMPLEMENTATION','label'))
story.append(p('<b>DE1-SoC + OV7670 + UGV02</b> | Cyclone V 5CSEMA5F31C6 | Production top: <b>echo7IntegratedTop</b>. One SOF selects real vision, synthetic-vision chassis debugging or integrated operation. Physical IR and J3 sonar always remain in the motion safety chain.'))
story.append(Spacer(1,6))
story.append(table([
 ['MODE','INPUT / OUTPUT'],
 ['INTEGRATED (power-up default)','Real camera; explicitly started tasks only. No host heartbeat required.'],
 ['VISION_ONLY','Real tracking/calibration; wheel UART remains zero, even without a valid sonar reading.'],
 ['CHASSIS_INJECT','JTAG observations at 25 Hz through the real C controller; physical IR/J3 remain active.'],
],[132,width-132],True))
story.append(Spacer(1,7))
left=section('CONTROLS & VISUAL WORKFLOW',[
 '<b>SW0-SW5:</b> one-hot bay 1-6; approximately 20 ms stability. No selection/conflict cannot move. Selection changes cancel the task; valid selection tracks before ARM.',
 '<b>SW6/SW7:</b> candidate / centre RGB-HSV diagnostics. All 16 candidates appear on two 8-slot pages, about 2 s/page. <b>SW8:</b> perspective bypass. <b>SW9:</b> raw display, cancel motion.',
 '<b>Red1:</b> colour calibration. <b>Red2:</b> reselect the current switches and request a new task. Uncalibrated mode waits for a new 3-frame target lock. Remove the card for 3 healthy frames before presenting it for 3 frames; a resident card does not start at reset.',
 '<b>IR A (0x0F):</b> latched stop. <b>POWER (0x12):</b> first fresh press releases an IR stop; a second press starts. Repeats/held POWER do not start twice. <b>KEY0:</b> full reset.',
])
right=section('MOTION & STOP CONDITIONS',[
 '<b>Search:</b> opposite logical wheel requests at 4 cm/s. First valid observation stops rotation; await a complete zero-speed JSON, then 200 ms conservative dwell and 3 new independent frames.',
 '<b>Alignment:</b> U=110-130 centred (U range 0-239). <b>Approach:</b> 5 cm/s above 500 mm; 3 cm/s at 350-500 mm. <b>Dock:</b> 350 mm with an aligned, locked target.',
 '<b>Guard:</b> distance &lt;=250 mm, invalid or stale data stops motion. HOLD recovery needs 3 new safe samples &gt;=300 mm. DOCKED/NOT_FOUND stay disarmed until a new start.',
 '<b>Freshness:</b> visual reports about 150 ms; injection lease 500 ms (host renewal about 100 ms). Lost lease cancels ARM; renewed heartbeat does not restart. UART: 115200 8N1, complete JSON, zero-speed priority.',
])
columns=Table([[left,right]],colWidths=[width/2,width/2]);columns.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),('RIGHTPADDING',(0,0),(0,0),12),('LEFTPADDING',(1,0),(1,0),12),('RIGHTPADDING',(1,0),(1,0),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('LINEBEFORE',(1,0),(1,0),0.5,line)]))
story.append(columns)
story.append(Spacer(1,7))
scan=Table([[p('<b>SCAN_UNCALIBRATED:</b> no verified heading feedback or three-trial floor calibration. The default 10 s is a bounded injection-debug budget, not a measured 360 degrees. INTEGRATED blocks unseen-target scanning until calibrated; an already locked visible target may still dock. Search has a 120 s total task limit.','cell')]],colWidths=[width]);scan.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),amber),('BOX',(0,0),(-1,-1),0.4,colors.HexColor('#E5CF9E')),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(scan)
story.append(Spacer(1,7))
story.append(p('EVIDENCE / CURRENT BUILD & HARDWARE','label'))
story.append(table([
 ['CHECK','RESULT / LIMIT'],
 ['Directed control & protocols','PASS: control 254 checks; CCTL 58 checks. Complete UART bytes decoded.'],
 ['Earlier pin-level simulation','PASS on pre-red2 RTL: 9 sonar model measurements; 3 moving / 6 zero UART lines. NEC repeat/release checked; 97.734 s runtime.'],
 ['Pixel-to-UART system','PASS: 12 fixed-rate 25 fps frames through perceptionCore, real C and UART. Synthetic pixels; not a live-camera acceptance.'],
 ['Course R6',field('r6','PENDING - fresh Verilator 5.050 clean-copy run; 300 s limit')],
 ['Quartus fit / timing',field('fit')],
 ['Current-board raised checks',field('hardware')],
 ['Earlier wheel / IR checks',field('hardware_prior','PENDING')],
],[132,width-132],True))
story.append(Spacer(1,7))
story.append(p('<b>Unmeasured:</b> floor 360-degree repeatability, six-bay closed-loop trials, physical docking error, scene-to-UART latency, real no-echo response and SW8 comparison. Transient visual loss and historical frame30321 blue6 fragmentation remain limitations.','small'))
story.append(p('<b>Current SOF:</b> '+field('sof','PENDING - use only the successful current compilation output')+'<br/><b>Reproduction:</b> README.md / README_EN.md; docs/REPAIR_RESULT.md; tools/render_integrated_datasheet.py. No direct wheel or synthetic-distance override.','small'))

def decorate(canvas,doc):
 canvas.setFillColor(navy);canvas.rect(0,A4[1]-79,A4[0],79,fill=1,stroke=0)
 canvas.setFillColor(colors.white);canvas.setFont('Helvetica-Bold',25);canvas.drawString(36,A4[1]-38,'ECHO-7')
 canvas.setFont('Helvetica',11);canvas.drawString(36,A4[1]-58,'Integrated vision-guided bay search and docking')
 canvas.setFont('Helvetica',8);canvas.drawRightString(A4[0]-36,A4[1]-35,'DATASHEET / 04 NOV 2026')
 canvas.drawRightString(A4[0]-36,A4[1]-50,'Design E7070004 / CCTL E7070001')
 canvas.setStrokeColor(line);canvas.line(36,29,A4[0]-36,29)
 canvas.setFillColor(gray);canvas.setFont('Helvetica',7);canvas.drawString(36,17,'Simulation, programmed-board state and physical vehicle results are reported separately.')
 canvas.drawRightString(A4[0]-36,17,'1 / 1')
doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=36,leftMargin=36,topMargin=94,bottomMargin=38,title='ECHO-7 Integrated Datasheet',author='ECHO-7 project team; AI-assisted compilation')
doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
reader=PdfReader(str(OUT));assert len(reader.pages)==1, f'Expected one page, got {len(reader.pages)}'
print(f'Created {OUT}; pages={len(reader.pages)}')
