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
    Sphere,
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
# NFC IC package (black epoxy) and copper antenna trace
_COLOR_CHIP   = Color(0.02, 0.02, 0.02)
_COLOR_COPPER = Color(0.72, 0.42, 0.10)

from .params import FACET_EXAMPLES, HexaParams, P


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_apothem(across_corners: float) -> float:
    """Centre-to-flat-face distance for a regular hexagon."""
    return across_corners / 2 * math.cos(math.radians(30))


# ---------------------------------------------------------------------------
# Chain helpers
# ---------------------------------------------------------------------------

def _ball_chain_y(x: float, y_start: float, z: float,
                  length: float, color: Color,
                  ball_d: float, neck_d: float) -> list:
    """Return a list of parts forming a ball chain along +Y from (x, y_start, z).

    Pitch = ball_d + neck_d*0.6 so beads slightly overlap the necks.
    """
    neck_len = neck_d * 0.6
    pitch = ball_d + neck_len
    n_beads = max(1, int(length / pitch))
    parts = []
    for i in range(n_beads):
        cy = y_start + i * pitch + ball_d / 2
        with BuildPart() as bead:
            with Locations(Location(Vector(x, cy, z))):
                Sphere(radius=ball_d / 2)
        bead.part.color = color
        parts.append(bead.part)
        if i < n_beads - 1:
            ny = cy + ball_d / 2
            with BuildPart() as neck:
                with Locations(Location(Vector(x, ny + neck_len / 2, z),
                                        Vector(1, 0, 0), 90)):
                    Cylinder(radius=neck_d / 2, height=neck_len)
            neck.part.color = color
            parts.append(neck.part)
    return parts


def _ball_chain_y_neg(x: float, y_start: float, z: float,
                      length: float, color: Color,
                      ball_d: float, neck_d: float) -> list:
    """Return ball chain parts along -Y from (x, y_start, z)."""
    neck_len = neck_d * 0.6
    pitch = ball_d + neck_len
    n_beads = max(1, int(length / pitch))
    parts = []
    for i in range(n_beads):
        cy = y_start - (i * pitch + ball_d / 2)
        with BuildPart() as bead:
            with Locations(Location(Vector(x, cy, z))):
                Sphere(radius=ball_d / 2)
        bead.part.color = color
        parts.append(bead.part)
        if i < n_beads - 1:
            ny = cy - ball_d / 2
            with BuildPart() as neck:
                with Locations(Location(Vector(x, ny - neck_len / 2, z),
                                        Vector(1, 0, 0), 90)):
                    Cylinder(radius=neck_d / 2, height=neck_len)
            neck.part.color = color
            parts.append(neck.part)
    return parts


def _ball_chain_x(x_start: float, y: float, z: float,
                  length: float, color: Color,
                  ball_d: float, neck_d: float) -> list:
    """Return ball chain parts along +X from (x_start, y, z)."""
    neck_len = neck_d * 0.6
    pitch = ball_d + neck_len
    n_beads = max(1, int(length / pitch))
    parts = []
    for i in range(n_beads):
        cx = x_start + i * pitch + ball_d / 2
        with BuildPart() as bead:
            with Locations(Location(Vector(cx, y, z))):
                Sphere(radius=ball_d / 2)
        bead.part.color = color
        parts.append(bead.part)
        if i < n_beads - 1:
            nx = cx + ball_d / 2
            with BuildPart() as neck:
                with Locations(Location(Vector(nx + neck_len / 2, y, z),
                                        Vector(0, 1, 0), 90)):
                    Cylinder(radius=neck_d / 2, height=neck_len)
            neck.part.color = color
            parts.append(neck.part)
    return parts


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
        # Facet 0 (alpha=90°, +Y face) carries the antenna slot — no engrave pocket there.
        if engrave_w > 0 and engrave_h > 0:
            for i in range(p.N_FACETS):
                if i == 0:
                    continue          # antenna slot facet: slot already occupies this face
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

        # ── 11. Body chamfer: front-face outer perimeter ────────────────
        if p.FRONT_CHAMFER > 0:
            try:
                front_outer = (
                    bp.edges()
                    .filter_by(GeomType.LINE)
                    .filter_by_position(Axis.Z, ring_t - 1e-3, ring_t + 1e-3)
                )
                if front_outer:
                    chamfer(front_outer, length=p.FRONT_CHAMFER)
            except Exception:
                pass

        # ── 13. Chain hole chamfers ──────────────────────────────────────
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
    part = part.rotate(Axis.Z, 90)   # tab vertex to +Y (points up when worn)
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

                # Example text on each core facet (same fields as ring).
                label = FACET_EXAMPLES.get(i, "")
                if label:
                    try:
                        font_size = min(1.2, c_engrave_h * 0.45)
                        normal_v  = Vector(math.cos(alpha_rad), math.sin(alpha_rad), 0.0)
                        x_dir_v   = Vector(-math.sin(alpha_rad), math.cos(alpha_rad), 0.0)
                        text_origin = Vector(
                            (core_apo - p.CORE_ENGRAVE_DEPTH) * math.cos(alpha_rad),
                            (core_apo - p.CORE_ENGRAVE_DEPTH) * math.sin(alpha_rad),
                            z0 + core_h / 2,
                        )
                        text_plane = Plane(
                            origin=text_origin, x_dir=x_dir_v, z_dir=normal_v
                        )
                        with BuildSketch(text_plane):
                            Text(label, font_size=font_size,
                                 align=(Align.CENTER, Align.CENTER))
                        extrude(amount=-p.CORE_ENGRAVE_DEPTH, mode=Mode.SUBTRACT)
                    except Exception:
                        pass

        # ── 5. Rotation indicator: "TURN" engraved on core front face ───
        # Visible through the open ring front (ADR-0042) — tells owner to twist.
        try:
            core_top = z0 + core_h
            with BuildSketch(Plane.XY.offset(core_top)):
                Text("TURN", font_size=1.4, align=(Align.CENTER, Align.CENTER))
            extrude(amount=-p.CORE_ENGRAVE_DEPTH, mode=Mode.SUBTRACT)
        except Exception:
            pass

        # ── 6. Edge chamfers: front and back hex perimeter ───────────────
        if p.CORE_CHAMFER > 0:
            for z_level in (z0, z0 + core_h):
                try:
                    edges = (
                        bp.edges()
                        .filter_by(GeomType.LINE)
                        .filter_by_position(Axis.Z, z_level - 1e-3, z_level + 1e-3)
                    )
                    if edges:
                        chamfer(edges, length=p.CORE_CHAMFER)
                except Exception:
                    pass

    part = bp.part
    part.color = _COLOR_CORE
    part = part.rotate(Axis.Z, 90)   # match ring orientation
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

    lower_len = 8.0  # chain loops below the mounting tab before bridging
    ball_d    = p.CHAIN_BALL_D

    parts = []
    for lh_y in (lh_y1, lh_y2):
        lh_x_rot = -lh_y
        parts += _ball_chain_y(lh_x_rot, lh_cx, 0.0, stub_len, _COLOR_CHAIN,
                               ball_d, p.CHAIN_NECK_D)
        parts += _ball_chain_y_neg(lh_x_rot, lh_cx, 0.0, lower_len, _COLOR_CHAIN,
                                   ball_d, p.CHAIN_NECK_D)

    bridge_y    = lh_cx - lower_len
    bridge_x0   = -abs(lh_y1) - ball_d
    bridge_span = abs(lh_y1 - lh_y2) + 2 * ball_d
    parts += _ball_chain_x(bridge_x0, bridge_y, -chain_r, bridge_span, _COLOR_CHAIN,
                           ball_d, p.CHAIN_NECK_D)

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
    stub_len = 30.0   # mm above the mounting tab toward the neck
    ring_t   = p.RING_T

    lower_len = 8.0  # mm the chain loops below the mounting tab before bridging
    ball_d    = p.CHAIN_BALL_D

    parts = [ring, core]

    # Upward stubs: chain comes from the neck, enters each hole from above.
    for lh_y in (lh_y1, lh_y2):
        lh_x_rot = -lh_y
        parts += _ball_chain_y(lh_x_rot, lh_cx, 0.0, stub_len, _COLOR_CHAIN,
                               ball_d, p.CHAIN_NECK_D)

    # Downward stubs: chain exits each hole downward, looping below the tab.
    for lh_y in (lh_y1, lh_y2):
        lh_x_rot = -lh_y
        parts += _ball_chain_y_neg(lh_x_rot, lh_cx, 0.0, lower_len, _COLOR_CHAIN,
                                   ball_d, p.CHAIN_NECK_D)

    # Bridge: connects the two downward stubs below the tab, slightly behind the back face.
    bridge_y    = lh_cx - lower_len
    bridge_x0   = -abs(lh_y1) - ball_d
    bridge_span = abs(lh_y1 - lh_y2) + 2 * ball_d
    parts += _ball_chain_x(bridge_x0, bridge_y, -chain_r, bridge_span, _COLOR_CHAIN,
                           ball_d, p.CHAIN_NECK_D)

    return Compound(children=parts)


# ---------------------------------------------------------------------------
# Electronics / RFID internals (ADR-0003, ADR-0038, ADR-0045)
# ---------------------------------------------------------------------------

def build_ring_electronics(p: HexaParams = P) -> Compound:
    """Chip A NFC IC + slotted-ring antenna trace, positioned inside the ring.

    Origin matches build_ring(): back face at z=0, rotated 90° CCW.
    - Black IC package in the Chip A recess on the back face.
    - Copper hex loop tracing the RF current path around the inner bore.
    """
    inner_ac  = p.RING_INNER_ACROSS_CORNERS
    inner_apo = _hex_apothem(inner_ac)
    outer_apo = _hex_apothem(p.RING_ACROSS_CORNERS)
    chip_a_cy = (outer_apo + inner_apo) / 2

    parts = []

    # Chip A: NFC IC package in back-face recess — scaled up for visibility
    try:
        with BuildPart() as chip_bp:
            with Locations(Location(Vector(0.0, chip_a_cy, 1.0))):
                Box(5.0, 4.0, 2.0)
        chip_bp.part.color = _COLOR_CHIP
        parts.append(chip_bp.part)
    except Exception:
        pass

    # Ring antenna trace: copper hex loop around the inner bore.
    # The slotted-ring antenna uses the Ti ring as its inductive element;
    # this represents the matching/feed trace interrupted at the slot (+Y face).
    ant_trace_w = 1.4
    ant_h       = 1.5
    ant_z       = 0.5
    ant_r_outer = inner_ac / 2 - 0.2
    ant_r_inner = ant_r_outer - ant_trace_w

    try:
        with BuildPart() as ant_bp:
            with BuildSketch(Plane.XY.offset(ant_z)):
                RegularPolygon(radius=ant_r_outer, side_count=6,
                               align=(Align.CENTER, Align.CENTER))
            extrude(amount=ant_h)
            with BuildSketch(Plane.XY.offset(ant_z)):
                RegularPolygon(radius=ant_r_inner, side_count=6,
                               align=(Align.CENTER, Align.CENTER))
            extrude(amount=ant_h + 0.02, mode=Mode.SUBTRACT)
            with Locations(Location(Vector(0.0, inner_apo, ant_z + ant_h / 2))):
                Box(p.ANTENNA_SLOT_W + 0.5, ant_trace_w * 2 + 0.5, ant_h + 0.04,
                    mode=Mode.SUBTRACT)
        ant_bp.part.color = _COLOR_COPPER
        parts.append(ant_bp.part)
    except Exception:
        pass

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


def build_core_electronics(p: HexaParams = P) -> Compound:
    """Chip B NFC IC + flat spiral coil antenna, positioned on the core face.

    Origin matches build_core(): back face at z=0, rotated 90° CCW.
    - Black IC package in the Chip B recess on the core front face.
    - Three concentric copper hex loops representing the flat NFC coil.
    """
    core_ac  = p.CORE_ACROSS_CORNERS
    core_apo = _hex_apothem(core_ac)
    z0       = p.RING_FACE_T
    core_top = z0 + p.CORE_T

    parts = []

    # Chip B: NFC IC package on front face — scaled up for visibility
    try:
        with BuildPart() as chip_bp:
            with Locations(Location(Vector(0.0, 0.0, core_top + 1.0))):
                Box(4.0, 4.0, 2.0)
        chip_bp.part.color = _COLOR_CHIP
        parts.append(chip_bp.part)
    except Exception:
        pass

    # Flat coil: three concentric copper hex loops on the core front face.
    coil_z  = core_top + 0.1
    coil_t  = 0.5
    trace_w = 0.9
    for r_frac in (0.82, 0.63, 0.44):
        r_outer = core_apo * r_frac
        r_inner = r_outer - trace_w
        if r_inner < 1.5:
            continue
        try:
            with BuildPart() as loop_bp:
                with BuildSketch(Plane.XY.offset(coil_z)):
                    RegularPolygon(radius=r_outer, side_count=6,
                                   align=(Align.CENTER, Align.CENTER))
                extrude(amount=coil_t)
                with BuildSketch(Plane.XY.offset(coil_z)):
                    RegularPolygon(radius=r_inner, side_count=6,
                                   align=(Align.CENTER, Align.CENTER))
                extrude(amount=coil_t + 0.02, mode=Mode.SUBTRACT)
            loop_bp.part.color = _COLOR_COPPER
            parts.append(loop_bp.part)
        except Exception:
            pass

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


def build_electronics(p: HexaParams = P) -> Compound:
    """All RFID electronics in assembly position: Chip A + ring antenna + Chip B + coil."""
    return Compound(children=[build_ring_electronics(p), build_core_electronics(p)])
