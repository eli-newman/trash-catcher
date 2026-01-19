"""Tests for trajectory simulator."""

import numpy as np
import pytest
from src.simulator import (
    calculate_landing,
    is_point_in_fov,
    generate_throw,
    get_visible_points
)


def test_calculate_landing_straight_drop():
    """Object dropped straight down should land at same x,y."""
    start_pos = (1.0, 2.0, 3.0)  # 3m high
    start_vel = (0.0, 0.0, 0.0)  # no velocity
    
    landing, time = calculate_landing(start_pos, start_vel, catch_height=0.3)
    
    assert abs(landing[0] - 1.0) < 0.01  # lands at same x
    assert abs(landing[1] - 2.0) < 0.01  # lands at same y
    assert time > 0  # takes positive time


def test_calculate_landing_with_horizontal_velocity():
    """Object with horizontal velocity should land offset."""
    start_pos = (0.0, 0.0, 3.0)
    start_vel = (1.0, 0.0, 0.0)  # 1 m/s in x direction
    
    landing, time = calculate_landing(start_pos, start_vel, catch_height=0.3)
    
    # Should land in positive x direction
    assert landing[0] > 0
    # Expected: x = vx * t
    expected_x = 1.0 * time
    assert abs(landing[0] - expected_x) < 0.01


def test_is_point_in_fov_directly_above():
    """Point directly above camera should be in FOV."""
    assert is_point_in_fov((0.0, 0.0, 2.0)) == True


def test_is_point_in_fov_too_far():
    """Point beyond max range should be out of FOV."""
    assert is_point_in_fov((0.0, 0.0, 10.0)) == False  # 10m > 4m max


def test_is_point_in_fov_below_camera():
    """Point below camera should be out of FOV."""
    assert is_point_in_fov((0.0, 0.0, -1.0)) == False


def test_is_point_in_fov_at_edge():
    """Point at edge of FOV cone."""
    # At 2m height, with 70 degree FOV, max horizontal distance is:
    # tan(35 degrees) * 2m = ~1.4m
    assert is_point_in_fov((1.0, 0.0, 2.0)) == True   # inside
    assert is_point_in_fov((2.0, 0.0, 2.0)) == False  # outside


def test_generate_throw_has_points():
    """Generated throw should have observed points."""
    throw = generate_throw()
    
    assert len(throw.observed_points) > 0
    assert throw.actual_flight_time > 0


def test_generate_throw_visible_points():
    """Should have some visible points for typical throw."""
    throw = generate_throw(
        start_position=(0.0, 0.0, 2.5),
        start_velocity=(0.0, 0.0, 0.0)
    )
    
    visible = get_visible_points(throw)
    assert len(visible) > 0


def test_generate_throw_deterministic():
    """Same seed should give same throw."""
    np.random.seed(42)
    throw1 = generate_throw()
    
    np.random.seed(42)
    throw2 = generate_throw()
    
    assert throw1.actual_landing == throw2.actual_landing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
