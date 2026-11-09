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
    view     Show a scene in OCP CAD Viewer (-Scene <name>: assembly|assembled|ring|core|exploded).
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
        & $python -m hexa.view $Scene
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

    "stl-all" {
        Require-Venv
        $env:PYTHONPATH = "src"
        New-Item -ItemType Directory -Force out/stl | Out-Null
        & $python -c "
import build123d as bd
from hexa.tag import build_ring, build_core, build_assembly, build_exploded, build_worn
from hexa.checks import check_all
check_all()
bd.export_stl(build_ring(),     'out/stl/ring.stl')
bd.export_stl(build_core(),     'out/stl/core.stl')
bd.export_stl(build_assembly(), 'out/stl/assembly.stl')
bd.export_stl(build_exploded(), 'out/stl/exploded.stl')
bd.export_stl(build_worn(),     'out/stl/worn.stl')
print('STL files written to out/stl/')
"
    }

    "gltf" {
        Require-Venv
        $env:PYTHONPATH = "src"
        New-Item -ItemType Directory -Force out/gltf | Out-Null
        Write-Host "Note: hexarender.py --push copies both .gltf and .bin to the site"
        $pyGltf = @'
import build123d as bd
from hexa.tag import (build_ring, build_core, build_assembly, build_exploded,
                      build_worn, build_chain_hardware, build_ring_electronics,
                      build_core_electronics, build_electronics)
from hexa.checks import check_all
check_all()
bd.export_gltf(build_ring(),               'out/gltf/ring.gltf')
bd.export_gltf(build_core(),               'out/gltf/core.gltf')
bd.export_gltf(build_assembly(),           'out/gltf/assembly.gltf')
bd.export_gltf(build_exploded(),           'out/gltf/exploded.gltf')
bd.export_gltf(build_worn(),               'out/gltf/worn.gltf')
bd.export_gltf(build_chain_hardware(),     'out/gltf/chain-hardware.gltf')
bd.export_gltf(build_ring_electronics(),   'out/gltf/ring-electronics.gltf')
bd.export_gltf(build_core_electronics(),   'out/gltf/core-electronics.gltf')
bd.export_gltf(build_electronics(),        'out/gltf/electronics.gltf')
print('GLTF files written to out/gltf/')
'@
        & $python -c $pyGltf
    }

    "card-view" {
        Require-Venv
        $env:PYTHONPATH = "src"
        & $python -m hexa.view $Scene
    }

    "card-gltf" {
        Require-Venv
        $env:PYTHONPATH = "src"
        New-Item -ItemType Directory -Force out/gltf | Out-Null
        $pyCard = @'
import build123d as bd
from hexa.card_tag import (build_hex_card, build_card_grommet, build_card_surround,
                            build_tear_away, build_card_assembly,
                            build_full_assembly, build_worn, build_card_electronics)
bd.export_gltf(build_hex_card(),           'out/gltf/card-nfc.gltf')
bd.export_gltf(build_card_grommet(),       'out/gltf/card-grommet.gltf')
bd.export_gltf(build_card_surround(),      'out/gltf/card-surround.gltf')
bd.export_gltf(build_tear_away(),          'out/gltf/card-tearaway.gltf')
bd.export_gltf(build_card_assembly(),      'out/gltf/card-assembly.gltf')
bd.export_gltf(build_full_assembly(),      'out/gltf/card-full.gltf')
bd.export_gltf(build_worn(),               'out/gltf/card-worn.gltf')
bd.export_gltf(build_card_electronics(),   'out/gltf/card-electronics.gltf')
print('Card GLTF files written to out/gltf/')
'@
        & $python -c $pyCard
    }

    "clean" {
        if (Test-Path out) { Remove-Item -Recurse -Force out }
        Write-Host "out/ deleted."
    }

    default {
        Write-Error "Unknown target '$Target'. Valid: venv, check, test, view, card-view, step, stl, gltf, card-gltf, clean"
        exit 1
    }
}
