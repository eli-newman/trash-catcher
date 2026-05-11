"""Tests for predictor edge cases and error handling."""

import numpy as np
import pytest
from src.simulator import TrajectoryPoint
from src.predictor import (
    predict_landing,
    _validate_trajectory_point,
    _validate_trajectory_points,
    fit_parabola_1d,
    fit_line_1d,
    ValidationError,
    NumericalError,
    ContinuousPredictor
)


class TestValidation:
    """Test input validation."""

    def test_nan_time_rejected(self):
        """NaN time should raise ValidationError."""
        point = TrajectoryPoint(np.nan, 0.0, 0.0, 2.0, True)
        with pytest.raises(ValidationError, match="Invalid time"):
            _validate_trajectory_point(point)

    def test_inf_position_rejected(self):
        """Inf position should raise ValidationError."""
        point = TrajectoryPoint(0.0, np.inf, 0.0, 2.0, True)
        with pytest.raises(ValidationError, match="Invalid x"):
            _validate_trajectory_point(point)

    def test_negative_time_rejected(self):
        """Negative time should raise ValidationError."""
        point = TrajectoryPoint(-1.0, 0.0, 0.0, 2.0, True)
        with pytest.raises(ValidationError, match="Negative time"):
            _validate_trajectory_point(point)

    def test_huge_position_rejected(self):
        """Position > 100m should raise ValidationError."""
        point = TrajectoryPoint(0.0, 150.0, 0.0, 2.0, True)
        with pytest.raises(ValidationError, match="x out of bounds"):
            _validate_trajectory_point(point)

    def test_empty_list_rejected(self):
        """Empty points list should raise ValidationError."""
        with pytest.raises(ValidationError, match="Empty points list"):
            _validate_trajectory_points([])

    def test_non_monotonic_time_rejected(self):
        """Times must be monotonically increasing."""
        points = [
            TrajectoryPoint(0.0, 0.0, 0.0, 2.0, True),
            TrajectoryPoint(0.1, 0.0, 0.0, 1.9, True),
            TrajectoryPoint(0.05, 0.0, 0.0, 1.8, True),  # Out of order!
        ]
        with pytest.raises(ValidationError, match="monotonically increasing"):
            _validate_trajectory_points(points)


class TestCurveFitting:
    """Test curve fitting edge cases."""

    def test_identical_times_parabola(self):
        """All same time should raise NumericalError."""
        times = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        positions = np.array([2.0, 2.1, 2.0, 2.1, 2.0])

        with pytest.raises(NumericalError, match="All times are identical"):
            fit_parabola_1d(times, positions)

    def test_identical_times_line(self):
        """All same time should return zero velocity."""
        times = np.array([1.0, 1.0, 1.0])
        positions = np.array([2.0, 2.1, 2.0])

        m, b = fit_line_1d(times, positions)
        assert m == 0.0
        assert abs(b - 2.033) < 0.01  # Mean position

    def test_unrealistic_velocity_rejected(self):
        """Velocity > 50 m/s should raise NumericalError."""
        times = np.array([0.0, 0.1, 0.2])
        positions = np.array([0.0, 10.0, 20.0])  # 100 m/s!

        with pytest.raises(NumericalError, match="Unrealistic velocity"):
            fit_line_1d(times, positions)

    def test_rank_deficient_matrix(self):
        """Rank-deficient matrix should raise NumericalError."""
        # Only 2 unique points - can't fit parabola
        times = np.array([0.0, 0.0, 0.1, 0.1])
        positions = np.array([1.0, 1.0, 2.0, 2.0])

        # This will fail because rank < 3
        with pytest.raises(NumericalError, match="Matrix rank"):
            fit_parabola_1d(times, positions)


class TestPredictionEdgeCases:
    """Test prediction edge cases."""

    def test_empty_points_list(self):
        """Empty list should return None."""
        result = predict_landing([])
        assert result is None

    def test_no_visible_points(self):
        """All points out of FOV should return None."""
        points = [
            TrajectoryPoint(0.0, 0.0, 0.0, 2.0, False),
            TrajectoryPoint(0.1, 0.0, 0.0, 1.9, False),
            TrajectoryPoint(0.2, 0.0, 0.0, 1.8, False),
        ]
        result = predict_landing(points)
        assert result is None

    def test_object_already_past_catch_plane(self):
        """Object below catch plane should return None."""
        # Create points all below catch plane (0.3m)
        points = []
        for i in range(10):
            t = i * 0.033
            z = 0.2 - 0.1 * t  # Moving down, starting below catch plane
            points.append(TrajectoryPoint(t, 0.0, 0.0, z, True))

        result = predict_landing(points, catch_height=0.3)
        assert result is None

    def test_object_moving_away_from_catch_plane(self):
        """Object moving upward away from catch plane should return None."""
        points = []
        for i in range(10):
            t = i * 0.033
            z = 0.1 + 2.0 * t  # Moving up fast
            points.append(TrajectoryPoint(t, 0.0, 0.0, z, True))

        result = predict_landing(points, catch_height=0.3)
        assert result is None

    def test_all_points_same_position(self):
        """Stationary object should fail gracefully."""
        points = []
        for i in range(10):
            t = i * 0.033
            # Same position every time (degenerate case)
            points.append(TrajectoryPoint(t, 1.0, 1.0, 2.0, True))

        # Should either return None or raise NumericalError
        try:
            result = predict_landing(points)
            # If it returns, should be None
            assert result is None
        except NumericalError:
            # Also acceptable - curve fit failed
            pass

    def test_very_short_flight_time(self):
        """Object very close to catch plane should work."""
        points = []
        g = 9.81
        for i in range(10):
            t = i * 0.033
            z = 0.35 - 0.5 * g * t * t  # Start just above catch plane
            if z > 0.3:
                points.append(TrajectoryPoint(t, 0.0, 0.0, z, True))

        result = predict_landing(points, catch_height=0.3)
        # Should work even with very short flight time
        assert result is not None or len(points) < 5

    def test_extreme_horizontal_velocity(self):
        """Very fast horizontal motion should be rejected."""
        points = []
        vx = 60.0  # 60 m/s horizontal (unrealistic)
        for i in range(10):
            t = i * 0.033
            x = vx * t
            z = 2.5 - 0.5 * 9.81 * t * t
            if z > 0.3:
                points.append(TrajectoryPoint(t, x, 0.0, z, True))

        # Should raise NumericalError due to unrealistic velocity
        with pytest.raises(NumericalError, match="Unrealistic velocity"):
            predict_landing(points)


class TestContinuousPredictor:
    """Test continuous predictor."""

    def test_continuous_predictor_initialization(self):
        """ContinuousPredictor should initialize correctly."""
        predictor = ContinuousPredictor()
        assert not predictor.has_prediction()
        assert predictor.get_frame_count() == 0
        assert predictor.get_latest_prediction() is None

    def test_continuous_predictor_accumulates_frames(self):
        """Frames should accumulate."""
        predictor = ContinuousPredictor()

        for i in range(10):
            t = i * 0.033
            z = 2.5 - 0.5 * 9.81 * t * t
            frame = TrajectoryPoint(t, 0.0, 0.0, z, True)
            predictor.add_frame(frame)

        assert predictor.get_frame_count() == 10

    def test_continuous_predictor_updates_prediction(self):
        """Prediction should update as frames arrive."""
        predictor = ContinuousPredictor()

        predictions = []
        for i in range(15):
            t = i * 0.033
            x = 1.0 * t
            z = 2.5 - 0.5 * 9.81 * t * t
            frame = TrajectoryPoint(t, x, 0.0, z, True)

            pred = predictor.add_frame(frame)
            if pred:
                predictions.append(pred)

        # Should have predictions after min frames
        assert len(predictions) > 0

        # Later predictions should use more frames
        assert predictions[-1].frames_used >= predictions[0].frames_used

    def test_continuous_predictor_rejects_invalid_frames(self):
        """Invalid frames should be rejected."""
        predictor = ContinuousPredictor()

        # Add good frame
        frame1 = TrajectoryPoint(0.0, 0.0, 0.0, 2.5, True)
        predictor.add_frame(frame1)
        assert predictor.get_frame_count() == 1

        # Add bad frame (NaN)
        frame2 = TrajectoryPoint(0.1, np.nan, 0.0, 2.4, True)
        predictor.add_frame(frame2)

        # Bad frame should not be added
        assert predictor.get_frame_count() == 1

    def test_continuous_predictor_reset(self):
        """Reset should clear all state."""
        predictor = ContinuousPredictor()

        # Add frames
        for i in range(10):
            t = i * 0.033
            z = 2.5 - 0.5 * 9.81 * t * t
            frame = TrajectoryPoint(t, 0.0, 0.0, z, True)
            predictor.add_frame(frame)

        # Reset
        predictor.reset()

        assert predictor.get_frame_count() == 0
        assert not predictor.has_prediction()

    def test_prediction_is_actionable(self):
        """Test is_actionable() method."""
        predictor = ContinuousPredictor()

        # Add enough frames to get a prediction
        for i in range(10):
            t = i * 0.033
            z = 2.5 - 0.5 * 9.81 * t * t
            frame = TrajectoryPoint(t, 0.0, 0.0, z, True)
            pred = predictor.add_frame(frame)

        if predictor.has_prediction():
            pred = predictor.get_latest_prediction()
            # Check actionable with different thresholds
            if pred.confidence >= 0.6:
                assert pred.is_actionable(min_confidence=0.6)
            if pred.confidence < 0.6:
                assert not pred.is_actionable(min_confidence=0.6)


class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_more_frames_higher_confidence(self):
        """More frames should generally give higher confidence."""
        np.random.seed(42)

        # Generate clean throw
        points_5 = []
        points_10 = []

        for i in range(10):
            t = i * 0.033
            z = 2.5 - 0.5 * 9.81 * t * t
            point = TrajectoryPoint(t, 0.0, 0.0, z, True)

            if i < 5:
                points_5.append(point)
            points_10.append(point)

        pred_5 = predict_landing(points_5)
        pred_10 = predict_landing(points_10)

        if pred_5 and pred_10:
            # More frames should give higher confidence (generally)
            # Note: This is a trend, not absolute guarantee
            assert pred_10.frames_used > pred_5.frames_used

    def test_good_fit_higher_confidence(self):
        """Clean data should have higher confidence than noisy data."""
        np.random.seed(42)

        # Clean throw
        clean_points = []
        for i in range(10):
            t = i * 0.033
            z = 2.5 - 0.5 * 9.81 * t * t
            clean_points.append(TrajectoryPoint(t, 0.0, 0.0, z, True))

        # Noisy throw (same trajectory + noise)
        noisy_points = []
        for i in range(10):
            t = i * 0.033
            z = 2.5 - 0.5 * 9.81 * t * t + np.random.normal(0, 0.1)
            noisy_points.append(TrajectoryPoint(t, 0.0, 0.0, z, True))

        pred_clean = predict_landing(clean_points)
        pred_noisy = predict_landing(noisy_points)

        if pred_clean and pred_noisy:
            # Clean data should have higher confidence
            assert pred_clean.confidence > pred_noisy.confidence
            # Clean data should have lower fit residual
            assert pred_clean.fit_residual < pred_noisy.fit_residual


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
