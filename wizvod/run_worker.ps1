# wizvod/run_worker.ps1
$ErrorActionPreference = "Stop"

# 1) Pozicioniraj se u root projekta (gdje je ova skripta)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# 2) Aktiviraj virtualno okruženje ako postoji (ne ruši se ako ne postoji)
$venvActivatePs1 = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivatePs1) {
    & $venvActivatePs1
}

# 3) Pokreni worker kao modul
python -m wizvod.worker --run
