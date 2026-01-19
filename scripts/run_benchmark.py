"""
Run many throws and measure prediction accuracy.
Usage: python scripts/run_benchmark.py [num_throws]
"""

import sys
import numpy as np

sys.path.insert(0, '.')

from src.simulator import generate_throw, get_visible_points
from src.predictor import predict_landing, calculate_prediction_error


def run_benchmark(num_throws: int = 100):
    """Run benchmark and collect statistics."""
    
    errors = []
    failures = 0
    not_enough_frames = 0
    
    print(f"Running {num_throws} throw simulations...")
    
    for i in range(num_throws):
        np.random.seed(i)
        
        throw = generate_throw(
            add_measurement_noise=True,
            dropout_probability=0.05
        )
        
        visible = get_visible_points(throw)
        
        if len(visible) < 5:
            not_enough_frames += 1
            continue
        
        prediction = predict_landing(visible)
        
        if prediction is None:
            failures += 1
            continue
        
        error = calculate_prediction_error(prediction, throw.actual_landing)
        errors.append(error)
    
    # Calculate statistics
    errors = np.array(errors)
    
    print("\n" + "="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    print(f"\nTotal throws: {num_throws}")
    print(f"Successful predictions: {len(errors)}")
    print(f"Failed predictions: {failures}")
    print(f"Not enough frames: {not_enough_frames}")
    
    if len(errors) > 0:
        print(f"\nError Statistics (cm):")
        print(f"  Mean:   {errors.mean()*100:.1f}")
        print(f"  Median: {np.median(errors)*100:.1f}")
        print(f"  Std:    {errors.std()*100:.1f}")
        print(f"  Min:    {errors.min()*100:.1f}")
        print(f"  Max:    {errors.max()*100:.1f}")
        
        # Accuracy buckets
        print(f"\nAccuracy breakdown:")
        print(f"  < 5cm:  {(errors < 0.05).sum()} ({(errors < 0.05).mean()*100:.1f}%)")
        print(f"  < 10cm: {(errors < 0.10).sum()} ({(errors < 0.10).mean()*100:.1f}%)")
        print(f"  < 20cm: {(errors < 0.20).sum()} ({(errors < 0.20).mean()*100:.1f}%)")
        print(f"  < 30cm: {(errors < 0.30).sum()} ({(errors < 0.30).mean()*100:.1f}%)")
        
        # Success rate at 10cm target
        success_rate = (errors < 0.10).mean() * 100
        print(f"\n{'='*50}")
        print(f"SUCCESS RATE (< 10cm): {success_rate:.1f}%")
        print(f"{'='*50}")
        
        return success_rate
    
    return 0.0


if __name__ == "__main__":
    num_throws = 100
    if len(sys.argv) > 1:
        num_throws = int(sys.argv[1])
    
    run_benchmark(num_throws)
