
# Course R6 entry point.
# Requires Verilator 5.050, make, a C++ compiler,
# Python 3, NumPy and Pillow.
# Never installs dependencies.

$ErrorActionPreference = "Stop"

# Resolve repository root from this script's location.
$repoDir = $PSScriptRoot

# Use PYTHON if specified; otherwise locate Python 3 on Windows.
$pythonArgs = @()

if ($env:PYTHON) {
    $pythonCommand = $env:PYTHON
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = "py"
    $pythonArgs = @("-3")
}
else {
    $pythonCommand = "python"
}

# Check whether the Python executable exists.
if (-not (Get-Command $pythonCommand -ErrorAction SilentlyContinue)) {
    [Console]::Error.WriteLine(
        "FAIL ENVIRONMENT_BLOCKED: Python 3 is unavailable; set PYTHON to its executable."
    )
    exit 2
}

# Execute the Verilator test suite with all supplied arguments.
$suitePath = Join-Path $repoDir "tools\lib\verilator_suite.py"

& $pythonCommand @pythonArgs $suitePath @args

# Propagate the Python process exit code.
exit $LASTEXITCODE
