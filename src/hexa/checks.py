"""Geometric self-consistency checks for the Hexa tag.

Pure functions over HexaParams — no geometry build needed for most checks,
so they run fast and can gate every export.

Usage:
    python -c "from hexa.checks import check_all; check_all()"
"""

from __future__ import annotations

from .params import HexaParams, P


class CheckError(AssertionError):
    """Raised when the design violates one of its own rules."""


def check_key_push(p: HexaParams = P) -> None:
    """KEY_PUSH_MM must be at least 2× the axial print tolerance.

    If it is not, the push-before-twist action is lost in normal fit variation
    and the bayonet can disengage without intent.
    """
    min_push = 2 * p.M_AXIAL_TOL
    if p.KEY_PUSH_MM < min_push:
        raise CheckError(
            f"KEY_PUSH_MM={p.KEY_PUSH_MM} < 2×M_AXIAL_TOL={min_push:.2f}: "
            "press-before-twist is within print tolerance and will be unreliable."
        )


def check_lug_travel(p: HexaParams = P) -> None:
    """The lug travel arc must exceed the lug circumferential width.

    If the arc is shorter than the lug, the lug cannot fully clear its slot
    during the twist and the core will jam rather than release.
    """
    arc = p.BAYONET_LUG_ARC_MM
    if arc <= p.BAYONET_LUG_W:
        raise CheckError(
            f"BAYONET_LUG_ARC_MM={arc:.2f} ≤ BAYONET_LUG_W={p.BAYONET_LUG_W}: "
            "lug cannot clear its slot during release twist."
        )


def check_wall_min(p: HexaParams = P) -> None:
    """Ring rim must be at least M_WALL_MIN thick; face must be at least M_WALL_MIN."""
    if p.RING_RIM_T < p.M_WALL_MIN:
        raise CheckError(
            f"RING_RIM_T={p.RING_RIM_T} < M_WALL_MIN={p.M_WALL_MIN}: rim too thin to print."
        )
    if p.RING_FACE_T < p.M_WALL_MIN:
        raise CheckError(
            f"RING_FACE_T={p.RING_FACE_T} < M_WALL_MIN={p.M_WALL_MIN}: face too thin to print."
        )


def check_lanyard_hole(p: HexaParams = P) -> None:
    """Lanyard hole must leave at least LANYARD_HOLE_EDGE wall to the outer edge.

    Outer edge radius at the lanyard vertex = RING_ACROSS_CORNERS / 2.
    Hole centre sits at that vertex, so the wall from hole edge to tag edge
    = RING_ACROSS_CORNERS/2 - LANYARD_HOLE_D/2.
    """
    outer_r = p.RING_ACROSS_CORNERS / 2
    hole_r = p.LANYARD_HOLE_D / 2
    wall = outer_r - hole_r
    if wall < p.LANYARD_HOLE_EDGE:
        raise CheckError(
            f"Lanyard hole leaves {wall:.2f} mm to edge; "
            f"minimum is LANYARD_HOLE_EDGE={p.LANYARD_HOLE_EDGE} mm."
        )


def check_core_fits(p: HexaParams = P) -> None:
    """Core across-corners must be positive and smaller than the ring inner space."""
    if p.CORE_ACROSS_CORNERS <= 0:
        raise CheckError(
            f"CORE_ACROSS_CORNERS={p.CORE_ACROSS_CORNERS:.2f}: core has zero or negative size."
        )
    if p.CORE_ACROSS_CORNERS >= p.RING_INNER_ACROSS_CORNERS:
        raise CheckError(
            f"CORE_ACROSS_CORNERS={p.CORE_ACROSS_CORNERS:.2f} >= "
            f"RING_INNER_ACROSS_CORNERS={p.RING_INNER_ACROSS_CORNERS:.2f}: core does not fit."
        )


def check_all(p: HexaParams = P) -> None:
    """Run every check; raise CheckError on the first failure."""
    check_key_push(p)
    check_lug_travel(p)
    check_wall_min(p)
    check_lanyard_hole(p)
    check_core_fits(p)
