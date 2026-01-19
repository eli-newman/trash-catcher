#!/usr/bin/env python3
"""
Create an animated video of object entering FOV mid-flight.
Shows frame-by-frame how the camera tracks the object.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from mpl_toolkits.mplot3d import Axes3D

# Add parent directory to path
sys.path.insert(0, '.')

from src.simulator import generate_throw, get_visible_points
from src.predictor import predict_landing, calculate_prediction_error
import config

def plot_fov_cone(ax, height_max=3.5, num_points=20):
    """Plot the camera's field of view as a cone."""
    half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)

    z = np.linspace(0.1, height_max, num_points)
    theta = np.linspace(0, 2*np.pi, num_points)
    Z, Theta = np.meshgrid(z, theta)

    R = Z * np.tan(half_angle)
    X = R * np.cos(Theta)
    Y = R * np.sin(Theta)

    ax.plot_wireframe(X, Y, Z, alpha=0.15, color='gray', linewidth=0.5)

def main():
    print("Generating FOV entry animation...")

    np.random.seed(789)

    # Generate throw
    throw = generate_throw(
        start_position=(2.5, 0.0, 1.5),
        start_velocity=(-3.0, 0.0, 3.0),
        add_measurement_noise=False,
        dropout_probability=0.0
    )

    visible_points = get_visible_points(throw)
    all_points = throw.observed_points

    # Create figure with two subplots
    fig = plt.figure(figsize=(14, 6))
    ax1 = fig.add_subplot(121, projection='3d')
    ax2 = fig.add_subplot(122)

    # Store objects to update
    objects = {}

    def init():
        """Initialize the animation."""
        # 3D plot setup
        plot_fov_cone(ax1)

        # Camera
        ax1.scatter([0], [0], [0], c='black', marker='^', s=100, label='Camera')

        # Landing plane
        catch_z = config.CATCH_PLANE_HEIGHT_M

        # Start position
        ax1.scatter([throw.start_position[0]], [throw.start_position[1]],
                   [throw.start_position[2]], c='blue', marker='o', s=100,
                   label='Start', alpha=0.3)

        # Actual landing
        ax1.scatter([throw.actual_landing[0]], [throw.actual_landing[1]], [catch_z],
                   c='orange', marker='*', s=200, label='Actual Landing', alpha=0.3)

        # Initialize trajectory lines
        objects['traj_line_3d'], = ax1.plot([], [], [], 'g-', linewidth=2, label='Trajectory')
        objects['traj_scatter_3d'] = ax1.scatter([], [], [], c='green', s=50)
        objects['current_point_3d'] = ax1.scatter([], [], [], c='red', s=200, marker='o')

        ax1.set_xlabel('X (m)')
        ax1.set_ylabel('Y (m)')
        ax1.set_zlabel('Z (m)')
        ax1.set_title('3D View - Object Entering FOV')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.set_xlim(-1, 3)
        ax1.set_ylim(-1, 1)
        ax1.set_zlim(0, 3.5)
        ax1.view_init(elev=20, azim=45)

        # 2D top-down plot setup
        # FOV circles
        heights = [1.0, 1.5, 2.0, 2.5, 3.0]
        half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
        for h in heights:
            radius = h * np.tan(half_angle)
            circle = plt.Circle((0, 0), radius, fill=False, color='gray',
                               alpha=0.2, linestyle='--', linewidth=1)
            ax2.add_patch(circle)

        # Camera
        ax2.scatter([0], [0], c='black', marker='^', s=100, label='Camera', zorder=5)

        # Start
        ax2.scatter([throw.start_position[0]], [throw.start_position[1]],
                   c='blue', marker='o', s=100, label='Start', alpha=0.3, zorder=5)

        # Landing
        ax2.scatter([throw.actual_landing[0]], [throw.actual_landing[1]],
                   c='orange', marker='*', s=200, label='Landing', alpha=0.3, zorder=5)

        # Initialize trajectory
        objects['traj_line_2d'], = ax2.plot([], [], 'g-', linewidth=2)
        objects['traj_scatter_2d'] = ax2.scatter([], [], c='green', s=30)
        objects['current_point_2d'] = ax2.scatter([], [], c='red', s=150, marker='o', zorder=10)

        ax2.set_xlabel('X (m)')
        ax2.set_ylabel('Y (m)')
        ax2.set_title('Top-Down View')
        ax2.set_aspect('equal')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right', fontsize=8)
        ax2.set_xlim(-1, 3)
        ax2.set_ylim(-1.5, 1.5)

        # Text for frame info
        objects['text'] = fig.text(0.5, 0.95, '', ha='center', fontsize=12, weight='bold')

        return list(objects.values())

    def animate(frame):
        """Update animation for each frame."""
        # Get points up to current frame
        current_points = [p for p in all_points if p.time_sec <= all_points[frame].time_sec]
        visible_so_far = [p for p in current_points if p.in_fov]

        current = all_points[frame]

        # Update 3D plot
        if visible_so_far:
            xs = [p.x_m for p in visible_so_far]
            ys = [p.y_m for p in visible_so_far]
            zs = [p.z_m for p in visible_so_far]
            objects['traj_line_3d'].set_data(xs, ys)
            objects['traj_line_3d'].set_3d_properties(zs)
            objects['traj_scatter_3d']._offsets3d = (xs, ys, zs)

        # Current point (only if in FOV)
        if current.in_fov:
            objects['current_point_3d']._offsets3d = ([current.x_m], [current.y_m], [current.z_m])
        else:
            objects['current_point_3d']._offsets3d = ([], [], [])

        # Update 2D plot
        if visible_so_far:
            xs = [p.x_m for p in visible_so_far]
            ys = [p.y_m for p in visible_so_far]
            objects['traj_line_2d'].set_data(xs, ys)
            objects['traj_scatter_2d'].set_offsets(np.c_[xs, ys])

        if current.in_fov:
            objects['current_point_2d'].set_offsets([[current.x_m, current.y_m]])
        else:
            objects['current_point_2d'].set_offsets(np.empty((0, 2)))

        # Update text
        status = "✅ IN FOV" if current.in_fov else "❌ OUTSIDE FOV"
        prediction_text = ""

        if len(visible_so_far) >= 5:
            pred = predict_landing(visible_so_far)
            if pred:
                error = calculate_prediction_error(pred, throw.actual_landing)
                prediction_text = f" | Prediction Error: {error*100:.1f}cm"

        objects['text'].set_text(
            f"Frame {frame+1}/{len(all_points)} | t={current.time_sec:.3f}s | "
            f"{status} | Visible: {len(visible_so_far)}/{len(current_points)}{prediction_text}"
        )

        return list(objects.values())

    # Create animation
    print(f"Creating animation with {len(all_points)} frames...")
    anim = FuncAnimation(fig, animate, init_func=init, frames=len(all_points),
                        interval=100, blit=False, repeat=True)

    # Save as GIF
    output_file = "fov_entry_animation.gif"
    print(f"Saving animation to {output_file}...")
    writer = PillowWriter(fps=10)
    anim.save(output_file, writer=writer)

    print(f"✅ Animation saved to: {output_file}")
    print(f"\nAnimation details:")
    print(f"  Total frames: {len(all_points)}")
    print(f"  Visible frames: {len(visible_points)}")
    print(f"  Duration: ~{len(all_points)/10:.1f} seconds")
    print(f"  File size: check {output_file}")

    # Also show it
    print("\nDisplaying animation (close window when done)...")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
