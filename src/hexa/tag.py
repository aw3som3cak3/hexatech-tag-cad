"""Hexa tag geometry builders.

build_ring()      — outer hexagonal ring body (frame)
build_core()      — ceramic core carrier (twist-out puck)
build_assembly()  — ring + core assembled (core inserted, flush)
build_exploded()  — ring + core separated 15 mm in Z for inspection
build_worn()      — assembly + chain stubs (how the tag is worn)

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
    Color,
    Compound,
    Cylinder,
    GeomType,
    Location,
    Locations,
    Mode,
    Plane,
    RegularPolygon,
    Text,
    Vector,
    chamfer,
    extrude,
)

# Ring: natural bead-blast Ti Gr5 — stays with casualty
_COLOR_RING  = Color(0.72, 0.72, 0.76)
# Core: Ti Type II anodize 60–70 V (Pantone 2727 C / RAL 5005 Signal Blue) — travels to records
_COLOR_CORE  = Color(0.18, 0.38, 0.72)
# Stainless ball chain — slightly warmer steel grey
_COLOR_CHAIN = Color(0.65, 0.65, 0.67)

from .params import FACET_EXAMPLES, HexaParams, P


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
    Inner cavity (z = RING_FACE_T … RING_T, or RING_T-RING_FACE_T if closed) accepts the core.

    Features:
    - Hollow hex prism; front face plate removed when RING_FRONT_OPEN (ADR-0042)
    - Circumferential parting-line groove at z=RING_FACE_T (ADR-0042)
    - Slotted-ring antenna slot through the +Y flat face
    - Chip A recess on the back face (inner rim side, +Y quadrant)
    - Mounting tab at +X vertex with two chain holes (chain threads through both)
    - Engraving relief zones + example text on each of the 6 rim facets
    - TURN / PULL instruction engraved on back face (ADR-0043)
    - Body chamfer on back-face outer perimeter (ergonomics)
    """
    outer_ac  = p.RING_ACROSS_CORNERS
    inner_ac  = p.RING_INNER_ACROSS_CORNERS
    ring_t    = p.RING_T
    face_t    = p.RING_FACE_T
    # ADR-0042: open front removes the front face plate
    cavity_h  = ring_t - face_t if p.RING_FRONT_OPEN else ring_t - 2 * face_t

    outer_apo = _hex_apothem(outer_ac)   # ~17.32 mm
    inner_apo = _hex_apothem(inner_ac)   # ~14.20 mm

    # Mounting tab at +X vertex: gives chain holes clean through-hole geometry.
    # Tab overlaps 1 mm into ring body for a clean boolean union.
    _tab_overlap = 1.0
    _tab_x_extent = p.CHAIN_TAB_DEPTH + _tab_overlap
    _tab_x_center = outer_ac / 2 + (p.CHAIN_TAB_DEPTH - _tab_overlap) / 2
    # Chain holes centred in tab (X), spaced ±CHAIN_HOLE_SPACING/2 in Y
    lh_cx = outer_ac / 2 + (p.CHAIN_TAB_DEPTH - _tab_overlap) / 2
    lh_y1 = +p.CHAIN_HOLE_SPACING / 2
    lh_y2 = -p.CHAIN_HOLE_SPACING / 2

    # Chip A recess centre Y: midpoint of rim apothem, +Y side
    chip_a_cy = (outer_apo + inner_apo) / 2   # ~15.76 mm

    # Engraving field dimensions on each facet
    engrave_w = p.FACET_SIDE - 2 * p.ENGRAVE_MARGIN
    engrave_h = ring_t - 2 * p.ENGRAVE_MARGIN

    with BuildPart() as bp:
        # ── 1. Outer hex solid ──────────────────────────────────────────
        with BuildSketch(Plane.XY):
            RegularPolygon(
                radius=outer_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=ring_t)

        # ── 2. Mounting tab at +X vertex for chain holes ─────────────────
        with Locations(Location(Vector(_tab_x_center, 0.0, ring_t / 2))):
            Box(_tab_x_extent, 2 * p.CHAIN_TAB_HALF_W, ring_t)

        # ── 3. Hollow out inner cavity ──────────────────────────────────
        with BuildSketch(Plane.XY.offset(face_t)):
            RegularPolygon(
                radius=inner_ac / 2,
                side_count=6,
                align=(Align.CENTER, Align.CENTER),
            )
        extrude(amount=cavity_h, mode=Mode.SUBTRACT)

        # ── 4. Parting-line groove at z=RING_FACE_T (ADR-0042) ──────────
        #    Circumferential groove on the inner bore wall marks the core
        #    seating plane — visible from the front when RING_FRONT_OPEN.
        if p.PART_LINE_W > 0 and p.PART_LINE_D > 0:
            try:
                groove_r = inner_apo + p.PART_LINE_D
                groove_z = face_t + p.PART_LINE_W / 2
                with Locations(Location(Vector(0.0, 0.0, groove_z))):
                    Cylinder(
                        radius=groove_r,
                        height=p.PART_LINE_W,
                        mode=Mode.SUBTRACT,
                    )
            except Exception:
                pass  # cosmetic; skip if unsupported

        # ── 5. Antenna slot: radial cut on +Y flat face, full height ────
        slot_cy = outer_apo - p.ANTENNA_SLOT_D / 2
        with Locations(Location(Vector(0.0, slot_cy, ring_t / 2))):
            Box(
                p.ANTENNA_SLOT_W,
                p.ANTENNA_SLOT_D + 0.02,
                ring_t + 0.02,
                mode=Mode.SUBTRACT,
            )

        # ── 6. Chip A recess: shallow pocket on back face (+Y rim zone) ─
        with Locations(Location(Vector(0.0, chip_a_cy, p.CHIP_A_RECESS_T / 2))):
            Cylinder(
                radius=p.CHIP_A_RECESS_D / 2,
                height=p.CHIP_A_RECESS_T + 0.02,
                mode=Mode.SUBTRACT,
            )

        # ── 7. Two chain holes in mounting tab ──────────────────────────
        for lh_y in (lh_y1, lh_y2):
            with Locations(Location(Vector(lh_cx, lh_y, ring_t / 2))):
                Cylinder(
                    radius=p.LANYARD_HOLE_D / 2,
                    height=ring_t + 0.02,
                    mode=Mode.SUBTRACT,
                )

        # ── 8. Engraving relief pockets + example text on each facet ────
        if engrave_w > 0 and engrave_h > 0:
            for i in range(p.N_FACETS):
                alpha_deg = 90.0 - i * 60.0
                alpha_rad = math.radians(alpha_deg)
                f_cx = (outer_apo - p.ENGRAVE_DEPTH / 2) * math.cos(alpha_rad)
                f_cy = (outer_apo - p.ENGRAVE_DEPTH / 2) * math.sin(alpha_rad)
                loc = Location(
                    Vector(f_cx, f_cy, ring_t / 2),
                    Vector(0, 0, 1),
                    alpha_deg,
                )
                with Locations(loc):
                    Box(
                        p.ENGRAVE_DEPTH + 0.02,
                        engrave_w,
                        engrave_h,
                        mode=Mode.SUBTRACT,
                    )

                # Example text engraving inside the relief pocket
                label = FACET_EXAMPLES.get(i, "")
                if label:
                    try:
                        font_size = min(1.4, engrave_h * 0.45)
                        normal_v  = Vector(math.cos(alpha_rad), math.sin(alpha_rad), 0.0)
                        x_dir_v   = Vector(-math.sin(alpha_rad), math.cos(alpha_rad), 0.0)
                        text_origin = Vector(
                            (outer_apo - p.ENGRAVE_DEPTH) * math.cos(alpha_rad),
                            (outer_apo - p.ENGRAVE_DEPTH) * math.sin(alpha_rad),
                            ring_t / 2,
                        )
                        text_plane = Plane(
                            origin=text_origin, x_dir=x_dir_v, z_dir=normal_v
                        )
                        with BuildSketch(text_plane):
                            Text(label, font_size=font_size,
                                 align=(Align.CENTER, Align.CENTER))
                        extrude(amount=-p.ENGRAVE_DEPTH, mode=Mode.SUBTRACT)
                    except Exception:
                        pass  # text is cosmetic; skip if unsupported

        # ── 9. TURN / PULL instruction on back face (ADR-0043) ──────────
        try:
            back_text_y = inner_apo * 0.65   # ~9.2 mm from centre, within solid plate
            for text, ty in (("TURN", back_text_y), ("PULL", -back_text_y)):
                with BuildSketch(Plane.XY):
                    with Locations(Location(Vector(0.0, ty, 0.0))):
                        Text(text, font_size=1.0,
                             align=(Align.CENTER, Align.CENTER))
                extrude(amount=p.ENGRAVE_DEPTH, mode=Mode.SUBTRACT)
        except Exception:
            pass  # cosmetic; skip if unsupported

        # ── 10. Body chamfer: back-face outer perimeter ─────────────────
        if p.BODY_CHAMFER > 0:
            try:
                back_outer = (
                    bp.edges()
                    .filter_by(GeomType.LINE)
                    .filter_by_position(Axis.Z, -1e-3, 1e-3)
                )
                if back_outer:
                    chamfer(back_outer, length=p.BODY_CHAMFER)
            except Exception:
                pass

        # ── 11. Chain hole chamfers ──────────────────────────────────────
        if p.LANYARD_CHAMFER > 0:
            for lh_y in (lh_y1, lh_y2):
                try:
                    lh_edges = (
                        bp.edges()
                        .filter_by(GeomType.CIRCLE)
                        .filter_by_position(
                            Axis.X, lh_cx - p.LANYARD_HOLE_D, lh_cx + p.LANYARD_HOLE_D,
                        )
                        .filter_by_position(
                            Axis.Y, lh_y - p.LANYARD_HOLE_D, lh_y + p.LANYARD_HOLE_D,
                        )
                    )
                    if lh_edges:
                        chamfer(lh_edges, length=p.LANYARD_CHAMFER)
                except Exception:
                    pass

    part = bp.part
    part.color = _COLOR_RING
    return part


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

        # ── 4. Engraving relief zones on core facets ──────────────────────
        # Same 6-facet layout as the ring but using CORE_ENGRAVE_* params.
        # Both parts carry the same fields so either is independently identifiable.
        core_apo  = _hex_apothem(core_ac)
        c_engrave_w = core_ac / 2 - 2 * p.CORE_ENGRAVE_MARGIN
        c_engrave_h = core_h - 2 * p.CORE_ENGRAVE_MARGIN
        if c_engrave_w > 0 and c_engrave_h > 0:
            for i in range(p.N_FACETS):
                alpha_deg = 90.0 - i * 60.0
                alpha_rad = math.radians(alpha_deg)
                f_cx = (core_apo - p.CORE_ENGRAVE_DEPTH / 2) * math.cos(alpha_rad)
                f_cy = (core_apo - p.CORE_ENGRAVE_DEPTH / 2) * math.sin(alpha_rad)
                loc = Location(
                    Vector(f_cx, f_cy, z0 + core_h / 2),
                    Vector(0, 0, 1),
                    alpha_deg,
                )
                with Locations(loc):
                    Box(
                        p.CORE_ENGRAVE_DEPTH + 0.02,
                        c_engrave_w,
                        c_engrave_h,
                        mode=Mode.SUBTRACT,
                    )

    part = bp.part
    part.color = _COLOR_CORE
    return part


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


def build_chain_stubs(p: HexaParams = P) -> Compound:
    """Chain stubs only — for per-part Blender render."""
    lh_cx    = p.RING_ACROSS_CORNERS / 2 + (p.CHAIN_TAB_DEPTH - 1.0) / 2
    lh_y1    = +p.CHAIN_HOLE_SPACING / 2
    lh_y2    = -p.CHAIN_HOLE_SPACING / 2
    chain_r  = p.CHAIN_NECK_D / 2
    stub_len = 30.0
    ring_t   = p.RING_T
    bridge_z = -4.0

    parts = []
    for lh_y in (lh_y1, lh_y2):
        with BuildPart() as seg_above:
            with Locations(Location(Vector(lh_cx, lh_y, ring_t + stub_len / 2))):
                Cylinder(radius=chain_r, height=stub_len)
        seg_above.part.color = _COLOR_CHAIN
        parts.append(seg_above.part)

        below_len = abs(bridge_z)
        with BuildPart() as seg_below:
            with Locations(Location(Vector(lh_cx, lh_y, bridge_z + below_len / 2))):
                Cylinder(radius=chain_r, height=below_len)
        seg_below.part.color = _COLOR_CHAIN
        parts.append(seg_below.part)

    bridge_span = abs(lh_y1 - lh_y2)
    with BuildPart() as bridge:
        with Locations(Location(Vector(lh_cx, 0.0, bridge_z), Vector(1, 0, 0), 90)):
            Cylinder(radius=chain_r, height=bridge_span)
    bridge.part.color = _COLOR_CHAIN
    parts.append(bridge.part)

    return Compound(children=parts)


def build_worn(p: HexaParams = P) -> Compound:
    """Assembly + chain showing how the tag is worn on a ball chain.

    The chain threads through TWO holes at the +X vertex (±CHAIN_HOLE_SPACING/2 in Y).
    This prevents the tag from rotating — it hangs flat, point-down.

    Chain routing: exits hole 1 upward → goes up chain · hole 1 downward → bridge
    behind the tag → hole 2 upward → goes up chain · hole 2 exits upward.
    Shown as: two upward stubs + two downward stubs + one horizontal bridge.
    """
    ring = build_ring(p)
    core = build_core(p)

    lh_cx    = p.RING_ACROSS_CORNERS / 2 + (p.CHAIN_TAB_DEPTH - 1.0) / 2
    lh_y1    = +p.CHAIN_HOLE_SPACING / 2
    lh_y2    = -p.CHAIN_HOLE_SPACING / 2
    chain_r  = p.CHAIN_NECK_D / 2
    stub_len = 30.0   # mm each chain segment above/below
    ring_t   = p.RING_T
    bridge_z = -4.0   # mm below back face for the bridge

    parts = [ring, core]

    for lh_y in (lh_y1, lh_y2):
        # Chain segment above (exiting front face upward)
        with BuildPart() as seg_above:
            with Locations(Location(Vector(lh_cx, lh_y, ring_t + stub_len / 2))):
                Cylinder(radius=chain_r, height=stub_len)
        seg_above.part.color = _COLOR_CHAIN
        parts.append(seg_above.part)

        # Chain segment below (exiting back face downward to bridge level)
        below_len = abs(bridge_z)
        with BuildPart() as seg_below:
            with Locations(Location(Vector(lh_cx, lh_y, bridge_z + below_len / 2))):
                Cylinder(radius=chain_r, height=below_len)
        seg_below.part.color = _COLOR_CHAIN
        parts.append(seg_below.part)

    # Horizontal bridge connecting the two downward exits behind the tag
    bridge_span = abs(lh_y1 - lh_y2)
    with BuildPart() as bridge:
        with Locations(Location(Vector(lh_cx, 0.0, bridge_z), Vector(1, 0, 0), 90)):
            Cylinder(radius=chain_r, height=bridge_span)
    bridge.part.color = _COLOR_CHAIN
    parts.append(bridge.part)

    return Compound(children=parts)
