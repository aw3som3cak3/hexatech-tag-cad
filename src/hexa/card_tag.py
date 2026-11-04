"""Hexa Card form factor (ADR-0056 Proposed — rev 2).

Two elements on a neck chain:

  build_hex_card()       — hexagonal NFC card with embedded JCOP chip + antenna
  build_card_grommet()   — 316L stainless flange grommet (UUID, fire-survival layer)
  build_card_surround()  — silicone hex edge surround (dog-tag silencer)
  build_tear_away()      — 316L stainless hex tear-away tag (full identity fields)
  build_card_assembly()  — card + surround + grommet combined
  build_full_assembly()  — card assembly + tear-away, laid out side by side
  build_worn()           — both elements on chain stubs (worn view)

Sizing: both elements ~48 mm across-corners — equivalent area to a US dog tag.

Coordinate system: z=0 at back face, +z toward front face, +Y toward chain hole.
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
    make_face,
)

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

# Both elements share the same outer footprint (~US dog tag area)
CARD_AC         = 48.0   # mm — hex card across-corners
CARD_T          = 3.5    # mm — card body thickness
CARD_CHAMFER    = 0.4    # mm — edge chamfer

# 316L flange grommet in chain hole
GROMMET_FLANGE_OD = 8.0  # mm — flange outer diameter (visible on face)
GROMMET_BORE_D    = 3.5  # mm — chain bore diameter
GROMMET_FLANGE_T  = 0.8  # mm — flange thickness on each face

# Silicone hex surround
SIL_WALL        = 1.8    # mm — perimeter wall thickness
SIL_FLANGE_T    = 0.6    # mm — face overhang on each side
SIL_AC          = CARD_AC + 2 * SIL_WALL / math.cos(math.radians(30))

# 316L steel tear-away — same outer size as card
TOKEN_AC        = 48.0   # mm — matching the card for a visual pair
TOKEN_T         = 2.5    # mm — solid steel, thinner than card
TOKEN_BORE_D    = 3.5    # mm — chain hole
TOKEN_CHAMFER   = 0.3    # mm

# NFC chip representation
CHIP_W  = 3.5    # mm
CHIP_D  = 2.0    # mm
CHIP_H  = 1.2    # mm

# Antenna coil representation
COIL_T  = 0.4    # mm — trace width
COIL_H  = 0.25   # mm — trace height above card back face
COIL_Z  = 0.4    # mm — z from card back face

# Engraving
ENGRAVE_D = 0.15  # mm

# Chain geometry
BALL_D    = 2.4   # mm
NECK_D    = 1.6   # mm
CHAIN_LEN = 50.0  # mm — stub length shown in worn view

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

_COLOR_CARD     = Color(0.93, 0.93, 0.91)   # off-white PC laminate
_COLOR_SILICONE = Color(0.10, 0.10, 0.10)   # black silicone
_COLOR_STEEL    = Color(0.60, 0.60, 0.62)   # 316L stainless
_COLOR_CHIP     = Color(0.02, 0.02, 0.02)   # black epoxy JCOP
_COLOR_COPPER   = Color(0.72, 0.42, 0.10)   # copper coil
_COLOR_CHAIN    = Color(0.65, 0.65, 0.67)   # stainless chain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_apothem(ac: float) -> float:
    return ac / 2 * math.cos(math.radians(30))


def _chain_y(x: float, y_start: float, z: float, length: float) -> list:
    """Ball chain along +Y. Returns list of colored parts."""
    neck_len = NECK_D * 0.6
    pitch    = BALL_D + neck_len
    n        = max(1, int(length / pitch))
    parts    = []
    for i in range(n):
        cy = y_start + i * pitch + BALL_D / 2
        with BuildPart() as bead:
            with Locations(Location(Vector(x, cy, z))):
                Sphere(radius=BALL_D / 2)
        bead.part.color = _COLOR_CHAIN
        parts.append(bead.part)
        if i < n - 1:
            ny = cy + BALL_D / 2
            with BuildPart() as neck:
                with Locations(Location(Vector(x, ny + neck_len / 2, z),
                                        Vector(1, 0, 0), 90)):
                    Cylinder(radius=NECK_D / 2, height=neck_len)
            neck.part.color = _COLOR_CHAIN
            parts.append(neck.part)
    return parts


def _chain_y_neg(x: float, y_start: float, z: float, length: float) -> list:
    """Ball chain along -Y. Returns list of colored parts."""
    neck_len = NECK_D * 0.6
    pitch    = BALL_D + neck_len
    n        = max(1, int(length / pitch))
    parts    = []
    for i in range(n):
        cy = y_start - (i * pitch + BALL_D / 2)
        with BuildPart() as bead:
            with Locations(Location(Vector(x, cy, z))):
                Sphere(radius=BALL_D / 2)
        bead.part.color = _COLOR_CHAIN
        parts.append(bead.part)
        if i < n - 1:
            ny = cy - BALL_D / 2
            with BuildPart() as neck:
                with Locations(Location(Vector(x, ny - neck_len / 2, z),
                                        Vector(1, 0, 0), 90)):
                    Cylinder(radius=NECK_D / 2, height=neck_len)
            neck.part.color = _COLOR_CHAIN
            parts.append(neck.part)
    return parts


# ---------------------------------------------------------------------------
# 316L flange grommet
# ---------------------------------------------------------------------------

def build_card_grommet() -> Compound:
    """316L stainless double-flange grommet — pressed into card chain hole.

    Protects card plastic from chain wear. UUID engraved on flange face.
    Fire-survival layer: grommet stays on chain after card plastic burns.
    """
    parts = []

    # Tube through card
    with BuildPart() as tube:
        Cylinder(radius=GROMMET_FLANGE_OD / 2,
                 height=CARD_T + 2 * GROMMET_FLANGE_T,
                 align=(Align.CENTER, Align.CENTER, Align.MIN))
    # Bore
    with BuildPart() as bore:
        Cylinder(radius=GROMMET_BORE_D / 2,
                 height=CARD_T + 2 * GROMMET_FLANGE_T + 0.1,
                 align=(Align.CENTER, Align.CENTER, Align.MIN))

    grommet_solid = tube.part - bore.part
    grommet_solid.color = _COLOR_STEEL
    parts.append(grommet_solid)

    # UUID engraving on front flange face (representational)
    uuid_z = CARD_T + 2 * GROMMET_FLANGE_T
    try:
        with BuildPart() as uuid_text:
            with BuildSketch(Plane.XY.offset(uuid_z)):
                with Locations(Location(Vector(0, 0, 0))):
                    Text("A1B2C3D4",
                         font_size=0.9,
                         align=(Align.CENTER, Align.CENTER))
            extrude(amount=-ENGRAVE_D)
        engraved = grommet_solid - uuid_text.part
        engraved.color = _COLOR_STEEL
        parts = [engraved]
    except Exception:
        pass

    return Compound(children=parts)


# ---------------------------------------------------------------------------
# NFC hex card
# ---------------------------------------------------------------------------

def build_hex_card() -> Compound:
    """Hexagonal NFC card — PC/PETG laminate, JCOP chip, 2-turn hex coil.

    Chain hole is at the +Y vertex (top). Grommet pocket matches grommet OD.
    """
    card_r   = CARD_AC / 2
    hole_y   = card_r - GROMMET_FLANGE_OD / 2 - 0.6
    parts    = []

    # ── Card body ────────────────────────────────────────────────────────────
    with BuildPart() as body:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=card_r, side_count=6)
        extrude(amount=CARD_T)
        try:
            chamfer(body.edges(), CARD_CHAMFER)
        except Exception:
            pass

    # ── Grommet pocket (flange recess + through bore) ────────────────────────
    with BuildPart() as pocket:
        # Through bore
        with Locations(Location(Vector(0, hole_y, CARD_T / 2))):
            Cylinder(radius=GROMMET_BORE_D / 2 + 0.05,
                     height=CARD_T + 1,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER))
    with BuildPart() as flange_pocket:
        # Front flange recess
        with Locations(Location(Vector(0, hole_y, CARD_T))):
            Cylinder(radius=GROMMET_FLANGE_OD / 2 + 0.05,
                     height=GROMMET_FLANGE_T + 0.05,
                     align=(Align.CENTER, Align.CENTER, Align.MAX))
        # Back flange recess
        with Locations(Location(Vector(0, hole_y, 0))):
            Cylinder(radius=GROMMET_FLANGE_OD / 2 + 0.05,
                     height=GROMMET_FLANGE_T + 0.05,
                     align=(Align.CENTER, Align.CENTER, Align.MIN))

    card_solid = body.part - pocket.part - flange_pocket.part
    card_solid.color = _COLOR_CARD
    parts.append(card_solid)

    # ── JCOP chip ─────────────────────────────────────────────────────────────
    with BuildPart() as chip:
        with Locations(Location(Vector(1.5, 0.0, CARD_T / 2))):
            Box(CHIP_W, CHIP_D, CHIP_H,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
    chip.part.color = _COLOR_CHIP
    parts.append(chip.part)

    # ── 2-turn hex coil ───────────────────────────────────────────────────────
    for turn_scale in (0.88, 0.70):
        t_r     = card_r * turn_scale
        inner_r = t_r * (1 - COIL_T / (t_r * math.cos(math.radians(30))))
        try:
            with BuildPart() as coil_outer:
                with BuildSketch(Plane.XY.offset(COIL_Z)):
                    RegularPolygon(radius=t_r, side_count=6)
                extrude(amount=COIL_H)
            with BuildPart() as coil_inner:
                with BuildSketch(Plane.XY.offset(COIL_Z)):
                    RegularPolygon(radius=max(inner_r, t_r * 0.86), side_count=6)
                extrude(amount=COIL_H)
            coil_ring = coil_outer.part - coil_inner.part
            coil_ring.color = _COLOR_COPPER
            parts.append(coil_ring)
        except Exception:
            pass

    # ── Face engraving text (representational) ────────────────────────────────
    card_apo  = _hex_apothem(CARD_AC)
    text_rows = [
        ("DOE",         card_apo * 0.55),
        ("JOHN A",      card_apo * 0.35),
        ("A1B2C3D4",    card_apo * 0.12),
        ("E5F6A7B8",   -card_apo * 0.08),
        ("1 INF BN",   -card_apo * 0.30),
    ]
    try:
        for label, ty in text_rows:
            with BuildPart() as txt:
                with BuildSketch(Plane.XY.offset(CARD_T)):
                    with Locations(Location(Vector(0, ty, 0))):
                        Text(label, font_size=1.8,
                             align=(Align.CENTER, Align.CENTER))
                extrude(amount=-ENGRAVE_D)
            card_solid = card_solid - txt.part
        card_solid.color = _COLOR_CARD
        parts[0] = card_solid
    except Exception:
        pass

    # Grommet placed in hole
    grommet = build_card_grommet().moved(
        Location(Vector(0, hole_y, -GROMMET_FLANGE_T)))
    parts.append(grommet)

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


# ---------------------------------------------------------------------------
# Silicone hex surround
# ---------------------------------------------------------------------------

def build_card_surround() -> Compound:
    """Silicone hex surround — wraps card perimeter, flanges both faces."""
    sil_r  = SIL_AC / 2
    card_r = CARD_AC / 2
    sil_t  = CARD_T + 2 * SIL_FLANGE_T

    with BuildPart() as outer:
        with BuildSketch(Plane.XY.offset(-SIL_FLANGE_T)):
            RegularPolygon(radius=sil_r, side_count=6)
        extrude(amount=sil_t)
    with BuildPart() as inner:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=card_r, side_count=6)
        extrude(amount=CARD_T)

    surround = outer.part - inner.part
    surround.color = _COLOR_SILICONE
    return Compound(children=[surround]).rotate(Axis.Z, 90)


# ---------------------------------------------------------------------------
# Card assembly (card + surround)
# ---------------------------------------------------------------------------

def build_card_assembly() -> Compound:
    """NFC card with silicone surround."""
    return Compound(children=[build_hex_card(), build_card_surround()])


# ---------------------------------------------------------------------------
# 316L steel tear-away
# ---------------------------------------------------------------------------

def build_tear_away() -> Compound:
    """316L stainless hex tear-away — same size as card, full identity fields.

    Engraved: SURNAME / GIVEN NAME / UUID / UNIT / NATIONALITY / DATE.
    Chain hole at +Y vertex with chamfered bore. Attached by short chain.
    """
    token_r = TOKEN_AC / 2
    hole_y  = token_r - TOKEN_BORE_D / 2 - 0.6
    parts   = []

    # ── Token body ────────────────────────────────────────────────────────────
    with BuildPart() as body:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=token_r, side_count=6)
        extrude(amount=TOKEN_T)
        try:
            chamfer(body.edges(), TOKEN_CHAMFER)
        except Exception:
            pass

    # ── Chain hole ────────────────────────────────────────────────────────────
    with BuildPart() as hole_cut:
        with Locations(Location(Vector(0, hole_y, TOKEN_T / 2))):
            Cylinder(radius=TOKEN_BORE_D / 2,
                     height=TOKEN_T + 1,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER))

    token_solid = body.part - hole_cut.part
    token_solid.color = _COLOR_STEEL
    parts.append(token_solid)

    # ── Face engraving (representational — front face) ────────────────────────
    token_apo = _hex_apothem(TOKEN_AC)
    text_rows = [
        ("DOE",         token_apo * 0.55),
        ("JOHN A",      token_apo * 0.32),
        ("A1B2C3D4",    token_apo * 0.08),
        ("E5F6A7B8",   -token_apo * 0.15),
        ("1 INF BN",   -token_apo * 0.38),
        ("SWE  2026",  -token_apo * 0.60),
    ]
    try:
        for label, ty in text_rows:
            with BuildPart() as txt:
                with BuildSketch(Plane.XY.offset(TOKEN_T)):
                    with Locations(Location(Vector(0, ty, 0))):
                        Text(label, font_size=1.8,
                             align=(Align.CENTER, Align.CENTER))
                extrude(amount=-ENGRAVE_D)
            token_solid = token_solid - txt.part
        token_solid.color = _COLOR_STEEL
        parts[0] = token_solid
    except Exception:
        pass

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


# ---------------------------------------------------------------------------
# Full layout and worn views
# ---------------------------------------------------------------------------

def build_full_assembly() -> Compound:
    """Card assembly + tear-away laid side by side for comparison.

    Card on left (x < 0), tear-away on right (x > 0), same Z plane.
    """
    card_asm = build_card_assembly()
    token    = build_tear_away()

    gap = 10.0
    card_x  = -(CARD_AC / 2 + gap / 2)
    token_x =  (TOKEN_AC / 2 + gap / 2)

    card_placed  = card_asm.moved(Location(Vector(card_x,  0, 0)))
    token_placed = token.moved(Location(Vector(token_x, 0, 0)))

    return Compound(children=[card_placed, token_placed])


def build_worn() -> Compound:
    """Card + tear-away on chain stubs, vertically arranged as worn.

    Card hangs above, tear-away on a shorter chain below/adjacent.
    Both chain stubs exit upward (+Y) to suggest a common neck chain.
    """
    card_asm = build_card_assembly()
    token    = build_tear_away()

    # Card centred at origin; tear-away 70 mm to the right (+X), simulating
    # the short-chain offset hanging beside the card on the same neck chain
    token_offset_x = TOKEN_AC / 2 + CARD_AC / 2 + 10.0
    token_placed   = token.moved(Location(Vector(token_offset_x, 0, 0)))

    # Chain from card hole upward (+Y)
    card_hole_y = CARD_AC / 2 - 1.5
    card_chain  = _chain_y(0, card_hole_y, CARD_T / 2, CHAIN_LEN)

    # Short chain from tear-away hole upward
    tok_hole_y  = TOKEN_AC / 2 - 1.5
    tok_chain   = _chain_y(token_offset_x, tok_hole_y, TOKEN_T / 2,
                            CHAIN_LEN * 0.5)

    # Short chain downward from tear-away (shows easy-pull separation)
    tok_chain_down = _chain_y_neg(token_offset_x, -(tok_hole_y),
                                  TOKEN_T / 2, 20.0)

    all_parts = ([card_asm, token_placed]
                 + card_chain + tok_chain + tok_chain_down)
    return Compound(children=all_parts)
