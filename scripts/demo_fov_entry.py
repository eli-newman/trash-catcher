#!/usr/bin/env python3
"""
Demo: Object entering FOV mid-flight.

Simulates trash thrown from outside the camera's field of view
that enters mid-flight. Tests whether predictor can still accurately
predict landing with only partial trajectory data.
"""

import sys
import numpy as np

# Add parent directory to path
sys.path.insert(0, '.')

from src.simulator import generate_throw, get_visible_points
from src.predictor import predict_landing, calculate_prediction_error

def main():
    print("="*70)
    print("DEMO: Object Entering FOV Mid-Flight")
    print("="*70)
    print("\nScenario: Trash thrown from the side, arcing through camera view")
    print("Challenge: Predictor only sees partial trajectory\n")

    # Generate throw that starts outside FOV
    np.random.seed(789)

    throw = generate_throw(
        start_position=(2.5, 0.0, 1.5),  # 2.5m to side, outside FOV
        start_velocity=(-3.0, 0.0, 3.0),  # fast toward center, upward arc
        add_measurement_noise=True,      # Add realistic noise
        dropout_probability=0.05          # Occasional missed frames
    )

    # Analyze observations
    all_points = throw.observed_points
    visible_points = get_visible_points(throw)

    first_visible_time = visible_points[0].time_sec if visible_points else None

    print("Trajectory Details:")
    print(f"  Start position: ({throw.start_position[0]:.2f}, {throw.start_position[1]:.2f}, {throw.start_position[2]:.2f}) m")
    print(f"  Start velocity: ({throw.start_velocity[0]:.2f}, {throw.start_velocity[1]:.2f}, {throw.start_velocity[2]:.2f}) m/s")
    print(f"  Actual landing: ({throw.actual_landing[0]:.2f}, {throw.actual_landing[1]:.2f}) m")
    print(f"  Flight time: {throw.actual_flight_time:.3f} s")

    print(f"\nCamera Observations:")
    print(f"  Total trajectory frames: {len(all_points)}")
    print(f"  Visible frames: {len(visible_points)}")
    print(f"  Frames missed (outside FOV): {len(all_points) - len(visible_points)}")
    print(f"  Object enters FOV at: t={first_visible_time:.3f}s")
    print(f"  Trajectory coverage: {len(visible_points)/len(all_points)*100:.1f}%")

    # Make prediction from visible data only
    if len(visible_points) >= 5:
        prediction = predict_landing(visible_points)

        if prediction:
            error = calculate_prediction_error(prediction, throw.actual_landing)

            print(f"\nPrediction Results:")
            print(f"  Predicted landing: ({prediction.landing_x:.2f}, {prediction.landing_y:.2f}) m")
            print(f"  Time to landing: {prediction.time_to_landing:.3f} s")
            print(f"  Confidence: {prediction.confidence:.2f}")
            print(f"  Frames used: {prediction.frames_used}")

            print(f"\nAccuracy:")
            print(f"  Prediction error: {error*100:.1f} cm")

            if error < 0.10:
                print(f"  Status: ✅ Excellent (< 10cm)")
            elif error < 0.20:
                print(f"  Status: ✅ Good (< 20cm)")
            elif error < 0.30:
                print(f"  Status: ⚠️  Acceptable (< 30cm)")
            else:
                print(f"  Status: ❌ Poor (> 30cm)")

            print(f"\n" + "="*70)
            print("CONCLUSION:")
            print("="*70)
            print(f"Even with only {len(visible_points)/len(all_points)*100:.0f}% trajectory visibility,")
            print(f"the predictor achieved {error*100:.1f}cm accuracy!")
            print(f"\nThis proves the system can handle real-world scenarios where")
            print(f"trash is thrown from outside the camera's initial field of view.")

        else:
            print("\n❌ Could not generate prediction (insufficient data)")
    else:
        print(f"\n❌ Not enough visible frames ({len(visible_points)} < 5)")

if __name__ == "__main__":
    main()
