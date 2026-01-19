"""Tests for landing predictor."""

import numpy as np
import pytest
from src.simulator import generate_throw, get_visible_points, TrajectoryPoint
from src.predictor import (
    predict_landing,
    calculate_prediction_error,
    fit_parabola_1d,
    fit_line_1d
)


def test_fit_parabola_perfect_data():
    """Parabola fit should recover exact coefficients from perfect data."""
    times = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    # z = -4.9*t^2 + 2*t + 3 (gravity with upward velocity)
    a_true, b_true, c_true = -4.9, 2.0, 3.0
    positions = a_true * times**2 + b_true * times + c_true
    
    a, b, c = fit_parabola_1d(times, positions)
    
    assert abs(a - a_true) < 0.01
    assert abs(b - b_true) < 0.01
    assert abs(c - c_true) < 0.01


def test_fit_line_perfect_data():
    """Line fit should recover exact coefficients from perfect data."""
    times = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    m_true, b_true = 1.5, 0.5
    positions = m_true * times + b_true
    
    m, b = fit_line_1d(times, positions)
    
    assert abs(m - m_true) < 0.01
    assert abs(b - b_true) < 0.01


def test_predict_landing_not_enough_frames():
    """Should return None with too few frames."""
    points = [
        TrajectoryPoint(0.0, 0.0, 0.0, 2.0, True),
        TrajectoryPoint(0.033, 0.0, 0.0, 1.9, True),
    ]
    
    prediction = predict_landing(points, min_frames=5)
    assert prediction is None


def test_predict_landing_straight_drop():
    """Straight drop should predict landing at same x,y."""
    # Create points for straight drop from 2.5m
    points = []
    g = 9.81
    for i in range(10):
        t = i * 0.033  # 30 fps
        z = 2.5 - 0.5 * g * t * t
        if z > 0.3:  # above catch plane
            points.append(TrajectoryPoint(t, 0.0, 0.0, z, True))
    
    prediction = predict_landing(points, catch_height=0.3)
    
    assert prediction is not None
    assert abs(prediction.landing_x) < 0.1  # should land near x=0
    assert abs(prediction.landing_y) < 0.1  # should land near y=0


def test_predict_landing_with_horizontal_velocity():
    """Should predict offset landing with horizontal velocity."""
    points = []
    g = 9.81
    vx = 2.0  # 2 m/s horizontal
    
    for i in range(10):
        t = i * 0.033
        x = vx * t
        z = 2.5 - 0.5 * g * t * t
        if z > 0.3:
            points.append(TrajectoryPoint(t, x, 0.0, z, True))
    
    prediction = predict_landing(points, catch_height=0.3)
    
    assert prediction is not None
    assert prediction.landing_x > 0.5  # should land in positive x


def test_prediction_accuracy_on_simulated_throw():
    """Test prediction accuracy on full simulated throw."""
    np.random.seed(123)
    
    # Generate throw without noise for clean test
    throw = generate_throw(
        start_position=(0.0, 0.0, 2.5),
        start_velocity=(1.0, 0.5, 1.0),
        add_measurement_noise=False,
        dropout_probability=0.0
    )
    
    visible = get_visible_points(throw)
    
    # Use first 10 frames to predict
    prediction = predict_landing(visible[:10])
    
    assert prediction is not None
    
    error = calculate_prediction_error(prediction, throw.actual_landing)
    
    # Should be very accurate without noise
    assert error < 0.05  # within 5cm


def test_prediction_accuracy_with_noise():
    """Test prediction still works with realistic noise."""
    np.random.seed(456)

    throw = generate_throw(
        start_position=(0.0, 0.0, 2.5),
        start_velocity=(1.0, 0.5, 0.0),
        add_measurement_noise=True,
        dropout_probability=0.0
    )

    visible = get_visible_points(throw)

    if len(visible) >= 5:
        prediction = predict_landing(visible)

        if prediction is not None:
            error = calculate_prediction_error(prediction, throw.actual_landing)
            # Allow more error with noise
            assert error < 0.3  # within 30cm


def test_object_entering_fov_mid_flight():
    """Test prediction when object starts outside FOV and enters mid-flight."""
    np.random.seed(789)

    # Start object outside FOV, throw with upward arc that passes through FOV
    # Camera FOV: 70° (35° half-angle), at z=1.5m max radius ≈ 1.05m
    # Start at 2.5m horizontal offset (outside FOV), throw toward center with upward velocity
    # This simulates trash thrown from the side that arcs through camera view
    throw = generate_throw(
        start_position=(2.5, 0.0, 1.5),  # 2.5m to side, outside FOV
        start_velocity=(-3.0, 0.0, 3.0),  # fast toward center, upward arc
        add_measurement_noise=False,
        dropout_probability=0.0
    )

    # Verify object starts outside FOV
    first_point = throw.observed_points[0]
    assert not first_point.in_fov, "Object should start outside FOV"

    # Verify object enters FOV at some point
    visible = get_visible_points(throw)
    assert len(visible) > 0, "Object should enter FOV during flight"

    # First visible point should not be the first observation
    first_visible_time = visible[0].time_sec
    assert first_visible_time > 0, "Object should have observations before entering FOV"

    print(f"\n  Object enters FOV at t={first_visible_time:.3f}s (frame {len(throw.observed_points) - len(visible)} of {len(throw.observed_points)})")
    print(f"  Visible frames: {len(visible)}/{len(throw.observed_points)}")

    # Predict landing using only visible points
    assert len(visible) >= 5, "Should have enough visible frames for prediction"

    prediction = predict_landing(visible)
    assert prediction is not None, "Should be able to predict with visible points"

    error = calculate_prediction_error(prediction, throw.actual_landing)
    print(f"  Prediction error: {error*100:.1f}cm")
    print(f"  Actual landing: ({throw.actual_landing[0]:.2f}, {throw.actual_landing[1]:.2f})")
    print(f"  Predicted landing: ({prediction.landing_x:.2f}, {prediction.landing_y:.2f})")

    # Should still be reasonably accurate even though we missed the start
    # Allow slightly more error since we have less trajectory data
    assert error < 0.15, f"Prediction error {error*100:.1f}cm should be < 15cm"

    # Check that prediction uses only visible frames
    assert prediction.frames_used == len(visible)
    assert prediction.frames_used < len(throw.observed_points)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
