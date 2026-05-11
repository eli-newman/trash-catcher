"""
Live simulation showing continuous prediction refinement in real-time.

This script demonstrates the ContinuousPredictor by:
1. Simulating camera frames arriving one at a time
2. Updating prediction with each new frame
3. Visualizing the prediction improvement live
4. Showing confidence and actionable status

Usage: python scripts/live_sim.py [seed]
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Optional

from src.simulator import generate_throw, get_visible_points, TrajectoryPoint
from src.predictor import ContinuousPredictor, calculate_prediction_error, Prediction
from src.logging_config import setup_logging
from src.config_validator import validate_config
import config


class LiveSimulation:
    """Real-time simulation of continuous prediction."""

    def __init__(self, throw, fps: int = 30):
        """Initialize live simulation."""
        self.throw = throw
        self.visible_points = get_visible_points(throw)
        self.fps = fps
        self.current_frame = 0

        # Create continuous predictor
        self.predictor = ContinuousPredictor()

        # History for plotting
        self.error_history = []
        self.confidence_history = []
        self.frame_numbers = []

        # Setup plots
        self.fig = plt.figure(figsize=(16, 9))
        self.ax_3d = self.fig.add_subplot(2, 3, 1, projection='3d')
        self.ax_topdown = self.fig.add_subplot(2, 3, 2)
        self.ax_error = self.fig.add_subplot(2, 3, 3)
        self.ax_confidence = self.fig.add_subplot(2, 3, 4)
        self.ax_frames = self.fig.add_subplot(2, 3, 5)
        self.ax_info = self.fig.add_subplot(2, 3, 6)
        self.ax_info.axis('off')

        self._setup_plots()

    def _setup_plots(self):
        """Setup static plot elements."""
        # 3D view
        self.ax_3d.set_xlabel('X (m)')
        self.ax_3d.set_ylabel('Y (m)')
        self.ax_3d.set_zlabel('Z (m)')
        self.ax_3d.set_title('3D View')
        self.ax_3d.set_xlim([-2, 2])
        self.ax_3d.set_ylim([-2, 2])
        self.ax_3d.set_zlim([0, 4])

        # Draw camera FOV cone
        half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
        theta = np.linspace(0, 2*np.pi, 30)
        for zi in [3.0]:
            r = zi * np.tan(half_angle)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            self.ax_3d.plot(x, y, [zi]*len(theta), 'b--', alpha=0.2, linewidth=1)

        # Draw catch plane
        catch_h = config.CATCH_PLANE_HEIGHT_M
        x_plane = np.array([-1.5, 1.5, 1.5, -1.5, -1.5])
        y_plane = np.array([-1.5, -1.5, 1.5, 1.5, -1.5])
        self.ax_3d.plot(x_plane, y_plane, [catch_h]*5, 'g-', linewidth=2, alpha=0.5)

        # Top-down view
        self.ax_topdown.set_xlabel('X (m)')
        self.ax_topdown.set_ylabel('Y (m)')
        self.ax_topdown.set_title('Top-Down View (Catch Plane)')
        self.ax_topdown.set_xlim([-1.5, 1.5])
        self.ax_topdown.set_ylim([-1.5, 1.5])
        self.ax_topdown.grid(True, alpha=0.3)
        self.ax_topdown.set_aspect('equal')

        # Draw FOV circle on top-down
        r_fov = catch_h * np.tan(np.radians(config.CAMERA_FOV_DEGREES / 2))
        circle = plt.Circle((0, 0), r_fov, color='blue', fill=False, linestyle='--', alpha=0.3)
        self.ax_topdown.add_patch(circle)

        # Plot actual landing
        self.ax_topdown.scatter(
            [self.throw.actual_landing[0]],
            [self.throw.actual_landing[1]],
            c='green', s=200, marker='*',
            label='Actual', zorder=10
        )

        # Error plot
        self.ax_error.set_xlabel('Frame Number')
        self.ax_error.set_ylabel('Error (cm)')
        self.ax_error.set_title('Prediction Error Over Time')
        self.ax_error.grid(True, alpha=0.3)

        # Confidence plot
        self.ax_confidence.set_xlabel('Frame Number')
        self.ax_confidence.set_ylabel('Confidence')
        self.ax_confidence.set_title('Confidence Over Time')
        self.ax_confidence.set_ylim([0, 1])
        self.ax_confidence.axhline(y=0.6, color='orange', linestyle='--', alpha=0.5, label='Min actionable')
        self.ax_confidence.axhline(y=0.7, color='red', linestyle='--', alpha=0.5, label='High confidence')
        self.ax_confidence.grid(True, alpha=0.3)
        self.ax_confidence.legend()

        # Frames timeline
        self.ax_frames.set_xlabel('Frame Number')
        self.ax_frames.set_ylabel('Count')
        self.ax_frames.set_title('Frames Accumulated')
        self.ax_frames.grid(True, alpha=0.3)

        plt.tight_layout()

    def update(self, frame_idx):
        """Update function called by animation."""
        if frame_idx >= len(self.visible_points):
            return

        # Get new frame
        frame = self.visible_points[frame_idx]

        # Update predictor
        prediction = self.predictor.add_frame(frame)

        # Update history
        if prediction:
            error = calculate_prediction_error(prediction, self.throw.actual_landing)
            self.error_history.append(error * 100)  # Convert to cm
            self.confidence_history.append(prediction.confidence)
            self.frame_numbers.append(frame_idx)

            # Update 3D plot
            self.ax_3d.clear()
            self._setup_3d_view()

            # Show accumulated points
            points_so_far = self.visible_points[:frame_idx + 1]
            xs = [p.x_m for p in points_so_far]
            ys = [p.y_m for p in points_so_far]
            zs = [p.z_m for p in points_so_far]
            self.ax_3d.scatter(xs, ys, zs, c='blue', s=20, alpha=0.6)

            # Show current frame highlighted
            self.ax_3d.scatter([frame.x_m], [frame.y_m], [frame.z_m],
                             c='cyan', s=100, marker='o', edgecolors='white', linewidths=2)

            # Show actual landing
            self.ax_3d.scatter(
                [self.throw.actual_landing[0]],
                [self.throw.actual_landing[1]],
                [config.CATCH_PLANE_HEIGHT_M],
                c='green', s=200, marker='*', label='Actual'
            )

            # Show predicted landing
            color = 'red' if prediction.is_actionable(0.7) else 'orange'
            self.ax_3d.scatter(
                [prediction.landing_x],
                [prediction.landing_y],
                [config.CATCH_PLANE_HEIGHT_M],
                c=color, s=200, marker='x', linewidths=3, label='Predicted'
            )

            # Draw error line
            self.ax_3d.plot(
                [self.throw.actual_landing[0], prediction.landing_x],
                [self.throw.actual_landing[1], prediction.landing_y],
                [config.CATCH_PLANE_HEIGHT_M, config.CATCH_PLANE_HEIGHT_M],
                'r--', linewidth=2, alpha=0.7
            )

            self.ax_3d.legend()

            # Update top-down view
            self.ax_topdown.clear()
            self._setup_topdown_view()

            # Show prediction on top-down
            self.ax_topdown.scatter(
                [prediction.landing_x],
                [prediction.landing_y],
                c=color, s=200, marker='x', linewidths=3, label='Predicted'
            )

            # Show actual
            self.ax_topdown.scatter(
                [self.throw.actual_landing[0]],
                [self.throw.actual_landing[1]],
                c='green', s=200, marker='*', label='Actual', zorder=10
            )

            # Draw error circle
            if error < 0.5:  # Only show if error is reasonable
                circle = plt.Circle(
                    (self.throw.actual_landing[0], self.throw.actual_landing[1]),
                    error, color='red', fill=False, linestyle='--', alpha=0.5
                )
                self.ax_topdown.add_patch(circle)

            self.ax_topdown.legend()

            # Update error plot
            self.ax_error.clear()
            self.ax_error.plot(self.frame_numbers, self.error_history, 'b-o', linewidth=2)
            self.ax_error.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='10cm target')
            self.ax_error.set_xlabel('Frame Number')
            self.ax_error.set_ylabel('Error (cm)')
            self.ax_error.set_title('Prediction Error Over Time')
            self.ax_error.grid(True, alpha=0.3)
            self.ax_error.legend()

            # Update confidence plot
            self.ax_confidence.clear()
            self.ax_confidence.plot(self.frame_numbers, self.confidence_history, 'g-o', linewidth=2)
            self.ax_confidence.axhline(y=0.6, color='orange', linestyle='--', alpha=0.5, label='Min actionable')
            self.ax_confidence.axhline(y=0.7, color='red', linestyle='--', alpha=0.5, label='High confidence')
            self.ax_confidence.set_xlabel('Frame Number')
            self.ax_confidence.set_ylabel('Confidence')
            self.ax_confidence.set_title('Confidence Over Time')
            self.ax_confidence.set_ylim([0, 1])
            self.ax_confidence.grid(True, alpha=0.3)
            self.ax_confidence.legend()

            # Update frames plot
            self.ax_frames.clear()
            self.ax_frames.bar([0], [frame_idx + 1], width=0.5, color='blue', alpha=0.6)
            self.ax_frames.set_xlabel('Accumulated')
            self.ax_frames.set_ylabel('Frame Count')
            self.ax_frames.set_title(f'Frames: {frame_idx + 1}/{len(self.visible_points)}')
            self.ax_frames.set_xlim([-0.5, 0.5])
            self.ax_frames.set_ylim([0, len(self.visible_points) + 5])
            self.ax_frames.set_xticks([])

            # Update info panel
            self.ax_info.clear()
            self.ax_info.axis('off')

            status_color = 'green' if prediction.is_actionable(0.7) else 'orange'
            status_text = '✓ ACTIONABLE' if prediction.is_actionable(0.7) else '⏳ WAIT'

            info_text = f"""
LIVE SIMULATION STATUS

Frame: {frame_idx + 1}/{len(self.visible_points)}
Time: {frame.time_sec:.3f}s

PREDICTION:
  Position: ({prediction.landing_x:.3f}, {prediction.landing_y:.3f})
  Error: {error*100:.1f} cm
  Confidence: {prediction.confidence:.3f}
  Frames used: {prediction.frames_used}

  Status: {status_text}

ACTUAL:
  Position: ({self.throw.actual_landing[0]:.3f}, {self.throw.actual_landing[1]:.3f})
  Flight time: {self.throw.actual_flight_time:.3f}s

IMPROVEMENT:
  First error: {self.error_history[0]:.1f} cm
  Current error: {error*100:.1f} cm
  Δ: {self.error_history[0] - error*100:+.1f} cm
            """

            self.ax_info.text(0.05, 0.95, info_text,
                            transform=self.ax_info.transAxes,
                            fontsize=10, verticalalignment='top',
                            fontfamily='monospace',
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

            # Add status indicator
            self.ax_info.text(0.5, 0.15, status_text,
                            transform=self.ax_info.transAxes,
                            fontsize=16, fontweight='bold',
                            color=status_color,
                            ha='center',
                            bbox=dict(boxstyle='round', facecolor=status_color, alpha=0.2))

    def _setup_3d_view(self):
        """Reset 3D view static elements."""
        self.ax_3d.set_xlabel('X (m)')
        self.ax_3d.set_ylabel('Y (m)')
        self.ax_3d.set_zlabel('Z (m)')
        self.ax_3d.set_title('3D View (Live)')
        self.ax_3d.set_xlim([-2, 2])
        self.ax_3d.set_ylim([-2, 2])
        self.ax_3d.set_zlim([0, 4])

        # Redraw camera FOV
        half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
        theta = np.linspace(0, 2*np.pi, 30)
        for zi in [3.0]:
            r = zi * np.tan(half_angle)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            self.ax_3d.plot(x, y, [zi]*len(theta), 'b--', alpha=0.2, linewidth=1)

        # Redraw catch plane
        catch_h = config.CATCH_PLANE_HEIGHT_M
        x_plane = np.array([-1.5, 1.5, 1.5, -1.5, -1.5])
        y_plane = np.array([-1.5, -1.5, 1.5, 1.5, -1.5])
        self.ax_3d.plot(x_plane, y_plane, [catch_h]*5, 'g-', linewidth=2, alpha=0.5)

    def _setup_topdown_view(self):
        """Reset top-down view static elements."""
        self.ax_topdown.set_xlabel('X (m)')
        self.ax_topdown.set_ylabel('Y (m)')
        self.ax_topdown.set_title('Top-Down View (Catch Plane)')
        self.ax_topdown.set_xlim([-1.5, 1.5])
        self.ax_topdown.set_ylim([-1.5, 1.5])
        self.ax_topdown.grid(True, alpha=0.3)
        self.ax_topdown.set_aspect('equal')

        # Redraw FOV circle
        catch_h = config.CATCH_PLANE_HEIGHT_M
        r_fov = catch_h * np.tan(np.radians(config.CAMERA_FOV_DEGREES / 2))
        circle = plt.Circle((0, 0), r_fov, color='blue', fill=False, linestyle='--', alpha=0.3)
        self.ax_topdown.add_patch(circle)

    def run(self, interval: int = 100):
        """Run the live simulation."""
        anim = FuncAnimation(
            self.fig,
            self.update,
            frames=len(self.visible_points),
            interval=interval,
            repeat=False
        )
        plt.show()


def get_throw_parameters():
    """Interactive prompt for throw parameters."""
    print("\n" + "="*70)
    print("LIVE SIMULATION - Continuous Prediction Refinement")
    print("="*70)
    print("\nConfigure your throw:")
    print("-" * 70)

    # Start position
    print("\n1. START POSITION (meters)")
    print("   Camera is at origin (0, 0, 0) looking up")
    print("   Default: (1.0, 0.5, 2.5) - slightly off-center, 2.5m high")

    use_default_pos = input("\n   Use default start position? (y/n) [y]: ").strip().lower()
    if use_default_pos in ['n', 'no']:
        x = float(input("   X (side to side, m) [-2 to 2]: "))
        y = float(input("   Y (forward/back, m) [-2 to 2]: "))
        z = float(input("   Z (height, m) [1 to 4]: "))
        start_pos = (x, y, z)
    else:
        start_pos = (1.0, 0.5, 2.5)

    print(f"   → Start position: ({start_pos[0]:.1f}, {start_pos[1]:.1f}, {start_pos[2]:.1f})")

    # Start velocity
    print("\n2. START VELOCITY (m/s)")
    print("   Positive X = right, Positive Y = away from camera, Positive Z = up")
    print("   Default: (-0.5, 0.3, 1.0) - gentle arc toward camera")

    use_default_vel = input("\n   Use default velocity? (y/n) [y]: ").strip().lower()
    if use_default_vel in ['n', 'no']:
        vx = float(input("   VX (horizontal, m/s) [-5 to 5]: "))
        vy = float(input("   VY (horizontal, m/s) [-5 to 5]: "))
        vz = float(input("   VZ (vertical, m/s) [-5 to 5]: "))
        start_vel = (vx, vy, vz)
    else:
        start_vel = (-0.5, 0.3, 1.0)

    print(f"   → Start velocity: ({start_vel[0]:.1f}, {start_vel[1]:.1f}, {start_vel[2]:.1f})")

    # Noise and dropout
    print("\n3. MEASUREMENT NOISE")
    add_noise = input("   Add realistic camera noise (±2cm)? (y/n) [y]: ").strip().lower()
    add_noise = add_noise not in ['n', 'no']

    print("\n4. FRAME DROPOUT")
    dropout_str = input("   Dropout probability (0.0-0.2) [0.05]: ").strip()
    dropout = float(dropout_str) if dropout_str else 0.05

    # Random seed
    print("\n5. RANDOM SEED")
    seed_str = input("   Random seed for reproducibility [42]: ").strip()
    seed = int(seed_str) if seed_str else 42

    return start_pos, start_vel, add_noise, dropout, seed


def main():
    """Main entry point."""
    # Setup
    setup_logging(level="WARNING")  # Quiet for live sim
    validate_config()

    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--preset':
        # Use preset parameters
        start_pos = (1.0, 0.5, 2.5)
        start_vel = (-0.5, 0.3, 1.0)
        add_noise = True
        dropout = 0.05
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42

        print("\n" + "="*70)
        print("LIVE SIMULATION - Continuous Prediction Refinement")
        print("="*70)
        print("\nUsing preset configuration...")
    else:
        # Interactive configuration
        start_pos, start_vel, add_noise, dropout, seed = get_throw_parameters()

    print("\n" + "-"*70)
    print("GENERATING THROW...")
    print("-"*70)

    # Generate throw
    np.random.seed(seed)
    throw = generate_throw(
        start_position=start_pos,
        start_velocity=start_vel,
        add_measurement_noise=add_noise,
        dropout_probability=dropout
    )

    visible = get_visible_points(throw)
    print(f"\n✓ Visible frames: {len(visible)}")
    print(f"✓ Actual landing: ({throw.actual_landing[0]:.3f}, {throw.actual_landing[1]:.3f})")
    print(f"✓ Flight time: {throw.actual_flight_time:.3f}s")

    if len(visible) < 5:
        print("\n⚠ WARNING: Not enough visible frames for prediction!")
        print("   Try adjusting start position or velocity to stay in FOV longer.")
        return

    print("\nStarting live simulation...")
    print("Watch how prediction improves as frames arrive!")
    print("\nClose the window to exit.")

    # Run simulation
    sim = LiveSimulation(throw, fps=config.CAMERA_FPS)
    sim.run(interval=100)  # 100ms per frame (10 FPS playback)


def print_usage():
    """Print usage information."""
    print("""
Usage:
  python scripts/live_sim.py              # Interactive configuration
  python scripts/live_sim.py --preset     # Use default preset (seed 42)
  python scripts/live_sim.py --preset 123 # Use preset with custom seed

Preset Scenarios (use with --preset):
  - Seed 42:  Center arc (default)
  - Seed 100: Side throw
  - Seed 200: Fast toss
  - Seed 300: High arc
  - Seed 400: FOV entry (challenging!)

Interactive mode lets you configure:
  - Start position (x, y, z)
  - Start velocity (vx, vy, vz)
  - Measurement noise on/off
  - Frame dropout probability
  - Random seed

The simulation shows:
  - 3D trajectory view
  - Top-down catch plane view
  - Error improvement over time
  - Confidence growth
  - Real-time actionable status
""")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
    else:
        main()
