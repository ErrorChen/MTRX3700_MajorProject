#!/usr/bin/env python3
"""Run the required Bash entry point with isolated native Windows dependencies.

Does not install tools or change global PATH, credentials or execution policy.
Use the actual discovered compiler and Git Bash paths, including spaces.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler-bin",type=Path,required=True)
    parser.add_argument("--bash",type=Path,required=True)
    parser.add_argument("--verilator-root",type=Path,default=Path("build/toolchains/verilator5050/ucrt64"))
    parser.add_argument("--jobs",type=int,choices=range(1,17),default=4)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    toolRoot=args.verilator_root.resolve()
    compilerRoot=args.compiler_bin.resolve()
    verilator=toolRoot/"bin/verilator_bin.exe"
    for path in (args.bash,verilator,toolRoot/"bin/make.exe",compilerRoot/"g++.exe"):
        if not path.is_file():
            parser.error(f"missing dependency: {path}")
    environment=dict(os.environ)
    pathKey=next((key for key in environment if key.upper()=="PATH"),"PATH")
    shellTools=args.bash.resolve().parent.parent/"usr/bin"
    environment[pathKey]=os.pathsep.join((str(compilerRoot),str(toolRoot/"bin"),str(shellTools),environment.get(pathKey,"")))
    environment["VERILATOR_ROOT"]=(toolRoot/"share/verilator").as_posix()
    environment["PYTHON"]=Path(sys.executable).as_posix()
    # Git's bin/bash launcher prepends its incompatible mingw DLL directory.
    # The Python runner reapplies these explicit native tool paths after Bash.
    environment["ECHO7_R6_NATIVE_PATH"]=os.pathsep.join((str(compilerRoot),str(toolRoot/"bin"),str(shellTools)))
    return subprocess.run([str(args.bash),"./run_all_tests.sh","--verilator",str(verilator),"--jobs",str(args.jobs)],
                          cwd=root,env=environment,check=False).returncode


if __name__=="__main__":raise SystemExit(main())
