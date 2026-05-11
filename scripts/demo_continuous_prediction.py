"""
Demonstrate continuous prediction refinement.

Shows how predictions improve as more frames arrive, and how to use
the ContinuousPredictor class for real-time hardware applications.
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from src.simulator import generate_throw, TrajectoryPoint
from src.predictor import ContinuousPredictor, calculate_prediction_error
from src.logging_config import setup_logging
from src.config_validator import validate_config
import config


def demo_continuous_prediction():
    """
    Demonstrate continuous prediction with live updates.

    This mimics how the hardware will work:
    1. Camera sends frames one at a time
    2. Each frame updates the prediction
    3. Prediction improves as more data arrives
    4. Servo only moves when confidence is high enough
    """
    # Setup
    setup_logging(level="INFO")
    validate_config()

    print("\n" + "="*70)
    print("CONTINUOUS PREDICTION DEMO")
    print("="*70)
    print("\nSimulating real-time camera feed...")
    print("Each frame updates the prediction. Watch confidence improve!\n")

    # Generate a throw
    np.random.seed(42)
    throw = generate_throw(
        start_position=(1.0, 0.5, 2.5),
        start_velocity=(-0.5, 0.3, 1.0),
        add_measurement_noise=True,
        dropout_probability=0.05
    )

    print(f"Ground Truth:")
    print(f"  Actual landing: ({throw.actual_landing[0]:.3f}, {throw.actual_landing[1]:.3f})")
    print(f"  Flight time: {throw.actual_flight_time:.3f}s")
    print(f"  Total frames: {len(throw.observed_points)}\n")

    # Create continuous predictor
    predictor = ContinuousPredictor()

    # Process frames one by one (like camera would)
    prediction_history = []
    first_prediction_frame = None

    for frame_num, frame in enumerate(throw.observed_points):
        # Add frame to predictor
        prediction = predictor.add_frame(frame)

        # If we have a prediction, check if it's actionable
        if prediction:
            if first_prediction_frame is None:
                first_prediction_frame = frame_num
                time_to_first = frame.time_sec
                print(f"✓ First prediction at frame {frame_num} ({time_to_first:.3f}s)")
                print(f"  Needed {config.MIN_FRAMES_FOR_PREDICTION} frames @ {config.CAMERA_FPS} FPS\n")

            error = calculate_prediction_error(prediction, throw.actual_landing)
            prediction_history.append((frame_num, prediction, error))

            # Show key predictions
            if frame_num == first_prediction_frame:
                print(f"Frame {frame_num:2d} (FIRST):")
            elif frame_num == first_prediction_frame + 5:
                print(f"Frame {frame_num:2d} (+5 frames):")
            elif frame_num == first_prediction_frame + 10:
                print(f"Frame {frame_num:2d} (+10 frames):")
            elif frame_num == len(throw.observed_points) - 1:
                print(f"Frame {frame_num:2d} (LAST):")
            else:
                continue  # Skip intermediate frames for brevity

            print(f"  Position: ({prediction.landing_x:.3f}, {prediction.landing_y:.3f})")
            print(f"  Error: {error*100:.1f}cm")
            print(f"  Confidence: {prediction.confidence:.3f}")
            print(f"  Frames used: {prediction.frames_used}")
            print(f"  Time to landing: {prediction.time_to_landing:.3f}s")

            # Actionable check (would trigger servo in hardware)
            if prediction.is_actionable(min_confidence=0.6):
                print(f"  → ACTIONABLE! Servo would move to this position")
            else:
                print(f"  → Not confident enough, wait for more frames")
            print()

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)

    if prediction_history:
        errors = [e for _, _, e in prediction_history]
        confidences = [p.confidence for _, p, _ in prediction_history]

        print(f"\nPrediction convergence:")
        print(f"  First prediction error: {errors[0]*100:.1f}cm (confidence={confidences[0]:.3f})")
        print(f"  Final prediction error: {errors[-1]*100:.1f}cm (confidence={confidences[-1]:.3f})")
        print(f"  Improvement: {(errors[0]-errors[-1])*100:+.1f}cm")
        print(f"\n  Mean error: {np.mean(errors)*100:.1f}cm")
        print(f"  Min error: {np.min(errors)*100:.1f}cm")

        # Count actionable predictions
        actionable_count = sum(1 for _, p, _ in prediction_history if p.is_actionable(0.6))
        print(f"\n  Actionable predictions: {actionable_count}/{len(prediction_history)} "
              f"({100*actionable_count/len(prediction_history):.0f}%)")

        print(f"\nKey insight:")
        print(f"  • Predictions improve continuously as more frames arrive")
        print(f"  • Confidence increases with more data")
        print(f"  • Servo waits for high-confidence prediction before moving")
        print(f"  • This ensures accurate catches even with limited early data")


def demo_hardware_pattern():
    """
    Show the recommended pattern for hardware integration.
    """
    print("\n\n" + "="*70)
    print("HARDWARE INTEGRATION PATTERN")
    print("="*70)
    print("""
This is how you'll use ContinuousPredictor with real hardware:

```python
from src.predictor import ContinuousPredictor
from src.logging_config import setup_hardware_logging
from src.config_validator import validate_config

# Startup
setup_hardware_logging(log_dir="./logs")
validate_config()

# Create predictor
predictor = ContinuousPredictor()

# Main loop (runs at camera FPS, e.g., 30 Hz)
while True:
    # 1. Read frame from ToF camera
    frame = camera.read_frame()  # Returns TrajectoryPoint

    # 2. Update prediction
    prediction = predictor.add_frame(frame)

    # 3. Act on high-confidence predictions
    if prediction and prediction.is_actionable(min_confidence=0.7):
        # Move servo to predicted position
        servo.move_to_position(
            x=prediction.landing_x,
            y=prediction.landing_y,
            time_to_arrival=prediction.time_to_landing
        )

        # Log for debugging
        logger.info(f"Servo commanded: ({prediction.landing_x:.3f}, "
                   f"{prediction.landing_y:.3f}), conf={prediction.confidence:.2f}")

    # 4. Reset after catch or miss
    if object_caught_or_missed():
        predictor.reset()
```

Key advantages of this pattern:
- Thread-safe: ContinuousPredictor has internal locking
- Automatic validation: Bad frames are rejected silently
- Latency tracking: Logs warn if prediction takes >30ms
- Confidence gating: Prevents servo from moving on bad predictions
- Continuous refinement: Each frame improves accuracy
""")


if __name__ == "__main__":
    demo_continuous_prediction()
    demo_hardware_pattern()
