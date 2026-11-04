"""Hexa Card alternative form factor (ADR-0056 Proposed).

Three elements on a neck chain:

  build_hex_card()       — hexagonal NFC card body (JCOP chip, polymer laminate)
  build_card_surround()  — silicone edge surround (modified dog-tag silencer)
  build_pull_token()     — 316L stainless pull-off identity token (UUID, no chip)
  build_card_assembly()  — card + surround combined
  build_full_assembly()  — Ti ring (simplified) + card assembly + pull token
  build_worn()           — full assembly on chain stubs (worn view)

Coordinate system (matches tag.py convention):
  x, y : card/token centre
  z     : 0 at back face, +z toward front face

For a flat wear-view the card lies in XY; chain runs along +Y from the top vertex.
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

# NFC hex card
CARD_AC         = 40.0   # mm — across-corners (matches ring outer size)
CARD_T          = 3.5    # mm — total card thickness
CARD_CHAMFER    = 0.4    # mm — edge chamfer
CARD_HOLE_D     = 3.5    # mm — chain hole diameter (at top vertex)
CHIP_W          = 3.5    # mm — JCOP chip width
CHIP_D          = 2.0    # mm — JCOP chip depth
CHIP_H          = 1.2    # mm — JCOP chip height
COIL_T          = 0.4    # mm — coil trace width
COIL_H          = 0.25   # mm — coil trace height
ENGRAVE_DEPTH   = 0.15   # mm — face engraving depth (UUID, SURNAME)
ENGRAVE_H_CHAR  = 1.4    # mm — engraved character height

# Silicone surround
SIL_WALL        = 1.8    # mm — perimeter wall thickness
SIL_FLANGE      = 0.6    # mm — face overhang (top and bottom)
# Outer surround across-corners: each flat of a hex needs +SIL_WALL on each side.
# For a regular hex, adding a uniform offset d to all faces:
#   new_apothem = old_apothem + d  →  new_AC = (new_apothem + d) / cos30 × 2
# Simplified: outer AC ≈ CARD_AC + 2 * SIL_WALL / cos(30°)
SIL_AC = CARD_AC + 2 * SIL_WALL / math.cos(math.radians(30))

# 316L pull-off token
TOKEN_AC        = 30.0   # mm — across-corners (smaller than card)
TOKEN_T         = 3.0    # mm — thickness
TOKEN_HOLE_D    = 3.5    # mm — chain hole diameter
TOKEN_ENGRAVE_D = 0.15   # mm — engraving depth

# Chain geometry (reuse params from tag.py defaults)
BALL_D          = 2.4    # mm
NECK_D          = 1.6    # mm
CHAIN_LEN       = 40.0   # mm — stub shown in worn view

# Ti ring (simplified — no inner cavity, no bayonet)
RING_AC         = 40.0   # mm — matches existing ring design
RING_T          = 5.2    # mm — total axial thickness
RING_RIM_T      = 3.6    # mm — radial rim thickness
RING_FACE_T     = 1.2    # mm

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

_COLOR_CARD     = Color(0.93, 0.93, 0.91)   # off-white PC laminate
_COLOR_SILICONE = Color(0.10, 0.10, 0.10)   # black silicone surround
_COLOR_STEEL    = Color(0.60, 0.60, 0.62)   # 316L stainless pull-off token
_COLOR_RING     = Color(0.72, 0.72, 0.76)   # Ti Gr5 bead-blast ring
_COLOR_CHIP     = Color(0.02, 0.02, 0.02)   # black epoxy JCOP package
_COLOR_COPPER   = Color(0.72, 0.42, 0.10)   # copper antenna trace
_COLOR_CHAIN    = Color(0.65, 0.65, 0.67)   # stainless ball chain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_apothem(ac: float) -> float:
    """Centre-to-flat-face distance for a regular hexagon."""
    return ac / 2 * math.cos(math.radians(30))


def _ball_chain_y(x: float, y_start: float, z: float,
                  length: float, color: Color) -> list:
    """Ball chain along +Y from (x, y_start, z). Returns list of parts."""
    neck_len = NECK_D * 0.6
    pitch = BALL_D + neck_len
    n = max(1, int(length / pitch))
    parts = []
    for i in range(n):
        cy = y_start + i * pitch + BALL_D / 2
        with BuildPart() as bead:
            with Locations(Location(Vector(x, cy, z))):
                Sphere(radius=BALL_D / 2)
        bead.part.color = color
        parts.append(bead.part)
        if i < n - 1:
            ny = cy + BALL_D / 2
            with BuildPart() as neck:
                with Locations(Location(Vector(x, ny + neck_len / 2, z),
                                        Vector(1, 0, 0), 90)):
                    Cylinder(radius=NECK_D / 2, height=neck_len)
            neck.part.color = color
            parts.append(neck.part)
    return parts


# ---------------------------------------------------------------------------
# NFC hex card
# ---------------------------------------------------------------------------

def build_hex_card() -> Compound:
    """Hexagonal NFC card — PC/PETG laminate with embedded JCOP chip and 2-turn coil."""
    card_r   = CARD_AC / 2
    card_apo = _hex_apothem(CARD_AC)
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
    body.part.color = _COLOR_CARD

    # ── Chain hole at +Y vertex ──────────────────────────────────────────────
    # The top vertex of the hex (pointing +Y after the standard 90° rotation) is
    # at y = card_r from centre. We cut a vertical cylinder through the card there.
    hole_y = card_r - CARD_HOLE_D / 2 - 0.5   # pull back slightly from vertex tip
    with BuildPart() as hole_cut:
        with Locations(Location(Vector(0, hole_y, CARD_T / 2))):
            Cylinder(radius=CARD_HOLE_D / 2, height=CARD_T + 1,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER))
    # Boolean subtract: build_body - hole_cut
    card_solid = body.part - hole_cut.part
    card_solid.color = _COLOR_CARD
    parts.append(card_solid)

    # ── JCOP chip representation ──────────────────────────────────────────────
    # Chip sits embedded near the centre of the card, slightly offset in +X
    chip_z = CARD_T / 2 - CHIP_H / 2  # centred in card thickness
    with BuildPart() as chip:
        with Locations(Location(Vector(2.0, 0.0, chip_z + CHIP_H / 2))):
            Box(CHIP_W, CHIP_D, CHIP_H,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    chip.part.color = _COLOR_CHIP
    parts.append(chip.part)

    # ── Coil turns (2-turn hexagonal antenna) ────────────────────────────────
    # Represent each coil turn as a thin hex-ring solid in XY at coil_z.
    # Outer turn: 90% of card apothem; inner turn: 70% of card apothem.
    coil_z_base = COIL_H  # from card back face
    for turn_scale in (0.90, 0.70):
        turn_r = card_r * turn_scale
        with BuildPart() as outer_hex:
            with BuildSketch(Plane.XY.offset(coil_z_base)):
                RegularPolygon(radius=turn_r, side_count=6)
            extrude(amount=COIL_H)
        with BuildPart() as inner_hex:
            inner_r = turn_r - COIL_T / math.cos(math.radians(30))
            with BuildSketch(Plane.XY.offset(coil_z_base)):
                RegularPolygon(radius=max(inner_r, turn_r * 0.85), side_count=6)
            extrude(amount=COIL_H)
        try:
            coil_ring = outer_hex.part - inner_hex.part
            coil_ring.color = _COLOR_COPPER
            parts.append(coil_ring)
        except Exception:
            pass

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


# ---------------------------------------------------------------------------
# Silicone edge surround
# ---------------------------------------------------------------------------

def build_card_surround() -> Compound:
    """Silicone hex surround — wraps the card perimeter and flanges both faces."""
    sil_r  = SIL_AC / 2
    card_r = CARD_AC / 2
    sil_t  = CARD_T + 2 * SIL_FLANGE   # total axial height

    # ── Outer hex prism ───────────────────────────────────────────────────────
    with BuildPart() as outer:
        with BuildSketch(Plane.XY.offset(-SIL_FLANGE)):
            RegularPolygon(radius=sil_r, side_count=6)
        extrude(amount=sil_t)

    # ── Inner cutout (card opening, no flange) ────────────────────────────────
    with BuildPart() as inner:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=card_r, side_count=6)
        extrude(amount=CARD_T)

    surround = outer.part - inner.part
    surround.color = _COLOR_SILICONE

    # Rotate to match card orientation after card's 90° rotation
    return Compound(children=[surround]).rotate(Axis.Z, 90)


# ---------------------------------------------------------------------------
# 316L pull-off token
# ---------------------------------------------------------------------------

def build_pull_token() -> Compound:
    """316L stainless hexagonal pull-off token — engraved UUID, no NFC chip."""
    token_r = TOKEN_AC / 2
    hole_y  = token_r - TOKEN_HOLE_D / 2 - 0.5
    parts   = []

    # ── Token body ────────────────────────────────────────────────────────────
    with BuildPart() as body:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=token_r, side_count=6)
        extrude(amount=TOKEN_T)
        try:
            chamfer(body.edges(), 0.3)
        except Exception:
            pass

    # ── Chain hole ────────────────────────────────────────────────────────────
    with BuildPart() as hole_cut:
        with Locations(Location(Vector(0, hole_y, TOKEN_T / 2))):
            Cylinder(radius=TOKEN_HOLE_D / 2, height=TOKEN_T + 1,
                     align=(Align.CENTER, Align.CENTER, Align.CENTER))

    token_solid = body.part - hole_cut.part
    token_solid.color = _COLOR_STEEL
    parts.append(token_solid)

    # ── UUID engraving on front face (representational) ───────────────────────
    try:
        with BuildPart() as text_cut:
            with BuildSketch(Plane.XY.offset(TOKEN_T)):
                with Locations(Location(Vector(0.0, 0.0, 0.0))):
                    Text("A1B2C3D4E5F6A7B8",
                         font_size=1.4,
                         align=(Align.CENTER, Align.CENTER))
            extrude(amount=-TOKEN_ENGRAVE_D)
        engraved = token_solid - text_cut.part
        engraved.color = _COLOR_STEEL
        parts = [engraved]
    except Exception:
        pass

    result = Compound(children=parts)
    return result.rotate(Axis.Z, 90)


# ---------------------------------------------------------------------------
# Card assembly (card + silicone surround)
# ---------------------------------------------------------------------------

def build_card_assembly() -> Compound:
    """NFC card with silicone surround."""
    card     = build_hex_card()
    surround = build_card_surround()
    return Compound(children=[card, surround])


# ---------------------------------------------------------------------------
# Full assembly (ring + card assembly + pull token)
# ---------------------------------------------------------------------------

def build_simplified_ring() -> Compound:
    """Ti Gr5 ring — simplified variant (no inner cavity, no bayonet socket).

    In the card-form-factor design the ring is a solid hex frame: six engraved
    facets on the rim, chain tab at the +Y vertex. No bayonet features.
    For rendering purposes this is approximated as the existing ring geometry
    without the inner cavity extrusion.
    """
    ring_r   = RING_AC / 2
    ring_apo = _hex_apothem(RING_AC)
    inner_r  = ring_r - RING_RIM_T
    parts    = []

    # Outer hex prism
    with BuildPart() as outer:
        with BuildSketch(Plane.XY):
            RegularPolygon(radius=ring_r, side_count=6)
        extrude(amount=RING_T)

    # Inner cavity (kept shallow — ring is now mostly solid)
    inner_ac = RING_AC - 2 * RING_RIM_T
    with BuildPart() as inner:
        with BuildSketch(Plane.XY.offset(RING_FACE_T)):
            RegularPolygon(radius=inner_ac / 2, side_count=6)
        extrude(amount=RING_T - 2 * RING_FACE_T)

    ring_body = outer.part - inner.part

    # Chain tab at +X vertex (will end up at +Y after 90° rotation)
    tab_depth = 4.0
    tab_hw    = 6.0
    tab_x_ctr = ring_r + tab_depth / 2
    with BuildPart() as tab:
        with Locations(Location(Vector(tab_x_ctr, 0, RING_T / 2))):
            Box(tab_depth, tab_hw * 2, RING_T,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))

    ring_with_tab = ring_body + tab.part

    # Chain holes through tab
    hole_y1, hole_y2 = 3.0, -3.0
    hole_x = tab_x_ctr
    for hy in (hole_y1, hole_y2):
        with BuildPart() as hole:
            with Locations(Location(Vector(hole_x, hy, RING_T / 2))):
                Cylinder(radius=3.5 / 2, height=RING_T + 1,
                         align=(Align.CENTER, Align.CENTER, Align.CENTER))
        ring_with_tab = ring_with_tab - hole.part

    ring_with_tab.color = _COLOR_RING
    parts.append(ring_with_tab)

    return Compound(children=parts).rotate(Axis.Z, 90)


def build_full_assembly() -> Compound:
    """All three elements: Ti ring + NFC card + 316L pull-off token.

    Layout (in the worn plane, XY):
      - Ring centred at origin
      - Card centred 55 mm below ring (−Y), same Z plane
      - Token centred 100 mm below ring (−Y), same Z plane
    Elements are separated vertically to show the three-piece system.
    """
    ring  = build_simplified_ring()
    card  = build_card_assembly()
    token = build_pull_token()

    card_offset  = -(RING_AC / 2 + CARD_AC / 2 + 15)
    token_offset = card_offset - (CARD_AC / 2 + TOKEN_AC / 2 + 15)

    card_placed  = card.moved(Location(Vector(0, card_offset,  0)))
    token_placed = token.moved(Location(Vector(0, token_offset, 0)))

    return Compound(children=[ring, card_placed, token_placed])


# ---------------------------------------------------------------------------
# Worn view (chain stubs connecting the elements)
# ---------------------------------------------------------------------------

def build_worn() -> Compound:
    """Full assembly with ball-chain stubs showing how the three elements hang."""
    ring  = build_simplified_ring()
    card  = build_card_assembly()
    token = build_pull_token()

    ring_apo  = _hex_apothem(RING_AC)
    card_top  = -(RING_AC / 2 + 15)         # top of card region
    token_top = card_top - CARD_AC / 2 - 15  # top of token region

    card_placed  = card.moved(Location(Vector(0, card_top - CARD_AC / 2, 0)))
    token_placed = token.moved(Location(Vector(0, token_top - TOKEN_AC / 2, 0)))

    chain_z = RING_T / 2

    # Chain from ring tab (+Y) upward
    ring_chain_y = RING_AC / 2 + 4.0  # tab extends 4 mm beyond ring
    ring_chain = _ball_chain_y(0, ring_chain_y, chain_z, CHAIN_LEN, _COLOR_CHAIN)

    # Chain connecting ring to card
    gap_start = RING_AC / 2 + 4.0
    gap_end   = -(card_top)
    gap_mid   = -(gap_start + gap_end) / 2
    gap_chain = _ball_chain_y(0, -(gap_end - 2), chain_z,
                              gap_end - gap_start - 4, _COLOR_CHAIN)

    # Short chain for pull token (offset in Z to simulate the shorter chain)
    short_z  = RING_T / 2 + 2.0
    tok_chain = _ball_chain_y(0, ring_chain_y, short_z,
                              abs(token_top) + 5, _COLOR_CHAIN)

    all_parts = ([ring, card_placed, token_placed]
                 + ring_chain + gap_chain + tok_chain)

    return Compound(children=all_parts)
