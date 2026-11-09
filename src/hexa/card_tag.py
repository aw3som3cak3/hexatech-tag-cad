"""Hexa Card form factor (ADR-0056 Proposed — rev 5).

Two elements on a neck chain:

  build_hex_card()          — hexagonal NFC card with embedded JCOP chip + antenna
  build_card_grommet()      — 316L stainless flange grommet (UUID, fire-survival layer)
  build_card_surround()     — silicone hex edge surround (dog-tag silencer)
  build_tear_away()         — 316L stainless hex tear-away tag (full identity fields)
  build_card_assembly()     — card + surround + grommet combined
  build_full_assembly()     — card assembly + tear-away, laid out side by side
  build_worn()              — both elements on chain stubs (worn view)
  build_card_electronics()  — NFC inlay layer only (JCOP chip module + 2-turn coil)

Sizing: both elements 54 mm across-corners.
Hex orientation: pointy-top (vertex at +Y / chain hole). RegularPolygon rotation=30.

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
CARD_AC         = 54.0   # mm — hex card across-corners (ADR-0056 OQ-8 resolved)
CARD_T          = 3.5    # mm — card body thickness
CARD_CHAMFER    = 0.4    # mm — edge chamfer

# 316L double-flange grommet in chain hole (8–9 mm OD per RF + structural constraint)
GROMMET_OD       = 9.0  # mm — flange outer diameter; UUID laser-engraved on front flange face
GROMMET_BORE_D   = 3.5  # mm — chain bore diameter
GROMMET_FLANGE_T = 0.8  # mm — flange thickness on each face

# Silicone hex surround
SIL_WALL        = 1.8    # mm — perimeter wall thickness
SIL_FLANGE_T    = 0.6    # mm — face overhang on each side
SIL_AC          = CARD_AC + 2 * SIL_WALL / math.cos(math.radians(30))

# 316L steel tear-away — same outer size as card
TOKEN_AC        = 54.0   # mm — matching the card for a visual pair
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
_COLOR_CHIP     = Color(0.02, 0.02, 0.02)   # black epoxy JCOP module
_COLOR_COPPER   = Color(0.72, 0.42, 0.10)   # copper coil
_COLOR_CHAIN    = Color(0.65, 0.65, 0.67)   # stainless chain
_COLOR_INLAY    = Color(0.96, 0.92, 0.80)   # PET/PC inlay film


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

def build_card_grommet(barrel_height: float | None = None) -> Compound:
    """316L stainless double-flange grommet — pressed into card or tear-away chain hole.

    9 mm flange OD (RF-safe upper limit per EE review). UUID engraved on
    front flange face — flat surface, field-readable, fire-survivable.
    Fire-survival layer: grommet stays on chain after card plastic burns.
    barrel_height defaults to CARD_T; pass TOKEN_T for the tear-away grommet.
    """
    if barrel_height is None:
        barrel_height = CARD_T
    parts = []

    with BuildPart() as tube:
        Cylinder(radius=GROMMET_OD / 2,
                 height=barrel_height + 2 * GROMMET_FLANGE_T,
                 align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildPart() as bore:
        Cylinder(radius=GROMMET_BORE_D / 2,
                 height=barrel_height + 2 * GROMMET_FLANGE_T + 0.1,
                 align=(Align.CENTER, Align.CENTER, Align.MIN))

    grommet_solid = tube.part - bore.part
    grommet_solid.color = _COLOR_STEEL
    parts.append(grommet_solid)

    # UUID engraving — split across flange annulus above and below the bore.
    # The bore (r=1.75mm) only occupies y ∈ [-1.75, +1.75], so ±2.5mm clears it.
    uuid_z = barrel_height + 2 * GROMMET_FLANGE_T
    try:
        with BuildPart() as uuid_text:
            with BuildSketch(Plane.XY.offset(uuid_z)):
                with Locations(Location(Vector(0, +2.5, 0))):
                    Text("A1B2", font_size=0.7,
                         align=(Align.CENTER, Align.CENTER))
                with Locations(Location(Vector(0, -2.5, 0))):
                    Text("C3D4", font_size=0.7,
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
    Hex orientation: pointy-top (rotation=30 so vertex lands on +Y axis).
    """
    card_r   = CARD_AC / 2
    hole_y   = card_r - GROMMET_OD / 2 - 1.5   # 1.5 mm margin inside hex vertex
    parts    = []

    # ── Card body ────────────────────────────────────────────────────────────
    with BuildPart() as body:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=card_r, side_count=6, rotation=30)
        extrude(amount=CARD_T)
        try:
            chamfer(body.edges(), CARD_CHAMFER)
        except Exception:
            pass

    # ── Grommet pocket (flange recesses + through bore) ─────────────────────
    with BuildPart() as pocket:
        with Locations(Location(Vector(0, hole_y, CARD_T / 2))):
            Cylinder(radius=GROMMET_BORE_D / 2 + 0.05,
                     height=CARD_T + 1,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER))
    with BuildPart() as flange_pocket:
        with Locations(Location(Vector(0, hole_y, CARD_T))):
            Cylinder(radius=GROMMET_OD / 2 + 0.05,
                     height=GROMMET_FLANGE_T + 0.05,
                     align=(Align.CENTER, Align.CENTER, Align.MAX))
        with Locations(Location(Vector(0, hole_y, 0))):
            Cylinder(radius=GROMMET_OD / 2 + 0.05,
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

    # ── 2-turn hex coil — outer ~50 mm AC (turn_scale 0.93 × CARD_AC) ────────
    # Keep-out at grommet hole done in sketch (more robust than 3D boolean).
    for turn_scale in (0.93, 0.80):
        t_r     = card_r * turn_scale
        inner_r = t_r * (1 - COIL_T / (t_r * math.cos(math.radians(30))))
        try:
            with BuildPart() as coil_part:
                with BuildSketch(Plane.XY.offset(COIL_Z)):
                    RegularPolygon(radius=t_r, side_count=6, rotation=30)
                    RegularPolygon(radius=max(inner_r, t_r * 0.86), side_count=6,
                                   rotation=30, mode=Mode.SUBTRACT)
                    with Locations(Location(Vector(0, hole_y, 0))):
                        Circle(GROMMET_OD / 2 + 0.5, mode=Mode.SUBTRACT)
                extrude(amount=COIL_H)
            coil_part.part.color = _COLOR_COPPER
            parts.append(coil_part.part)
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
    return result


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
            RegularPolygon(radius=sil_r, side_count=6, rotation=30)
        extrude(amount=sil_t)
    with BuildPart() as inner:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=card_r, side_count=6, rotation=30)
        extrude(amount=CARD_T)

    surround = outer.part - inner.part
    # Cut chain bore through the two face flanges at the grommet position
    _gy = CARD_AC / 2 - GROMMET_OD / 2 - 1.5
    with BuildPart() as _chain_bore:
        with Locations(Location(Vector(0, _gy, -SIL_FLANGE_T - 0.1))):
            Cylinder(radius=GROMMET_BORE_D / 2 + 0.5,
                     height=CARD_T + 2 * SIL_FLANGE_T + 0.2,
                     align=(Align.CENTER, Align.CENTER, Align.MIN))
    surround = surround - _chain_bore.part
    surround.color = _COLOR_SILICONE
    return Compound(children=[surround])


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
    hole_y  = token_r - GROMMET_OD / 2 - 1.5   # 1.5 mm margin inside hex vertex
    parts   = []

    # ── Token body ────────────────────────────────────────────────────────────
    with BuildPart() as body:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=token_r, side_count=6, rotation=30)
        extrude(amount=TOKEN_T)
        try:
            chamfer(body.edges(), TOKEN_CHAMFER)
        except Exception:
            pass

    # ── Grommet pocket (flange recesses + through bore) ─────────────────────
    with BuildPart() as pocket:
        with Locations(Location(Vector(0, hole_y, TOKEN_T / 2))):
            Cylinder(radius=GROMMET_BORE_D / 2 + 0.05,
                     height=TOKEN_T + 1,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER))
    with BuildPart() as flange_pocket:
        with Locations(Location(Vector(0, hole_y, TOKEN_T))):
            Cylinder(radius=GROMMET_OD / 2 + 0.05,
                     height=GROMMET_FLANGE_T + 0.05,
                     align=(Align.CENTER, Align.CENTER, Align.MAX))
        with Locations(Location(Vector(0, hole_y, 0))):
            Cylinder(radius=GROMMET_OD / 2 + 0.05,
                     height=GROMMET_FLANGE_T + 0.05,
                     align=(Align.CENTER, Align.CENTER, Align.MIN))

    token_solid = body.part - pocket.part - flange_pocket.part
    token_solid.color = _COLOR_STEEL
    parts.append(token_solid)

    # ── Face text — raised + contrasting colour (engraving invisible on grey steel) ─
    token_apo = _hex_apothem(TOKEN_AC)
    text_rows = [
        ("DOE",         token_apo * 0.55),
        ("JOHN A",      token_apo * 0.32),
        ("A1B2C3D4",    token_apo * 0.08),
        ("E5F6A7B8",   -token_apo * 0.15),
        ("1 INF BN",   -token_apo * 0.38),
        ("SWE  2026",  -token_apo * 0.60),
    ]
    _text_col = Color(0.92, 0.88, 0.76)   # warm off-white — contrasts against steel grey
    try:
        for label, ty in text_rows:
            with BuildPart() as txt:
                with BuildSketch(Plane.XY.offset(TOKEN_T)):
                    with Locations(Location(Vector(0, ty, 0))):
                        Text(label, font_size=1.8,
                             align=(Align.CENTER, Align.CENTER))
                extrude(amount=0.3)
            txt.part.color = _text_col
            parts.append(txt.part)
    except Exception:
        pass

    # Grommet placed in hole
    grommet = build_card_grommet(barrel_height=TOKEN_T).moved(
        Location(Vector(0, hole_y, -GROMMET_FLANGE_T)))
    parts.append(grommet)

    result = Compound(children=parts)
    return result


# ---------------------------------------------------------------------------
# NFC inlay / electronics view
# ---------------------------------------------------------------------------

def build_card_electronics() -> Compound:
    """NFC inlay layer — JCOP chip module + 2-turn hex antenna coil.

    Shows the inlay without the card laminate body.
    Outer coil aperture ~50-51 mm AC (turn_scale 0.93 × CARD_AC / 54 mm body).
    Chain bore is cut from the substrate at the grommet position.
    """
    card_r  = CARD_AC / 2
    hole_y  = card_r - GROMMET_OD / 2 - 1.5
    _INLAY_T = 0.3   # mm — PET/PC film thickness
    _TRACE_H = 0.15  # mm — copper trace height above film
    _TRACE_W = 0.3   # mm — conductor width
    parts = []

    # ── Inlay substrate ───────────────────────────────────────────────────────
    with BuildPart() as slab:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=card_r - 0.5, side_count=6, rotation=30)
        extrude(amount=_INLAY_T)
    with BuildPart() as slab_bore:
        with Locations(Location(Vector(0, hole_y, _INLAY_T / 2))):
            Cylinder(radius=GROMMET_BORE_D / 2 + 0.2,
                     height=_INLAY_T + 0.1,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER))
    slab_solid = slab.part - slab_bore.part
    slab_solid.color = _COLOR_INLAY
    parts.append(slab_solid)

    # ── JCOP chip module — NFC inlay module ~5 × 3 mm ───────────────────────
    # Positioned so right edge sits on the inner coil right vertical side;
    # a bridge trace runs from inner coil right face to outer coil right face.
    _inner_apo = card_r * 0.80 * math.cos(math.radians(30))   # ≈ 18.71 mm
    _outer_apo = card_r * 0.93 * math.cos(math.radians(30))   # ≈ 21.73 mm
    _chip_w, _chip_d, _chip_h = 5.0, 3.0, 0.3
    _chip_x = _inner_apo - _chip_w / 2   # right chip edge flush with inner coil face
    with BuildPart() as module:
        with Locations(Location(Vector(_chip_x, 0.0, _INLAY_T))):
            Box(_chip_w, _chip_d, _chip_h,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    module.part.color = _COLOR_CHIP
    parts.append(module.part)

    # Bridge trace from inner coil right face to outer coil right face (chip bond)
    _bridge_len = _outer_apo - _inner_apo + 0.4   # slight overlap into both coil traces
    _bridge_cx  = (_inner_apo + _outer_apo) / 2
    try:
        with BuildPart() as bridge:
            with Locations(Location(Vector(_bridge_cx, 0.0, _INLAY_T))):
                Box(_bridge_len, 0.6, _TRACE_H,
                    align=(Align.CENTER, Align.CENTER, Align.MIN))
        bridge.part.color = _COLOR_COPPER
        parts.append(bridge.part)
    except Exception:
        pass

    # ── 2-turn hex coil — outer ~50 mm AC, inner ~43 mm AC ───────────────────
    # Keep-out at grommet hole done in sketch (no 3D boolean → no floating fragments).
    for turn_scale in (0.93, 0.80):
        t_r     = card_r * turn_scale
        inner_r = t_r - _TRACE_W / math.cos(math.radians(30))
        try:
            with BuildPart() as coil_part:
                with BuildSketch(Plane.XY.offset(_INLAY_T)):
                    RegularPolygon(radius=t_r, side_count=6, rotation=30)
                    RegularPolygon(radius=max(inner_r, t_r * 0.95), side_count=6,
                                   rotation=30, mode=Mode.SUBTRACT)
                    with Locations(Location(Vector(0, hole_y, 0))):
                        Circle(GROMMET_OD / 2 + 0.5, mode=Mode.SUBTRACT)
                extrude(amount=_TRACE_H)
            coil_part.part.color = _COLOR_COPPER
            parts.append(coil_part.part)
        except Exception:
            pass

    result = Compound(children=parts)
    return result


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

    # Chain from card hole upward (+Y) — exits top of grommet bore
    card_hole_y = CARD_AC / 2 - GROMMET_OD / 2 - 1.5 + GROMMET_BORE_D / 2
    card_chain  = _chain_y(0, card_hole_y, CARD_T / 2, CHAIN_LEN)

    # Short chain from tear-away hole upward
    tok_hole_y  = TOKEN_AC / 2 - GROMMET_OD / 2 - 1.5 + GROMMET_BORE_D / 2
    tok_chain   = _chain_y(token_offset_x, tok_hole_y, TOKEN_T / 2,
                            CHAIN_LEN * 0.5)

    # Short chain downward from tear-away (shows easy-pull separation)
    tok_chain_down = _chain_y_neg(token_offset_x, -tok_hole_y,
                                  TOKEN_T / 2, 20.0)

    all_parts = ([card_asm, token_placed]
                 + card_chain + tok_chain + tok_chain_down)
    return Compound(children=all_parts)
