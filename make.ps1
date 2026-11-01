#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build wrapper for hexatech-tag-cad.

.DESCRIPTION
    Mirrors the make targets from the flume template.
    All targets run inside the .venv (Python 3.12).

.PARAMETER Target
    venv     Create .venv with Python 3.12 and install requirements.
    check    Run geometric self-checks (no files written).
    test     Run pytest.
    view     Show a scene in OCP CAD Viewer (-Scene <name>: assembly|ring|core).
    step     Export STEP files to out/step/.
    stl      Export STL files to out/stl/.
    clean    Delete out/.

.EXAMPLE
    .\make.ps1 venv
    .\make.ps1 view -Scene assembly
    .\make.ps1 test
#>

param(
    [Parameter(Position=0)]
    [string] $Target = "check",
    [string] $Scene = "assembly"
)

$python = ".venv\Scripts\python.exe"
$pip    = ".venv\Scripts\pip.exe"

function Require-Venv {
    if (-not (Test-Path $python)) {
        Write-Error "No .venv found. Run '.\make.ps1 venv' first."
        exit 1
    }
}

switch ($Target) {
    "venv" {
        Write-Host "Creating .venv with Python 3.12..."
        py -3.12 -m venv .venv
        & $pip install --upgrade pip | Out-Null
        & $pip install -r requirements.txt
        Write-Host ".venv ready."
    }

    "check" {
        Require-Venv
        $env:PYTHONPATH = "src"
        & $python -c "from hexa.checks import check_all; check_all(); print('All checks passed.')"
    }

    "test" {
        Require-Venv
        $env:PYTHONPATH = "src"
        & $python -m pytest tests/ -v
    }

    "view" {
        Require-Venv
        $env:PYTHONPATH = "src"
        & $python src/hexa/view.py $Scene
    }

    "step" {
        Require-Venv
        $env:PYTHONPATH = "src"
        New-Item -ItemType Directory -Force out/step | Out-Null
        & $python -c "
from hexa.tag import build_ring, build_core, build_assembly
from hexa.checks import check_all
check_all()
ring = build_ring(); ring.export_step('out/step/ring.step')
core = build_core(); core.export_step('out/step/core.step')
asm  = build_assembly(); asm.export_step('out/step/assembly.step')
print('STEP files written to out/step/')
"
    }

    "stl" {
        Require-Venv
        $env:PYTHONPATH = "src"
        New-Item -ItemType Directory -Force out/stl | Out-Null
        & $python -c "
from hexa.tag import build_ring, build_core
from hexa.checks import check_all
check_all()
build_ring().export_stl('out/stl/ring.stl')
build_core().export_stl('out/stl/core.stl')
print('STL files written to out/stl/')
"
    }

    "clean" {
        if (Test-Path out) { Remove-Item -Recurse -Force out }
        Write-Host "out/ deleted."
    }

    default {
        Write-Error "Unknown target '$Target'. Valid: venv, check, test, view, step, stl, clean"
        exit 1
    }
}
