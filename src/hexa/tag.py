"""Hexa tag geometry builders.

build_ring()      — outer hexagonal ring body (frame)
build_core()      — ceramic core carrier (twist-out puck)
build_assembly()  — ring + core positioned together for viewing/export

All builders accept a HexaParams argument so variants can be explored:

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
    BuildPart,
    BuildSketch,
    Circle,
    Compound,
    Cylinder,
    Location,
    Mode,
    Plane,
    PolarLocations,
    RegularPolygon,
    ShapeList,
    Vector,
    add,
    extrude,
)

from .params import HexaParams, P


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_ring(p: HexaParams = P) -> object:
    """Build the outer ring (frame) as a single solid.

    Coordinate system: back face at z=0, front face at z=RING_T.
    The inner cavity (z = RING_FACE_T … RING_T - RING_FACE_T) accepts the core.
    """
    outer_ac = p.RING_ACROSS_CORNERS
    inner_ac = p.RING_INNER_ACROSS_CORNERS
    ring_t   = p.RING_T
    face_t   = p.RING_FACE_T
    cavity_h = ring_t - 2 * face_t

    with BuildPart() as bp:
        # 1. Full outer hex prism
        with BuildSketch(Plane.XY):
            RegularPolygon(
                radius=outer_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=ring_t)

        # 2. Hollow out the inner cavity (leaves front/back faces + rim)
        with BuildSketch(Plane.XY.offset(face_t)):
            RegularPolygon(
                radius=inner_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=cavity_h, mode=Mode.SUBTRACT)

        # 3. Lanyard hole through one vertex (at facet 0, +x direction)
        lh_r = p.LANYARD_HOLE_D / 2
        lh_cx = outer_ac / 2  # vertex lies at circumradius on the x-axis
        with BuildSketch(Plane.XZ.offset(ring_t / 2)):
            Circle(radius=lh_r, align=(Align.CENTER, Align.CENTER))
        extrude(amount=outer_ac, mode=Mode.SUBTRACT)

    return bp.part


def build_core(p: HexaParams = P) -> object:
    """Build the ceramic core carrier (twist-out puck).

    Sits inside the ring cavity: back at z=RING_FACE_T, front at z=RING_T-RING_FACE_T.
    Carries three evenly-spaced bayonet lugs on its outer circumference.
    """
    core_ac = p.CORE_ACROSS_CORNERS
    core_h  = p.CORE_T
    lug_h   = p.BAYONET_LUG_H
    lug_w   = p.BAYONET_LUG_W
    lug_r   = core_ac / 2 + lug_h / 2  # lug centre radius

    z0 = p.RING_FACE_T  # bottom of core inside ring

    with BuildPart() as bp:
        # Core body
        with BuildSketch(Plane.XY.offset(z0)):
            RegularPolygon(
                radius=core_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=core_h)

        # Bayonet lugs: small rectangular tabs at even angular spacing
        # Positioned at z0 + lug_h from the back (engage ring's lug groove)
        for i in range(p.BAYONET_LUGS):
            angle_rad = math.radians(i * p.BAYONET_PITCH_DEG)
            cx = lug_r * math.cos(angle_rad)
            cy = lug_r * math.sin(angle_rad)
            # Lug is a small cylinder for now; will be refined to rectangular tab
            lug_plane = Plane(
                origin=Vector(cx, cy, z0 + lug_h),
                x_dir=Vector(math.cos(angle_rad), math.sin(angle_rad), 0),
                z_dir=Vector(0, 0, 1),
            )
            with BuildSketch(lug_plane):
                Circle(
                    radius=lug_h / 2,
                    align=(Align.CENTER, Align.CENTER),
                )
            extrude(amount=lug_h)

    return bp.part


def build_assembly(p: HexaParams = P) -> Compound:
    """Ring + core together, ready for viewing or STEP export."""
    ring = build_ring(p)
    core = build_core(p)
    return Compound(children=[ring, core])
