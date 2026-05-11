"""
Live simulation with command-line configuration.

Configure throw parameters via command line or use presets.

Usage:
  # Use preset
  python scripts/live_sim_interactive.py --preset
  python scripts/live_sim_interactive.py --preset --seed 100

  # Custom throw
  python scripts/live_sim_interactive.py --pos 1 0.5 2.5 --vel -0.5 0.3 1
  python scripts/live_sim_interactive.py --pos 2 0 3 --vel -1 0 2 --noise --dropout 0.1

  # Preset scenarios
  python scripts/live_sim_interactive.py --scenario center    # Default gentle arc
  python scripts/live_sim_interactive.py --scenario side      # Side throw
  python scripts/live_sim_interactive.py --scenario fast      # Fast toss
  python scripts/live_sim_interactive.py --scenario high      # High arc
  python scripts/live_sim_interactive.py --scenario fov-entry # Enters FOV mid-flight
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
import argparse

from src.simulator import generate_throw, get_visible_points
from src.predictor import ContinuousPredictor, calculate_prediction_error
from src.logging_config import setup_logging
from src.config_validator import validate_config
import config

# Import LiveSimulation from live_sim
from live_sim import LiveSimulation


# Preset scenarios
SCENARIOS = {
    'center': {
        'pos': (1.0, 0.5, 2.5),
        'vel': (-0.5, 0.3, 1.0),
        'desc': 'Gentle arc toward center'
    },
    'side': {
        'pos': (1.5, -0.3, 2.8),
        'vel': (-0.8, 0.5, 0.8),
        'desc': 'Side throw with curve'
    },
    'fast': {
        'pos': (0.8, 0.8, 3.0),
        'vel': (-1.2, -0.2, 1.5),
        'desc': 'Fast toss'
    },
    'high': {
        'pos': (0.5, 0.2, 3.5),
        'vel': (-0.3, 0.1, 2.0),
        'desc': 'High arc'
    },
    'fov-entry': {
        'pos': (2.5, 0.0, 3.8),
        'vel': (-1.0, 0.0, 0.5),
        'desc': 'Enters FOV mid-flight (challenging!)'
    },
}


def main():
    parser = argparse.ArgumentParser(
        description='Live simulation with configurable throw parameters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Preset mode
    parser.add_argument('--preset', action='store_true',
                       help='Use default preset configuration')

    # Scenario mode
    parser.add_argument('--scenario', type=str, choices=SCENARIOS.keys(),
                       help='Use a preset scenario')

    # Custom parameters
    parser.add_argument('--pos', type=float, nargs=3, metavar=('X', 'Y', 'Z'),
                       help='Start position (x, y, z) in meters')
    parser.add_argument('--vel', type=float, nargs=3, metavar=('VX', 'VY', 'VZ'),
                       help='Start velocity (vx, vy, vz) in m/s')

    # Noise and dropout
    parser.add_argument('--noise', action='store_true', default=True,
                       help='Add measurement noise (default: True)')
    parser.add_argument('--no-noise', action='store_true',
                       help='Disable measurement noise')
    parser.add_argument('--dropout', type=float, default=0.05,
                       help='Frame dropout probability (default: 0.05)')

    # Random seed
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed (default: 42)')

    # Animation speed
    parser.add_argument('--speed', type=int, default=100,
                       help='Animation interval in ms (lower = faster, default: 100)')

    args = parser.parse_args()

    # Setup
    setup_logging(level="WARNING")
    validate_config()

    # Determine parameters
    if args.scenario:
        # Use scenario
        scenario = SCENARIOS[args.scenario]
        start_pos = scenario['pos']
        start_vel = scenario['vel']
        scenario_name = args.scenario.upper()
        scenario_desc = scenario['desc']
    elif args.pos and args.vel:
        # Custom parameters
        start_pos = tuple(args.pos)
        start_vel = tuple(args.vel)
        scenario_name = "CUSTOM"
        scenario_desc = "User-defined throw"
    elif args.preset:
        # Default preset
        start_pos = (1.0, 0.5, 2.5)
        start_vel = (-0.5, 0.3, 1.0)
        scenario_name = "PRESET"
        scenario_desc = "Default configuration"
    else:
        # No args - use default
        start_pos = (1.0, 0.5, 2.5)
        start_vel = (-0.5, 0.3, 1.0)
        scenario_name = "DEFAULT"
        scenario_desc = "Default configuration"

    # Noise setting
    add_noise = args.noise and not args.no_noise
    dropout = args.dropout
    seed = args.seed

    # Print configuration
    print("\n" + "="*70)
    print("LIVE SIMULATION - Continuous Prediction Refinement")
    print("="*70)
    print(f"\nScenario: {scenario_name}")
    print(f"Description: {scenario_desc}")
    print("\nConfiguration:")
    print(f"  Start position: ({start_pos[0]:.2f}, {start_pos[1]:.2f}, {start_pos[2]:.2f}) m")
    print(f"  Start velocity: ({start_vel[0]:.2f}, {start_vel[1]:.2f}, {start_vel[2]:.2f}) m/s")
    print(f"  Measurement noise: {'ON' if add_noise else 'OFF'}")
    print(f"  Dropout probability: {dropout:.2f}")
    print(f"  Random seed: {seed}")
    print(f"  Animation speed: {args.speed}ms per frame")

    # Generate throw
    print("\n" + "-"*70)
    print("GENERATING THROW...")
    print("-"*70)

    np.random.seed(seed)
    throw = generate_throw(
        start_position=start_pos,
        start_velocity=start_vel,
        add_measurement_noise=add_noise,
        dropout_probability=dropout
    )

    visible = get_visible_points(throw)
    print(f"\n✓ Total frames: {len(throw.observed_points)}")
    print(f"✓ Visible frames: {len(visible)}")
    print(f"✓ Actual landing: ({throw.actual_landing[0]:.3f}, {throw.actual_landing[1]:.3f})")
    print(f"✓ Flight time: {throw.actual_flight_time:.3f}s")

    if len(visible) < 5:
        print("\n⚠ WARNING: Not enough visible frames for prediction!")
        print("   Try adjusting start position or velocity to stay in FOV longer.")
        print("\nSuggested fixes:")
        print("  - Reduce horizontal velocity")
        print("  - Start closer to camera (smaller X, Y)")
        print("  - Start higher (larger Z)")
        return

    print("\nStarting live simulation...")
    print("Watch how prediction improves as frames arrive!")
    print("\n📊 The simulation shows:")
    print("  • 3D trajectory view with live prediction")
    print("  • Top-down catch plane view")
    print("  • Error decreasing over time")
    print("  • Confidence increasing over time")
    print("  • Actionable status (when servo should move)")
    print("\nClose the window to exit.")

    # Run simulation
    sim = LiveSimulation(throw, fps=config.CAMERA_FPS)
    sim.run(interval=args.speed)


def list_scenarios():
    """Print available scenarios."""
    print("\nAvailable Scenarios:")
    print("-" * 70)
    for name, info in SCENARIOS.items():
        print(f"\n{name}:")
        print(f"  Description: {info['desc']}")
        print(f"  Position: {info['pos']}")
        print(f"  Velocity: {info['vel']}")
    print()


if __name__ == "__main__":
    # Check for special commands
    if len(sys.argv) > 1 and sys.argv[1] in ['--list', 'list']:
        list_scenarios()
    else:
        main()
