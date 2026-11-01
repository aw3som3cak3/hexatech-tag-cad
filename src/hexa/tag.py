"""Hexa tag geometry builders.

build_ring()      — outer hexagonal ring body (frame)
build_core()      — ceramic core carrier (twist-out puck)
build_assembly()  — ring + core assembled (core inserted, flush)
build_exploded()  — ring + core separated 15 mm in Z for inspection

All builders accept a HexaParams argument:

    from dataclasses import replace
    from hexa.params import P
    from hexa.tag import build_exploded

    proto = build_exploded(replace(P, RING_FACE_T=1.6))
"""

from __future__ import annotations

import math

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Compound,
    Cylinder,
    Location,
    Locations,
    Mode,
    Plane,
    RegularPolygon,
    Vector,
    extrude,
)

from .params import HexaParams, P


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_apothem(across_corners: float) -> float:
    """Centre-to-flat-face distance for a regular hexagon."""
    return across_corners / 2 * math.cos(math.radians(30))


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_ring(p: HexaParams = P):
    """Outer hexagonal ring body.

    Origin: tag centre, back face at z=0, front face at z=RING_T.
    Inner cavity (z = RING_FACE_T … RING_T-RING_FACE_T) accepts the core.

    Features:
    - Hollow hex prism (rim + two face plates)
    - Slotted-ring antenna slot through the +Y flat face
    - Chip A recess on the back face (inner rim side, +Y quadrant)
    - Lanyard hole (Z-axis cylinder) at the +X vertex midpoint
    """
    outer_ac      = p.RING_ACROSS_CORNERS
    inner_ac      = p.RING_INNER_ACROSS_CORNERS
    ring_t        = p.RING_T
    face_t        = p.RING_FACE_T
    cavity_h      = ring_t - 2 * face_t

    outer_apo     = _hex_apothem(outer_ac)   # 17.32 mm
    inner_apo     = _hex_apothem(inner_ac)   # 14.20 mm

    # Lanyard hole centre: midpoint of rim in the +X vertex direction
    lh_cx = outer_ac / 2 - p.RING_RIM_T / 2   # 18.2 mm

    # Chip A recess centre Y: midpoint of rim apothem, +Y side
    chip_a_cy = (outer_apo + inner_apo) / 2   # ~15.76 mm

    with BuildPart() as bp:
        # ── 1. Outer hex solid ──────────────────────────────────────────
        with BuildSketch(Plane.XY):
            RegularPolygon(
                radius=outer_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=ring_t)

        # ── 2. Hollow out inner cavity ──────────────────────────────────
        with BuildSketch(Plane.XY.offset(face_t)):
            RegularPolygon(
                radius=inner_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=cavity_h, mode=Mode.SUBTRACT)

        # ── 3. Antenna slot: radial cut on +Y flat face, full height ────
        #    Slot centre Y = outer_apo − half-depth (midpoint of slot)
        slot_cy = outer_apo - p.ANTENNA_SLOT_D / 2
        with Locations(Location(Vector(0.0, slot_cy, ring_t / 2))):
            Box(
                p.ANTENNA_SLOT_W,
                p.ANTENNA_SLOT_D + 0.02,  # +epsilon to avoid open face
                ring_t + 0.02,
                mode=Mode.SUBTRACT,
            )

        # ── 4. Chip A recess: shallow pocket on back face (+Y rim zone) ─
        with Locations(Location(Vector(0.0, chip_a_cy, p.CHIP_A_RECESS_T / 2))):
            Cylinder(
                radius=p.CHIP_A_RECESS_D / 2,
                height=p.CHIP_A_RECESS_T + 0.02,
                mode=Mode.SUBTRACT,
            )

        # ── 5. Lanyard hole: Z-axis cylinder at the +X vertex midpoint ──
        with Locations(Location(Vector(lh_cx, 0.0, ring_t / 2))):
            Cylinder(
                radius=p.LANYARD_HOLE_D / 2,
                height=ring_t + 0.02,
                mode=Mode.SUBTRACT,
            )

    return bp.part


def build_core(p: HexaParams = P):
    """Ceramic core carrier — the twist-out puck.

    Sits inside the ring: back at z=RING_FACE_T, front at z=RING_T-RING_FACE_T.

    Features:
    - Hex prism body
    - Three rectangular bayonet lugs at 120° spacing (back edge)
    - Chip B recess centred on the front face
    """
    core_ac = p.CORE_ACROSS_CORNERS
    core_h  = p.CORE_T
    lug_h   = p.BAYONET_LUG_H   # axial height AND radial protrusion (square tab)
    lug_w   = p.BAYONET_LUG_W
    z0      = p.RING_FACE_T      # bottom of core in Z

    # Lug centres: just beyond the core outer face, back edge
    lug_r   = core_ac / 2 + lug_h / 2
    lug_cz  = z0 + lug_h / 2    # centred at bottom of core

    with BuildPart() as bp:
        # ── 1. Core hex body ────────────────────────────────────────────
        with BuildSketch(Plane.XY.offset(z0)):
            RegularPolygon(
                radius=core_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=core_h)

        # ── 2. Rectangular bayonet lugs ─────────────────────────────────
        lug_locs = []
        for i in range(p.BAYONET_LUGS):
            a_deg = i * p.BAYONET_PITCH_DEG
            a_rad = math.radians(a_deg)
            cx = lug_r * math.cos(a_rad)
            cy = lug_r * math.sin(a_rad)
            # Location: translate to (cx, cy, lug_cz), rotate a_deg around Z
            # so the lug's local X axis points radially outward
            lug_locs.append(
                Location(Vector(cx, cy, lug_cz), Vector(0, 0, 1), a_deg)
            )

        with Locations(*lug_locs):
            Box(
                lug_h,   # radial depth  (local X after rotation)
                lug_w,   # circumferential width (local Y)
                lug_h,   # axial height  (Z)
            )

        # ── 3. Chip B recess: centred on front face ─────────────────────
        core_top = z0 + core_h
        with Locations(Location(Vector(0.0, 0.0, core_top - p.CHIP_B_RECESS_T / 2))):
            Cylinder(
                radius=p.CHIP_B_RECESS_D / 2,
                height=p.CHIP_B_RECESS_T + 0.02,
                mode=Mode.SUBTRACT,
            )

    return bp.part


def build_assembly(p: HexaParams = P) -> Compound:
    """Ring with core inserted (assembled position)."""
    ring = build_ring(p)
    core = build_core(p)
    return Compound(children=[ring, core])


def build_exploded(p: HexaParams = P, gap: float = 15.0) -> Compound:
    """Ring and core separated by `gap` mm in +Z for inspection."""
    ring = build_ring(p)
    core = build_core(p).move(Location(Vector(0, 0, gap)))
    return Compound(children=[ring, core])
