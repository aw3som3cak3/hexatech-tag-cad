"""Hexa tag geometry builders.

build_ring()  — the outer hexagonal ring body (frame)
build_core()  — the ceramic core carrier (the twist-out puck)
build_assembly()  — ring + core positioned together for viewing/export

All builders accept a HexaParams argument so variant parameters can be
passed without global state:

    from dataclasses import replace
    from hexa.params import P
    from hexa.tag import build_assembly

    thick = build_assembly(replace(P, RING_FACE_T=1.6))
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
    GridLocations,
    Location,
    Plane,
    PolarLocations,
    RegularPolygon,
    Part,
    ShapeList,
    add,
    extrude,
    fillet,
    make_face,
    mirror,
    offset,
)

from .params import HexaParams, P


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hex_prism(across_corners: float, height: float) -> Part:
    """A solid regular hexagonal prism centred at the origin."""
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            RegularPolygon(
                radius=across_corners / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=height)
    return bp.part.move(Location((0, 0, -height / 2)))


def _hex_shell(outer_ac: float, inner_ac: float, height: float) -> Part:
    """Hollow hexagonal prism (outer minus inner), centred at the origin."""
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=outer_ac / 2, side_count=6,
                           align=(Align.CENTER, Align.CENTER))
            RegularPolygon(radius=inner_ac / 2, side_count=6,
                           align=(Align.CENTER, Align.CENTER), mode=mode.SUBTRACT)
        extrude(amount=height)
    return bp.part.move(Location((0, 0, -height / 2)))


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_ring(p: HexaParams = P) -> Part:
    """Build the outer ring (frame) as a single solid.

    The ring sits with its back face at z=0 and front face at z=RING_T.
    The inner cavity accepts the core.  The slotted-ring antenna slot is cut
    as a thin radial channel through the rim.

    Returns a build123d Part.
    """
    rim_h = p.RING_T
    face_t = p.RING_FACE_T
    inner_ac = p.RING_INNER_ACROSS_CORNERS
    outer_ac = p.RING_ACROSS_CORNERS

    with BuildPart() as bp:
        # Outer solid hex prism
        with BuildSketch(Plane.XY.offset(rim_h)):
            RegularPolygon(radius=outer_ac / 2, side_count=6,
                           align=(Align.CENTER, Align.CENTER))
        extrude(amount=-rim_h)

        # Subtract the inner cavity (leaves front + back faces + rim wall)
        cavity_h = rim_h - 2 * face_t
        with BuildSketch(Plane.XY.offset(rim_h - face_t)):
            RegularPolygon(radius=inner_ac / 2, side_count=6,
                           align=(Align.CENTER, Align.CENTER))
        extrude(amount=-cavity_h, mode=mode.SUBTRACT)

        # Antenna slot: thin radial cut through the rim, on one side
        slot_depth = p.RING_RIM_T + 0.1  # through the full rim
        slot_h = rim_h  # full height of the ring
        with BuildSketch(Plane.XY.offset(rim_h)):
            with Locations((outer_ac / 2 - p.RING_RIM_T / 2, 0)):
                Circle(radius=slot_depth / 2)  # placeholder — real slot is rectangular
        # TODO: replace circle with a proper rectangular slot once geometry is validated

        # Lanyard hole through one vertex
        lh_centre_r = outer_ac / 2
        with BuildSketch(Plane.YZ.offset(lh_centre_r)):
            Circle(radius=p.LANYARD_HOLE_D / 2)
        extrude(amount=-(p.LANYARD_HOLE_D + p.RING_RIM_T), mode=mode.SUBTRACT)

    return bp.part


def build_core(p: HexaParams = P) -> Part:
    """Build the ceramic core carrier (the twist-out puck).

    The core is a hex prism that fits inside the ring cavity.  It carries
    the three bayonet lugs on its circumference.

    Returns a build123d Part, positioned at z=RING_FACE_T (sitting inside the ring).
    """
    core_h = p.CORE_T
    core_ac = p.CORE_ACROSS_CORNERS
    lug_r = core_ac / 2  # lug sits at the outer radius of the core

    with BuildPart() as bp:
        # Core body
        with BuildSketch(Plane.XY.offset(core_h)):
            RegularPolygon(radius=core_ac / 2, side_count=6,
                           align=(Align.CENTER, Align.CENTER))
        extrude(amount=-core_h)

        # Bayonet lugs: small rectangular tabs at lug_r, evenly spaced
        lug_arc = p.BAYONET_LUG_W / lug_r  # angular width in radians
        for i in range(p.BAYONET_LUGS):
            angle_deg = i * p.BAYONET_PITCH_DEG
            with BuildSketch(Plane.XY.offset(p.BAYONET_LUG_H)):
                with Locations(Location(
                    (lug_r * math.cos(math.radians(angle_deg)),
                     lug_r * math.sin(math.radians(angle_deg)), 0)
                )):
                    # Approximate lug as a small box (will be refined)
                    Box(p.BAYONET_LUG_H, p.BAYONET_LUG_W, p.BAYONET_LUG_H,
                        align=(Align.CENTER, Align.CENTER, Align.MAX))
            extrude(amount=p.BAYONET_LUG_H, mode=mode.ADD)

    return bp.part.move(Location((0, 0, p.RING_FACE_T)))


def build_assembly(p: HexaParams = P) -> Compound:
    """Ring + core together, ready for viewing or STEP export."""
    ring = build_ring(p)
    core = build_core(p)
    return Compound(children=[ring, core])
