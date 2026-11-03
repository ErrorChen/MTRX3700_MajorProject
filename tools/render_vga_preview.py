#!/usr/bin/env python3
"""Replay a real capture through production VGA RTL; output is NOT VGA_PHYSICAL."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import echo7


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path,help="echo7 capture result.json")
    parser.add_argument("--switches",type=int,choices=range(4),default=3)
    parser.add_argument("--raw-camera",action="store_true",help="Replay SW9 pure-camera routing; this remains RTL evidence only")
    parser.add_argument("--modelsim-bin")
    args=parser.parse_args()
    record=json.loads(args.capture.read_text(encoding="utf-8"))
    # Retained evidence/submission archives keep result.json beside capture/.
    # Never depend on the original workstation's absolute outputDirectory.
    folder=args.capture.resolve().parent
    imagePath=folder/"capture/frame.png"
    image=Image.open(imagePath).convert("RGB")
    if image.size!=(320,240) or not record.get("recognition",{}).get("sameFrameVerified"):
        raise RuntimeError("preview needs a frame-bound, decoded native capture")
    # Independently recheck the binary CRC and exact RGB/metadata binding. A
    # same-length JSON file beside an unrelated PNG is not a replay source.
    spec=importlib.util.spec_from_file_location("preview_grab",echo7.ROOT/"tools/capture/grab.py")
    grab=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grab)
    dump=(folder/"capture/dump.bin").read_bytes()
    decoder=grab.decode(dump)
    if decoder["offset"]!=0 or decoder["bytes"]!=len(dump):
        raise RuntimeError("preview input has prefix/trailing GRAB bytes")
    from debug_decode import decodeGrabWords
    decoded=decodeGrabWords(decoder["results"],record["recognition"]["buildId"])
    if decoded["debugSchemaVersion"]!=7 or decoded["statusWordCount"]!=96:
        raise RuntimeError("current VGA RTL preview requires schema7; historical previews retain their original source")
    if decoded["frameId"]!=record["frameId"] or decoded["configVersion"]!=record["recognition"]["configVersion"]:
        raise RuntimeError("preview record and binary describe different frames/configurations")
    if not np.array_equal(np.asarray(image),grab.frame_rgb(decoder["pixels"])):
        raise RuntimeError("preview PNG pixels differ from the CRC-checked binary")
    runner=echo7.Runner(argparse.Namespace(command="vga_rtl_preview",timeout=180,modelsim_bin=args.modelsim_bin))
    out=runner.out
    source=np.asarray(image,dtype=np.uint32)
    screen=np.zeros((480,640,3),dtype=np.uint32)
    for y in range(480):
        for x in range(140,500):
            screen[y,x]=source[(x-140)*2//3,319-y*2//3]
    packed=(screen[:,:,0]<<22)|(screen[:,:,1]<<12)|(screen[:,:,2]<<2)
    (out/"display_rgb.hex").write_text("".join(f"{v:08x}\n" for v in packed.ravel()),encoding="ascii")
    (out/"debug_words.hex").write_text("".join(f"{v:08x}\n" for v in decoder["results"][:96]),encoding="ascii")
    sources=["rtl/common/perception_pkg.sv","rtl/vision/hsvColourGate.sv",
             *[f"rtl/debug/{name}.sv" for name in ("memberBVgaContour","memberBVgaLabels","memberBVgaHsv","memberBVgaDiagnostics","memberBVgaOverlay","memberBVgaModeSwitch")],
             "tests/rtl/memberBVgaPreview_tb.sv"]
    library=out/"simlib"
    runner.run("vlib",[echo7.discover("vlib",args.modelsim_bin),library],out)
    runner.run("compile",[echo7.discover("vlog",args.modelsim_bin),"-sv","-work",library,*[echo7.ROOT/s for s in sources]],out)
    _,output=runner.run("simulation",[echo7.discover("vsim",args.modelsim_bin),"-c","-lib",library,"memberBVgaPreview_tb",
                      "+VECTORS="+out.as_posix(),f"+SWITCHES={args.switches}",f"+RAW_MODE={int(args.raw_camera)}","-do","onerror {quit -code 1}; run -all; quit -code 0"],out)
    if "PASS memberBVgaPreview_tb" not in output or "Fatal:" in output:
        raise RuntimeError("RTL VGA preview did not pass")
    values=np.array([int(v,16) for v in (out/"rendered_rgb.hex").read_text().split()],dtype=np.uint32).reshape(480,640)
    if args.raw_camera and not np.array_equal(values,packed):
        raise RuntimeError("raw-camera RTL output changed the source display pixels")
    rgb=np.stack(((values>>22)&255,(values>>12)&255,(values>>2)&255),axis=2).astype(np.uint8)
    canvas=Image.new("RGB",(640,504),"#202020")
    canvas.paste(Image.fromarray(rgb),(0,24))
    ImageDraw.Draw(canvas).text((5,6),f"RTL REPLAY ONLY - NOT PHYSICAL VGA | SW0={args.switches&1} SW1={(args.switches>>1)&1} SW9={int(args.raw_camera)}",fill="white")
    canvas.save(out/"preview.png")
    result={"status":"PASS","level":"RTL_SIM_DISPLAY_ARTIFACT","output":str(out/"preview.png"),
            "capture":str(args.capture),"sourcePngSha256":hashlib.sha256(imagePath.read_bytes()).hexdigest(),
            "switches":args.switches,"rawCameraMode":args.raw_camera,
            "rawPixelIdentity":"PASS" if args.raw_camera else "NOT_APPLICABLE",
            "sources":{s:echo7.digest(echo7.ROOT/s) for s in sources}}
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
