"""Sanity checks for HexaParams: all derived quantities must be correct
and all geometric checks must pass on the default parameter set."""

import math
import pytest
from dataclasses import replace

from hexa.params import HexaParams, P
from hexa.checks import (
    CheckError,
    check_all,
    check_core_fits,
    check_key_push,
    check_lanyard_hole,
    check_lug_travel,
    check_wall_min,
)


class TestDerivedQuantities:
    def test_across_flats(self):
        expected = P.RING_ACROSS_CORNERS * math.cos(math.radians(30))
        assert abs(P.RING_ACROSS_FLATS - expected) < 1e-9

    def test_ring_inner_across_corners(self):
        expected = P.RING_ACROSS_CORNERS - 2 * P.RING_RIM_T
        assert abs(P.RING_INNER_ACROSS_CORNERS - expected) < 1e-9

    def test_ring_t(self):
        expected = 2 * P.RING_FACE_T + P.CORE_T
        assert abs(P.RING_T - expected) < 1e-9

    def test_core_across_corners(self):
        expected = P.RING_INNER_ACROSS_CORNERS - 2 * P.M_CERAMIC_FIT
        assert abs(P.CORE_ACROSS_CORNERS - expected) < 1e-9

    def test_bayonet_pitch_three_lugs(self):
        assert abs(P.BAYONET_PITCH_DEG - 120.0) < 1e-9

    def test_lug_arc_positive(self):
        assert P.BAYONET_LUG_ARC_MM > 0

    def test_antenna_slot_r_positive(self):
        assert P.ANTENNA_SLOT_R > 0


class TestDefaultChecks:
    def test_all_pass_on_defaults(self):
        check_all(P)

    def test_key_push_too_small_raises(self):
        tiny = replace(P, KEY_PUSH_MM=0.0)
        with pytest.raises(CheckError, match="KEY_PUSH_MM"):
            check_key_push(tiny)

    def test_lug_arc_too_small_raises(self):
        # Make lug width larger than any possible arc
        fat = replace(P, BAYONET_LUG_W=50.0)
        with pytest.raises(CheckError, match="BAYONET_LUG_ARC"):
            check_lug_travel(fat)

    def test_wall_min_rim_raises(self):
        thin_rim = replace(P, RING_RIM_T=0.3)
        with pytest.raises(CheckError, match="rim"):
            check_wall_min(thin_rim)

    def test_wall_min_face_raises(self):
        thin_face = replace(P, RING_FACE_T=0.3)
        with pytest.raises(CheckError, match="face"):
            check_wall_min(thin_face)

    def test_lanyard_hole_too_large_raises(self):
        # 38mm hole: outer_r=20, hole_r=19, wall=1 < LANYARD_HOLE_EDGE=1.5
        huge_hole = replace(P, LANYARD_HOLE_D=38.0)
        with pytest.raises(CheckError, match="[Ll]anyard"):
            check_lanyard_hole(huge_hole)

    def test_core_positive(self):
        # Sanity: default core is positive and fits
        assert P.CORE_ACROSS_CORNERS > 0
        assert P.CORE_ACROSS_CORNERS < P.RING_INNER_ACROSS_CORNERS
