"""Single source of truth for the Hexa tag design.

Every dimension is either declared here or derived from values declared here.
Nothing downstream may contain a magic number.

Units: millimetres (mm) and degrees throughout.

Coordinate system
-----------------
    x : 0 at the centre of the tag, +x toward facet 1 (lanyard side)
    y : 0 at the centre, +y toward facet 2
    z : 0 at the back face of the ring, +z toward the front face

The ring sits with its back at z=0 and front face at z=RING_T.
The core inserts from z=0 (back), core front flushes at z=RING_T or is recessed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class HexaParams:
    # ── Outer ring ────────────────────────────────────────────────────────────
    RING_ACROSS_CORNERS: float = 40.0
    """mm  point-to-point (vertex to opposite vertex) — the nominal tag size."""

    RING_RIM_T: float = 3.6
    """mm  radial rim thickness — the annular wall the tag body forms."""

    RING_FACE_T: float = 1.2
    """mm  front and back face wall thickness (the thin hex panels)."""

    RING_FRONT_OPEN: bool = True
    """If True the front face plate is omitted: cavity extrude extends to z=RING_T,
    exposing the core face from the front. ADR-0042."""

    N_FACETS: int = 6
    """Number of flat facets — hexagonal; don't change unless rethinking the antenna slot."""

    # ── Core (ceramic carrier) ────────────────────────────────────────────────
    CORE_T: float = 2.8
    """mm  total axial thickness of the ceramic core + carrier assembly."""

    CORE_FLUSH_DEPTH: float = 0.5
    """mm  core face recessed below the ring's front bore edge.
    0 = flush; 0.5 creates a visible shadow line and fingernail purchase gap. ADR-0042."""

    # ── Bayonet ───────────────────────────────────────────────────────────────
    BAYONET_LUGS: int = 3
    """Number of lugs, evenly spaced (every 120° for 3-lug)."""

    BAYONET_TWIST_DEG: float = 30.0
    """Degrees of one-way rotation required to disengage the core."""

    BAYONET_LUG_W: float = 3.0
    """mm  lug circumferential width."""

    BAYONET_LUG_H: float = 0.8
    """mm  lug axial engagement depth (how much axial load the lug carries)."""

    BAYONET_CLEARANCE: float = 0.15
    """mm  lug-to-slot fit clearance (FDM print tolerance)."""

    SHEAR_PIN_D: float = 1.0
    """mm  tamper-loop shear pin diameter."""

    SHEAR_PIN_COUNT: int = 2
    """Number of shear pins per assembly."""

    # ── Key ───────────────────────────────────────────────────────────────────
    KEY_PUSH_MM: float = 0.3
    """mm  axial press required before the twist engagement begins.
    Must be at least 2× axial print tolerance or it is lost in fit variation —
    checked by checks.py."""

    # ── NFC ───────────────────────────────────────────────────────────────────
    CHIP_A_RECESS_D: float = 4.0
    """mm  chip A pocket diameter (ring-side antenna chip)."""

    CHIP_A_RECESS_T: float = 0.5
    """mm  chip A pocket depth."""

    CHIP_B_RECESS_D: float = 4.0
    """mm  chip B pocket diameter (core-side chip)."""

    CHIP_B_RECESS_T: float = 0.5
    """mm  chip B pocket depth."""

    ANTENNA_SLOT_W: float = 1.2
    """mm  slot width through the ring (slotted-ring antenna geometry, circumferential)."""

    ANTENNA_SLOT_D: float = 2.0
    """mm  slot radial depth (how far the slot penetrates the rim from the outer face).
    Controls effective antenna inductance; deeper = longer RF detour path.
    Structural gate only — electrical tuning is deferred to RF sim / test sample."""

    # ── Manufacturing tolerances ── metal vs. polymer ─────────────────────────
    M_METAL_WEB_MIN: float = 0.5
    """mm  minimum wall for metal parts (CNC Ti Gr5 / 316L)."""

    M_POLYMER_WEB_MIN: float = 1.2
    """mm  minimum wall for FDM mock-up prints (3× 0.4 mm nozzle)."""

    # ── Tactile marker ────────────────────────────────────────────────────────
    TACTILE_MARK: bool = False
    """Raised triangle on one facet (allergy / alert flag). Off by default."""

    TACTILE_H: float = 0.4
    """mm  triangle height above the facet surface (only used when TACTILE_MARK)."""

    # ── Wearable geometry ─────────────────────────────────────────────────────
    CHAIN_BALL_D: float = 2.4
    """mm  standard military ball-chain bead diameter."""

    CHAIN_NECK_D: float = 1.6
    """mm  ball-chain neck (connector) diameter; gates minimum hole size."""

    LANYARD_HOLE_D: float = 3.2
    """mm  chain / lanyard hole diameter (CHAIN_NECK_D + 1.6 mm clearance)."""

    LANYARD_HOLE_EDGE: float = 1.5
    """mm  minimum wall between lanyard hole and outer edge."""

    LANYARD_CHAMFER: float = 0.6
    """mm  chamfer on both faces of the lanyard hole (prevents chain wear)."""

    ENGRAVE_DEPTH: float = 0.15
    """mm  laser engraving depth into facet face."""

    ENGRAVE_H: float = 1.5
    """mm  engraving character height."""

    ENGRAVE_MARGIN: float = 1.0
    """mm  margin from facet edge to engraving field boundary."""

    BODY_CHAMFER: float = 0.4
    """mm  chamfer on outer perimeter edges of the back (skin-side) face."""

    FRONT_CHAMFER: float = 0.3
    """mm  chamfer on outer perimeter edges of the ring's front (open) face."""

    CORE_CHAMFER: float = 0.3
    """mm  chamfer on the front and back hex edges of the core body."""

    CHAIN_HOLE_SPACING: float = 6.0
    """mm  centre-to-centre distance between the two chain holes at the top vertex.
    Chain threads through both holes so the tag hangs flat and cannot rotate."""

    CHAIN_TAB_DEPTH: float = 4.0
    """mm  how far the chain-hole mounting tab protrudes beyond the +X vertex."""

    CHAIN_TAB_HALF_W: float = 6.0
    """mm  half-width (Y direction) of the mounting tab; full tab is 2× this."""

    PART_LINE_W: float = 0.5
    """mm  width of the circumferential parting-line groove on the ring inner bore.
    Groove marks the front edge of the core seating plane (z=RING_FACE_T). ADR-0042."""

    PART_LINE_D: float = 0.4
    """mm  depth the parting groove cuts into each flat bore wall. ADR-0042."""

    # ── Core engraving ────────────────────────────────────────────────────────
    CORE_ENGRAVE_DEPTH: float = 0.15
    """mm  laser engraving depth on core facets."""

    CORE_ENGRAVE_H: float = 1.0
    """mm  character height on core facets (tighter than ring — less axial space)."""

    CORE_ENGRAVE_MARGIN: float = 0.6
    """mm  margin from core facet edge to engraving field boundary."""

    # ── Manufacturing tolerances ──────────────────────────────────────────────
    M_NOZZLE_D: float = 0.4
    """mm  FDM nozzle diameter; gates minimum feature sizes."""

    M_CERAMIC_FIT: float = 0.05
    """mm  ceramic-to-polymer radial clearance (tighter than polymer-to-polymer)."""

    M_POLYMER_FIT: float = 0.15
    """mm  polymer-to-polymer radial fit clearance."""

    M_WALL_MIN: float = 0.8
    """mm  minimum printable wall (2 × nozzle)."""

    M_AXIAL_TOL: float = 0.15
    """mm  axial print tolerance; KEY_PUSH_MM must exceed 2× this."""

    # ── Derived quantities ────────────────────────────────────────────────────
    # These are properties so they cannot be set directly; they follow from the
    # free parameters above and form a single, traceable derivation path.

    @property
    def RING_ACROSS_FLATS(self) -> float:
        """mm  flat-to-flat = across-corners × cos(30°)."""
        return self.RING_ACROSS_CORNERS * math.cos(math.radians(30))

    @property
    def RING_INNER_ACROSS_CORNERS(self) -> float:
        """mm  inner hexagon point-to-point (= outer - 2 × rim)."""
        return self.RING_ACROSS_CORNERS - 2 * self.RING_RIM_T

    @property
    def RING_T(self) -> float:
        """mm  total axial thickness of the ring body (both faces + core cavity)."""
        return 2 * self.RING_FACE_T + self.CORE_T

    @property
    def CORE_ACROSS_CORNERS(self) -> float:
        """mm  core hex across-corners = inner ring - bilateral ceramic fit clearance."""
        return self.RING_INNER_ACROSS_CORNERS - 2 * self.M_CERAMIC_FIT

    @property
    def BAYONET_PITCH_DEG(self) -> float:
        """degrees  angular spacing of lugs = 360° / lug count."""
        return 360.0 / self.BAYONET_LUGS

    @property
    def BAYONET_LUG_ARC_MM(self) -> float:
        """mm  lug travel arc at the core inner radius during BAYONET_TWIST_DEG.
        Must exceed BAYONET_LUG_W for the lug to fully clear the slot."""
        return self.BAYONET_TWIST_DEG * math.pi * self.CORE_ACROSS_CORNERS / 360

    @property
    def FACET_SIDE(self) -> float:
        """mm  side length of the outer hexagon.
        For a regular hexagon, side = circumradius = across_corners / 2."""
        return self.RING_ACROSS_CORNERS / 2

    @property
    def ANTENNA_SLOT_R(self) -> float:
        """mm  radial centre of the antenna slot (measured from tag centre).
        Slot runs from the outer surface inward by ANTENNA_SLOT_D."""
        return self.RING_ACROSS_CORNERS / 2 - self.ANTENNA_SLOT_D / 2

    @property
    def ANTENNA_SLOT_RADIAL_WEB(self) -> float:
        """mm  remaining wall between slot bottom and inner cavity wall.
        Must exceed M_METAL_WEB_MIN for structural integrity."""
        return self.RING_RIM_T - self.ANTENNA_SLOT_D

    @property
    def ANTENNA_SLOT_LATERAL_WEB(self) -> float:
        """mm  wall from slot edge to nearest hex corner (each side).
        Must exceed M_METAL_WEB_MIN to keep the corner intact."""
        return (self.FACET_SIDE - self.ANTENNA_SLOT_W) / 2


#: Default parameters — the field-grade Hexa tag.
P = HexaParams()

#: Engraving field label for each of the 6 rim facets (0 = back, clockwise).
#: Facet 0 faces away from the body; facet 3 faces the skin.
FACET_LABELS: dict[int, str] = {
    0: "SURNAME",
    1: "GIVEN NAME",
    2: "ID-A",      # first 8 chars of 16-char enrollment short-ID
    3: "ID-B",      # last 8 chars of 16-char enrollment short-ID
    4: "UNIT",
    5: "NFC",
}

#: Example engraved text for renders and PoC demonstrations.
#: Shows where data would appear on each facet. Not used in production.
FACET_EXAMPLES: dict[int, str] = {
    0: "DOE",
    1: "JOHN",
    2: "A1B2C3D4",
    3: "E5F6A7B8",
    4: "1 INF BN",
    5: "NFC",
}
