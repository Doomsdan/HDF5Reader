import numpy as np
import pytest

import avrwind


def test_angle_component_roundtrip_for_wind_scalar():
    u, v = avrwind.angle2component(90, 1)

    assert u == pytest.approx(-1.0)
    assert v == pytest.approx(0.0, abs=1e-12)

    angle, norm = avrwind.component2angle(u, v)

    assert angle == pytest.approx(90.0)
    assert norm == pytest.approx(1.0)


def test_angle_component_roundtrip_for_non_wind_vectors():
    angles = np.array([0.0, 90.0, 180.0, 270.0])
    speeds = np.array([1.0, 2.0, 3.0, 4.0])

    u, v = avrwind.angle2component(angles, speeds, wind=False)
    restored_angles, restored_speeds = avrwind.component2angle(u, v, wind=False)

    np.testing.assert_allclose(restored_angles, angles)
    np.testing.assert_allclose(restored_speeds, speeds)


def test_avrwind_vec_averages_components_and_speeds():
    result = avrwind.avrwind_vec([1, 3], [2, 4], verbose=False)

    assert result[0] == pytest.approx(2.0)
    assert result[1] == pytest.approx(3.0)
    assert result[3] == pytest.approx(np.sqrt(13.0))
    assert result[4] == pytest.approx((np.sqrt(5.0) + 5.0) / 2.0)


def test_avrwind_vec_returns_none_for_mismatched_lengths():
    assert avrwind.avrwind_vec([1], [1, 2], verbose=False) is None
