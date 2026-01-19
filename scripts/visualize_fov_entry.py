#!/usr/bin/env python3
"""
Visualize object entering FOV mid-flight.
Shows 3D trajectory with FOV boundary and which parts are visible.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Add parent directory to path
sys.path.insert(0, '.')

from src.simulator import generate_throw, get_visible_points
from src.predictor import predict_landing, calculate_prediction_error
import config

def plot_fov_cone(ax, height_max=4.0, num_points=20):
    """Plot the camera's field of view as a cone."""
    half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)

    # Generate cone surface
    z = np.linspace(0.1, height_max, num_points)
    theta = np.linspace(0, 2*np.pi, num_points)
    Z, Theta = np.meshgrid(z, theta)

    # Radius at each height
    R = Z * np.tan(half_angle)

    # Convert to cartesian
    X = R * np.cos(Theta)
    Y = R * np.sin(Theta)

    # Plot as wireframe
    ax.plot_wireframe(X, Y, Z, alpha=0.1, color='gray', linewidth=0.5)

def main():
    np.random.seed(789)

    # Generate throw that enters FOV mid-flight
    throw = generate_throw(
        start_position=(2.5, 0.0, 1.5),
        start_velocity=(-3.0, 0.0, 3.0),
        add_measurement_noise=False,
        dropout_probability=0.0
    )

    visible_points = get_visible_points(throw)

    # Make prediction
    prediction = None
    if len(visible_points) >= 5:
        prediction = predict_landing(visible_points)

    # Create 3D plot
    fig = plt.figure(figsize=(14, 6))

    # Plot 1: Full trajectory with FOV
    ax1 = fig.add_subplot(121, projection='3d')

    # Plot FOV cone
    plot_fov_cone(ax1)

    # Plot full trajectory - color by visibility
    all_points = throw.observed_points
    outside_fov = [p for p in all_points if not p.in_fov]
    inside_fov = [p for p in all_points if p.in_fov]

    # Outside FOV (red)
    if outside_fov:
        xs = [p.x_m for p in outside_fov]
        ys = [p.y_m for p in outside_fov]
        zs = [p.z_m for p in outside_fov]
        ax1.plot(xs, ys, zs, 'r--', alpha=0.5, linewidth=2, label='Outside FOV')
        ax1.scatter(xs, ys, zs, c='red', marker='x', s=30, alpha=0.5)

    # Inside FOV (green)
    if inside_fov:
        xs = [p.x_m for p in inside_fov]
        ys = [p.y_m for p in inside_fov]
        zs = [p.z_m for p in inside_fov]
        ax1.plot(xs, ys, zs, 'g-', linewidth=2, label='Inside FOV (visible)')
        ax1.scatter(xs, ys, zs, c='green', marker='o', s=30)

    # Mark start and landing
    ax1.scatter([throw.start_position[0]], [throw.start_position[1]], [throw.start_position[2]],
                c='blue', marker='o', s=100, label='Start')
    ax1.scatter([throw.actual_landing[0]], [throw.actual_landing[1]], [config.CATCH_PLANE_HEIGHT_M],
                c='orange', marker='*', s=200, label='Actual Landing')

    if prediction:
        ax1.scatter([prediction.landing_x], [prediction.landing_y], [config.CATCH_PLANE_HEIGHT_M],
                    c='purple', marker='s', s=100, label='Predicted Landing')

    # Camera at origin
    ax1.scatter([0], [0], [0], c='black', marker='^', s=100, label='Camera')

    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Z (m)')
    ax1.set_title('3D Trajectory - FOV Entry')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.set_zlim(0, 4)

    # Plot 2: Top-down view
    ax2 = fig.add_subplot(122)

    # Plot FOV boundary at different heights
    heights = [1.0, 1.5, 2.0, 2.5, 3.0]
    half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
    for h in heights:
        radius = h * np.tan(half_angle)
        circle = plt.Circle((0, 0), radius, fill=False, color='gray',
                           alpha=0.3, linestyle='--', linewidth=1)
        ax2.add_patch(circle)
        ax2.text(radius, 0, f'z={h}m', fontsize=8, color='gray')

    # Plot trajectory - color by visibility
    if outside_fov:
        xs = [p.x_m for p in outside_fov]
        ys = [p.y_m for p in outside_fov]
        ax2.plot(xs, ys, 'r--', alpha=0.5, linewidth=2, label='Outside FOV')
        ax2.scatter(xs, ys, c='red', marker='x', s=30, alpha=0.5)

    if inside_fov:
        xs = [p.x_m for p in inside_fov]
        ys = [p.y_m for p in inside_fov]
        ax2.plot(xs, ys, 'g-', linewidth=2, label='Inside FOV')
        ax2.scatter(xs, ys, c='green', marker='o', s=30)

    # Mark start and landing
    ax2.scatter([throw.start_position[0]], [throw.start_position[1]],
                c='blue', marker='o', s=100, label='Start', zorder=5)
    ax2.scatter([throw.actual_landing[0]], [throw.actual_landing[1]],
                c='orange', marker='*', s=200, label='Actual Landing', zorder=5)

    if prediction:
        ax2.scatter([prediction.landing_x], [prediction.landing_y],
                    c='purple', marker='s', s=100, label='Predicted', zorder=5)
        error = calculate_prediction_error(prediction, throw.actual_landing)
        ax2.set_title(f'Top-Down View (Error: {error*100:.1f}cm)')
    else:
        ax2.set_title('Top-Down View')

    # Camera at origin
    ax2.scatter([0], [0], c='black', marker='^', s=100, label='Camera', zorder=5)

    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_aspect('equal')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right', fontsize=8)
    ax2.set_xlim(-1, 3)
    ax2.set_ylim(-1.5, 1.5)

    plt.tight_layout()

    # Print summary
    print("\n" + "="*70)
    print("FOV ENTRY VISUALIZATION")
    print("="*70)
    print(f"Total frames: {len(all_points)}")
    print(f"Visible frames: {len(inside_fov)}")
    print(f"Outside FOV: {len(outside_fov)}")
    print(f"Visibility: {len(inside_fov)/len(all_points)*100:.1f}%")

    if prediction:
        error = calculate_prediction_error(prediction, throw.actual_landing)
        print(f"\nPrediction error: {error*100:.1f}cm")
        print(f"Confidence: {prediction.confidence:.2f}")

    print("\nShowing visualization...")
    plt.show()

if __name__ == "__main__":
    main()
