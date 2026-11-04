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


def _ball_chain_z(x: float, y: float, z_start: float,
                  length: float, color: Color,
                  ball_d: float, neck_d: float) -> list:
    """Return ball chain parts along +Z from (x, y, z_start)."""
    neck_len = neck_d * 0.6
    pitch = ball_d + neck_len
    n_beads = max(1, int(length / pitch))
    parts = []
    for i in range(n_beads):
        cz = z_start + i * pitch + ball_d / 2
        with BuildPart() as bead:
            with Locations(Location(Vector(x, y, cz))):
                Sphere(radius=ball_d / 2)
        bead.part.color = color
        parts.append(bead.part)
        if i < n_beads - 1:
            nz = cz + ball_d / 2
            with BuildPart() as neck:
                with Locations(Location(Vector(x, y, nz + neck_len / 2))):
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
    lower_len = 8.0
    ball_d    = p.CHAIN_BALL_D

    parts = []
    for lh_y in (lh_y1, lh_y2):
        lh_x_rot = -lh_y
        # Through-hole: chain threads through the tab in Z (back→front)
        parts += _ball_chain_z(lh_x_rot, lh_cx, 0.0, ring_t, _COLOR_CHAIN,
                               ball_d, p.CHAIN_NECK_D)
        # Upward stub: exits front face, goes toward neck
        parts += _ball_chain_y(lh_x_rot, lh_cx, ring_t, stub_len, _COLOR_CHAIN,
                               ball_d, p.CHAIN_NECK_D)
        # Downward stub: exits back face, loops below tab to bridge
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

    for lh_y in (lh_y1, lh_y2):
        lh_x_rot = -lh_y
        # Through-hole: chain threads through the mounting tab in Z (back→front)
        parts += _ball_chain_z(lh_x_rot, lh_cx, 0.0, ring_t, _COLOR_CHAIN,
                               ball_d, p.CHAIN_NECK_D)
        # Upward stub: exits front face, goes toward neck
        parts += _ball_chain_y(lh_x_rot, lh_cx, ring_t, stub_len, _COLOR_CHAIN,
                               ball_d, p.CHAIN_NECK_D)
        # Downward stub: exits back face, loops below tab to bridge
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
# Green FR4 PCB substrate colour (NFC flex PCB that carries chip + coil)
_COLOR_PCB = Color(0.07, 0.30, 0.09)


def build_ring_electronics(p: HexaParams = P) -> Compound:
    """Chip A NXP NTAG-I2C bonded across the antenna slot on the ring's back face.

    Physical model (pre-rotation, slot at +Y face):
    - Thin flex PCB patch sits on the back face rim at the +Y face.
    - Chip A (3.5×2.0×1.2 mm black package) bonded to the PCB, centred on the slot.
    - Two short copper feed traces bridge the slot gap (each pad → one slot wall).
    The Ti ring itself is the slotted-ring antenna; no extra copper loop is needed.

    After .rotate(Axis.Z, 90): slot face is at −X, chip at x≈−15.8 mm.
    """
    outer_apo = _hex_apothem(p.RING_ACROSS_CORNERS)
    inner_apo = _hex_apothem(p.RING_INNER_ACROSS_CORNERS)
    rim_mid_y = (outer_apo + inner_apo) / 2   # ≈ 15.8 mm
    slot_w    = p.ANTENNA_SLOT_W               # 1.2 mm (circumferential gap)

    chip_w, chip_d, chip_h = 3.5, 2.0, 1.2
    # Chip is recessed into the back face — sits from z=0 inward (away from parting groove at z=1.2mm)
    chip_y = rim_mid_y
    chip_z = chip_h / 2            # chip spans z=0 (back face) to z=chip_h=1.2mm

    trace_w = chip_w - slot_w          # total copper bridging both sides ≈ 2.3 mm
    trace_d = 0.5                      # trace depth (Y) — matches chip pad width
    trace_h = 0.4

    pcb_w = chip_w + 3.0
    pcb_d = chip_d + 1.5
    pcb_h = 0.3

    parts = []

    # Flex PCB substrate
    try:
        with BuildPart() as pcb_bp:
            with Locations(Location(Vector(0.0, chip_y, pcb_h / 2))):
                Box(pcb_w, pcb_d, pcb_h)
        pcb_bp.part.color = _COLOR_PCB
        parts.append(pcb_bp.part)
    except Exception:
        pass

    # Chip A body
    try:
        with BuildPart() as chip_bp:
            with Locations(Location(Vector(0.0, chip_y, chip_z))):
                Box(chip_w, chip_d, chip_h)
        chip_bp.part.color = _COLOR_CHIP
        parts.append(chip_bp.part)
    except Exception:
        pass

    # Two copper bond traces crossing the slot gap (one per antenna pad)
    for sign in (-1.0, +1.0):
        x_pad  = sign * chip_w / 2        # chip pad edge: ±1.75 mm
        x_slot = sign * slot_w / 2        # slot wall:     ±0.60 mm
        trace_len = abs(x_pad - x_slot)   # ≈ 1.15 mm
        trace_cx  = (x_pad + x_slot) / 2
        try:
            with BuildPart() as tr_bp:
                with Locations(Location(Vector(trace_cx, chip_y, chip_z))):
                    Box(trace_len, trace_d, trace_h)
            tr_bp.part.color = _COLOR_COPPER
            parts.append(tr_bp.part)
        except Exception:
            pass

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


def build_core_electronics(p: HexaParams = P) -> Compound:
    """Chip B NXP NTAG213 + 4-turn flat hex spiral coil on the core front face.

    Physical model (pre-rotation):
    - Flex PCB covers the core front face (z = core_top).
    - 4 hex coil turns of decreasing radius, each with a gap at the −Y face.
    - Adjacent turns connected by short radial bridge traces at the gap face.
    - Chip B (3.5×2.5×1.2 mm) sits on the PCB, offset toward +Y.
    - Feed trace connects outermost turn to chip pad 1.
    - Return trace at higher Z connects innermost turn to chip pad 2.

    After .rotate(Axis.Z, 90): gap/bridges at +X, chip at x≈−7 mm.
    """
    core_ac  = p.CORE_ACROSS_CORNERS
    core_apo = _hex_apothem(core_ac)         # ≈ 14.17 mm
    z0       = p.RING_FACE_T                 # 1.2 mm
    core_top = z0 + p.CORE_T                 # 4.0 mm
    apo_frac = math.cos(math.radians(30))    # 0.866

    coil_t  = 0.4                # coil trace height
    trace_w = 0.65               # coil trace width (radial)
    coil_z  = core_top - coil_t  # coil is on the INSIDE of the core front face

    # 4 turns: circumradii as fractions of core_apo
    r_fracs = (0.84, 0.69, 0.54, 0.39)

    chip_w, chip_d, chip_h = 3.5, 2.5, 1.2
    chip_y = core_apo * 0.52     # offset toward +Y (pre-rotation)
    chip_x = 0.0
    chip_z = core_top - chip_h / 2  # chip embedded in front face, top flush with core_top

    pcb_r  = core_apo * 0.92     # flex PCB hex radius ≈ core face

    parts = []

    # Flex PCB base layer on the inside of the core front face
    try:
        with BuildPart() as pcb_bp:
            with BuildSketch(Plane.XY.offset(coil_z - 0.25)):
                RegularPolygon(radius=pcb_r, side_count=6,
                               align=(Align.CENTER, Align.CENTER))
            extrude(amount=0.25)
        pcb_bp.part.color = _COLOR_PCB
        parts.append(pcb_bp.part)
    except Exception:
        pass

    # 4 coil turns: hex rings with gap at −Y face, radial bridge to next turn
    for i, r_frac in enumerate(r_fracs):
        r_outer = core_apo * r_frac
        r_inner = r_outer - trace_w
        if r_inner < 1.0:
            continue
        apo_outer = r_outer * apo_frac
        apo_inner = r_inner * apo_frac
        # Gap box cut at −Y flat face of this ring
        gap_cx_y  = -(apo_inner + (apo_outer - apo_inner) / 2)
        gap_w_cut = trace_w + 0.04   # just wider than trace so bridge fills it cleanly
        gap_d_cut = apo_outer - apo_inner + 0.3
        try:
            with BuildPart() as ring_bp:
                with BuildSketch(Plane.XY.offset(coil_z)):
                    RegularPolygon(radius=r_outer, side_count=6,
                                   align=(Align.CENTER, Align.CENTER))
                extrude(amount=coil_t)
                with BuildSketch(Plane.XY.offset(coil_z)):
                    RegularPolygon(radius=r_inner, side_count=6,
                                   align=(Align.CENTER, Align.CENTER))
                extrude(amount=coil_t + 0.02, mode=Mode.SUBTRACT)
                with Locations(Location(Vector(0.0, gap_cx_y, coil_z + coil_t / 2))):
                    Box(gap_w_cut, gap_d_cut, coil_t + 0.1, mode=Mode.SUBTRACT)
            ring_bp.part.color = _COLOR_COPPER
            parts.append(ring_bp.part)
        except Exception:
            pass

        # Radial bridge trace to next inner turn at the same gap face
        if i < len(r_fracs) - 1:
            r_next_outer = core_apo * r_fracs[i + 1]
            apo_next_outer = r_next_outer * apo_frac
            bridge_len = apo_inner - apo_next_outer
            if bridge_len > 0.05:
                bridge_cy = -(apo_next_outer + bridge_len / 2)
                try:
                    with BuildPart() as br_bp:
                        with Locations(Location(Vector(0.0, bridge_cy, coil_z + coil_t / 2))):
                            Box(trace_w, bridge_len + 0.05, coil_t)
                    br_bp.part.color = _COLOR_COPPER
                    parts.append(br_bp.part)
                except Exception:
                    pass

    # Chip B body
    try:
        with BuildPart() as chip_bp:
            with Locations(Location(Vector(chip_x, chip_y, chip_z))):
                Box(chip_w, chip_d, chip_h)
        chip_bp.part.color = _COLOR_CHIP
        parts.append(chip_bp.part)
    except Exception:
        pass

    # Feed trace: outermost ring → chip pad 1 (runs radially outward at +Y)
    r_out0 = core_apo * r_fracs[0]
    feed_len = chip_y - r_out0
    if feed_len > 0.05:
        try:
            with BuildPart() as feed_bp:
                with Locations(Location(Vector(chip_x - chip_w / 4,
                                               r_out0 + feed_len / 2,
                                               coil_z + coil_t / 2))):
                    Box(trace_w, feed_len, coil_t)
            feed_bp.part.color = _COLOR_COPPER
            parts.append(feed_bp.part)
        except Exception:
            pass

    # Return trace: innermost ring → chip pad 2, routed at higher Z to avoid crossing
    r_in_last = core_apo * r_fracs[-1]
    ret_z = coil_z + coil_t + 0.25
    ret_len = chip_y - r_in_last * 0.5
    if ret_len > 0.05:
        try:
            with BuildPart() as ret_bp:
                with Locations(Location(Vector(chip_x + chip_w / 4,
                                               r_in_last * 0.5 + ret_len / 2,
                                               ret_z))):
                    Box(trace_w * 0.8, ret_len, 0.3)
            ret_bp.part.color = _COLOR_COPPER
            parts.append(ret_bp.part)
        except Exception:
            pass

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


def build_electronics(p: HexaParams = P) -> Compound:
    """RFID electronics with ghost-transparent ring and core housing.

    Ring and core are shown at ~12% opacity so the internal electronics are
    visible through them. Alpha exports correctly as GLTF alphaMode BLEND.
    """
    ring = build_ring(p)
    core = build_core(p)
    # Apply transparent colours — alpha 0.12 (nearly see-through)
    ring.color = Color(0.72, 0.72, 0.76, 0.12)
    core.color = Color(0.18, 0.38, 0.72, 0.12)
    return Compound(children=[
        ring,
        core,
        build_ring_electronics(p),
        build_core_electronics(p),
    ])
