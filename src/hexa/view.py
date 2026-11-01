"""OCP CAD Viewer integration for the Hexa tag.

Usage (from the project root, with .venv active and VS Code OCP Viewer open):

    python src/hexa/view.py ring
    python src/hexa/view.py core
    python src/hexa/view.py assembly    # default

Or via make:
    .\\make.ps1 view               # shows assembly
    .\\make.ps1 view -Scene ring
"""

from __future__ import annotations

import sys

try:
    from ocp_vscode import show, show_all, set_colormap
except ImportError:
    print("ocp_vscode not installed — install requirements.txt into the .venv first.")
    sys.exit(1)

from .params import P
from .tag import build_assembly, build_core, build_ring
from .checks import check_all, CheckError


SCENES: dict[str, callable] = {
    "assembly": lambda: build_assembly(),
    "ring":     lambda: build_ring(),
    "core":     lambda: build_core(),
}


def main(scene: str = "assembly") -> None:
    try:
        check_all()
    except CheckError as e:
        print(f"CHECK FAILED: {e}", file=sys.stderr)
        sys.exit(1)

    if scene not in SCENES:
        print(f"Unknown scene '{scene}'. Available: {', '.join(SCENES)}", file=sys.stderr)
        sys.exit(1)

    obj = SCENES[scene]()
    show(obj, names=[scene])
    print(f"Sent scene '{scene}' to OCP CAD Viewer.")


if __name__ == "__main__":
    scene = sys.argv[1] if len(sys.argv) > 1 else "assembly"
    main(scene)
