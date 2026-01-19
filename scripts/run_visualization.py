"""
Run visualization showing prediction improvement over time.
Usage: python scripts/run_visualization.py [seed]
"""

import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, '.')

from src.simulator import generate_throw, get_visible_points
from src.visualizer import animate_prediction_over_time


def main():
    seed = 42
    if len(sys.argv) > 1:
        seed = int(sys.argv[1])
    
    np.random.seed(seed)
    print(f"Generating throw with seed={seed}")
    
    throw = generate_throw(
        add_measurement_noise=True,
        dropout_probability=0.0  # no dropouts for cleaner visualization
    )
    
    print(f"Visible frames: {len(get_visible_points(throw))}")
    print(f"Actual landing: ({throw.actual_landing[0]:.2f}, {throw.actual_landing[1]:.2f})")
    
    animate_prediction_over_time(throw)
    plt.show()


if __name__ == "__main__":
    main()
