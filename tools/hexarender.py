# -*- coding: utf-8 -*-
"""Render the Hexa tag from CAD — product-quality PNG for the team site.

    python tools/hexarender.py              # dry run, shows paths
    python tools/hexarender.py --skriv      # render (takes a few minutes)
    python tools/hexarender.py --skriv --push   # render + copy to site

Produces:
    out/renders/hexa-assembly.png   ring + core, diagonal view
    out/renders/hexa-worn.png       ring + core + chain, slight downward angle

Prerequisites: .venv (.\\make.ps1 venv) and Blender 4.5.
"""
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(ROT, ".venv", "Scripts", "python.exe")
MESH = os.path.join(ROT, "out", "render-mesh")
HAR  = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROT, "out", "renders")

BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
if "--blender" in sys.argv:
    BLENDER = sys.argv[sys.argv.index("--blender") + 1]

SITE_RENDERS = r"C:\Users\eriko\git\hexatech-site\public\renders"

LJUS    = "1.4"
PX      = "2400"
SAMPLES = "220"

SCENES = [
    {
        "name":  "assembly",
        "parts": "ring,core",
        "az":    "-45",
        "el":    "25",
        "out":   os.path.join(OUT, "hexa-assembly.png"),
    },
    {
        "name":  "worn",
        "parts": "ring,core,chain",
        "az":    "-60",
        "el":    "20",
        "out":   os.path.join(OUT, "hexa-worn.png"),
    },
]

EXPORT_SCRIPT = '''\
import os, sys
sys.path.insert(0, r"%(src)s")
import build123d as bd
from hexa.tag import build_ring, build_core, build_chain_stubs
from hexa.checks import check_all

check_all()
mesh = r"%(mesh)s"
os.makedirs(mesh, exist_ok=True)
opts = dict(tolerance=0.05, angular_tolerance=0.1)
bd.export_stl(build_ring(),        os.path.join(mesh, "ring.stl"),  **opts)
bd.export_stl(build_core(),        os.path.join(mesh, "core.stl"),  **opts)
bd.export_stl(build_chain_stubs(), os.path.join(mesh, "chain.stl"), **opts)
print("  ring.stl  core.stl  chain.stl ->", mesh)
'''

# Alpha values below this are shadow wisps. Left alone they form a grey
# plate at the image edges when composited against white. Strip them out
# and renormalise the remaining alpha so the crop is clean.
SKUGGGOLV = 42


def kor(vad, argv):
    print("\n%s" % vad)
    k = subprocess.run(argv, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if k.returncode:
        print(k.stdout[-3000:])
        print(k.stderr[-3000:], file=sys.stderr)
        raise SystemExit("%s failed (%d)" % (vad, k.returncode))
    return k.stdout


def beskar(path):
    """Strip alpha floor and crop to content."""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    r, g, b_, a = im.split()
    a = a.point(lambda v: 0 if v <= SKUGGGOLV else
                int((v - SKUGGGOLV) * 255.0 / (255 - SKUGGGOLV) + 0.5))
    im = Image.merge("RGBA", (r, g, b_, a))
    bb = a.point(lambda v: 255 if v > 8 else 0).getbbox()
    bw, bh = im.size
    m = int(max(bw, bh) * 0.02)
    ut = im.crop((max(0, bb[0] - m), max(0, bb[1] - m),
                  min(bw, bb[2] + m), min(bh, bb[3] + m)))
    ut.save(path, optimize=True)
    return ut.size


if __name__ == "__main__":
    print("HEXA RENDER")
    print("  venv     %s  %s" % (VENV, "ok" if os.path.exists(VENV) else "MISSING"))
    print("  blender  %s  %s" % (BLENDER, "ok" if os.path.exists(BLENDER) else "MISSING"))
    print("  mesh     %s" % MESH)
    for s in SCENES:
        print("  %-10s parts=%s  az=%s el=%s -> %s"
              % (s["name"], s["parts"], s["az"], s["el"], s["out"]))
    if "--skriv" not in sys.argv:
        # Push existing renders without re-rendering
        if "--push" in sys.argv:
            missing = [s["out"] for s in SCENES if not os.path.exists(s["out"])]
            if missing:
                print("\nMissing renders (run with --skriv first):")
                for p in missing:
                    print("  ", p)
                raise SystemExit(1)
        else:
            print("\nDRY RUN. Run with --skriv to render (a few minutes per scene).")
            raise SystemExit(0)

    # 1. Export per-part STLs (fine mesh — render quality, not print quality)
    os.makedirs(MESH, exist_ok=True)
    skript = os.path.join(MESH, "_export.py")
    with open(skript, "w", encoding="utf-8") as f:
        f.write(EXPORT_SCRIPT % {"src": os.path.join(ROT, "src"), "mesh": MESH})
    print(kor("1. export STLs", [VENV, "-I", "-X", "utf8", skript]), end="")

    os.makedirs(OUT, exist_ok=True)

    # 2. Render each scene
    for n, scene in enumerate(SCENES, 2):
        kor("%d. Blender: %s" % (n, scene["name"]), [
            BLENDER, "--background", "--python",
            os.path.join(HAR, "hexarender_blender.py"), "--",
            "--mesh",    MESH,
            "--parts",   scene["parts"],
            "--ut",      scene["out"],
            "--az",      scene["az"],
            "--el",      scene["el"],
            "--ljus",    LJUS,
            "--px",      PX,
            "--samples", SAMPLES,
        ])
        bw, bh = beskar(scene["out"])
        print("  %s: %dx%d  (%.1f MB)"
              % (scene["name"], bw, bh, os.path.getsize(scene["out"]) / 1e6))
        print("  wrote %s" % scene["out"])

    # 3. Push to site if requested
    if "--push" in sys.argv:
        if not os.path.isdir(SITE_RENDERS):
            os.makedirs(SITE_RENDERS, exist_ok=True)
        for scene in SCENES:
            if os.path.exists(scene["out"]):
                dest = os.path.join(SITE_RENDERS, os.path.basename(scene["out"]))
                shutil.copy2(scene["out"], dest)
                print("  pushed %s" % os.path.basename(scene["out"]))
        print("\nPushed renders to %s" % SITE_RENDERS)
        print("Commit hexatech-site and redeploy: vercel --prod --yes")
