param([string]$ModelSimBin='C:\intelFPGA_lite\18.1\modelsim_ase\win32aloem')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$sim=Join-Path $root 'sim/scheme_c'
New-Item -ItemType Directory -Path $sim -Force | Out-Null
Push-Location -LiteralPath $sim
try {
 if(!(Test-Path work)){ & (Join-Path $ModelSimBin 'vlib.exe') work; if($LASTEXITCODE -ne 0){throw 'vlib failed'} }
 $sources=@()
 foreach($line in Get-Content (Join-Path $root 'quartus/PartBDebug.qsf')){
  if($line -match '^set_global_assignment -name SYSTEMVERILOG_FILE (.+)$'){
   $sources+=Join-Path (Join-Path $root 'quartus') $Matches[1]
  }
 }
 $sources+=@(Join-Path $PSScriptRoot 'integration/vga_sink_sim.sv')
 $sources+=@(Join-Path $PSScriptRoot 'scheme_c/tb_scheme_c.sv')
 $sources+=@(Join-Path $PSScriptRoot 'scheme_c/tb_scheme_c_link.sv')
 $sources+=@(Join-Path $PSScriptRoot 'integration/perceptionCoreReplay_tb.sv')
 $sources+=@(Join-Path $PSScriptRoot 'integration/tb_v2_pixel_latency.sv')
 & (Join-Path $ModelSimBin 'vlog.exe') -sv '+define+VERILATOR' ('+incdir+'+(Join-Path $root 'rtl/common')) ('+incdir+'+(Join-Path $PSScriptRoot 'integration')) -work work -l compile.log @sources
 if($LASTEXITCODE -ne 0){throw 'RTL/TB simulation compilation failed'}
 foreach($name in @('tb_scheme_c','tb_scheme_c_link')){
  & (Join-Path $ModelSimBin 'vsim.exe') -c -onfinish exit -l ($name+'.log') ('work.'+$name) -do (Join-Path $PSScriptRoot 'run.do')
  if($LASTEXITCODE -ne 0 -or !(Select-String -LiteralPath ($name+'.log') -SimpleMatch -Pattern ('PASS: '+$name) -Quiet)){throw ($name+' failed')}
 }
} finally {Pop-Location}
