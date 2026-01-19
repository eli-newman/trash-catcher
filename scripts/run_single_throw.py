"""
Run a single throw simulation and visualize.
Usage: python scripts/run_single_throw.py [seed]
"""

import sys
import numpy as np
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.insert(0, '.')

from src.simulator import generate_throw, get_visible_points
from src.predictor import predict_landing, calculate_prediction_error
from src.visualizer import visualize_throw


def main():
    # Set seed for reproducibility (change for different throws)
    seed = 42
    if len(sys.argv) > 1:
        seed = int(sys.argv[1])
    
    np.random.seed(seed)
    print(f"Running simulation with seed={seed}")
    
    # Generate throw
    throw = generate_throw(
        add_measurement_noise=True,
        dropout_probability=0.05
    )
    
    print(f"\nThrow details:")
    print(f"  Start position: ({throw.start_position[0]:.2f}, {throw.start_position[1]:.2f}, {throw.start_position[2]:.2f}) m")
    print(f"  Start velocity: ({throw.start_velocity[0]:.2f}, {throw.start_velocity[1]:.2f}, {throw.start_velocity[2]:.2f}) m/s")
    print(f"  Flight time: {throw.actual_flight_time:.3f} s")
    print(f"  Landing position: ({throw.actual_landing[0]:.2f}, {throw.actual_landing[1]:.2f}) m")
    
    # Get visible points
    visible = get_visible_points(throw)
    print(f"\nCamera observations:")
    print(f"  Total frames: {len(throw.observed_points)}")
    print(f"  Visible frames: {len(visible)}")
    
    if len(visible) < 5:
        print("\nNot enough visible frames for prediction!")
        return
    
    # Make prediction
    prediction = predict_landing(visible)
    
    if prediction is None:
        print("\nCould not make prediction!")
        return
    
    # Calculate error
    error = calculate_prediction_error(prediction, throw.actual_landing)
    
    print(f"\nPrediction:")
    print(f"  Predicted landing: ({prediction.landing_x:.2f}, {prediction.landing_y:.2f}) m")
    print(f"  Time to landing: {prediction.time_to_landing:.3f} s")
    print(f"  Confidence: {prediction.confidence:.2f}")
    print(f"  Frames used: {prediction.frames_used}")
    print(f"\n  ERROR: {error*100:.1f} cm")
    
    # Visualize
    visualize_throw(throw, prediction, f"Throw Simulation (seed={seed})")
    plt.show()


if __name__ == "__main__":
    main()
