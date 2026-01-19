"""
3D visualization for trajectory and predictions.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Optional
from src.simulator import Throw, TrajectoryPoint, get_visible_points
from src.predictor import Prediction
import config


def plot_camera_fov(ax, height: float = 4.0):
    """Draw the camera FOV cone."""
    # Camera at origin, pointing up
    # FOV is 70 degrees diagonal
    half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
    
    # Draw cone edges
    theta = np.linspace(0, 2*np.pi, 50)
    
    for zi in [height]:  # just draw top circle
        r = zi * np.tan(half_angle)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        ax.plot(x, y, [zi]*len(theta), 'b--', alpha=0.3, linewidth=1)
    
    # Draw 4 edge lines of cone
    for angle in [0, np.pi/2, np.pi, 3*np.pi/2]:
        r = height * np.tan(half_angle)
        ax.plot([0, r*np.cos(angle)], [0, r*np.sin(angle)], [0, height], 
                'b--', alpha=0.3, linewidth=1)


def plot_catch_plane(ax, size: float = 3.0):
    """Draw the catch plane."""
    h = config.CATCH_PLANE_HEIGHT_M
    x = np.array([-size/2, size/2, size/2, -size/2, -size/2])
    y = np.array([-size/2, -size/2, size/2, size/2, -size/2])
    ax.plot(x, y, [h]*5, 'g-', linewidth=2, label=f'Catch plane (z={h}m)')


def plot_trajectory(
    ax,
    throw: Throw,
    show_all_points: bool = True,
    show_visible_only: bool = True
):
    """Plot a trajectory."""
    # All points (ground truth)
    if show_all_points:
        all_x = [p.x_m for p in throw.observed_points]
        all_y = [p.y_m for p in throw.observed_points]
        all_z = [p.z_m for p in throw.observed_points]
        ax.plot(all_x, all_y, all_z, 'k-', alpha=0.3, linewidth=1, label='Full trajectory')
    
    # Visible points only
    if show_visible_only:
        visible = get_visible_points(throw)
        vis_x = [p.x_m for p in visible]
        vis_y = [p.y_m for p in visible]
        vis_z = [p.z_m for p in visible]
        ax.scatter(vis_x, vis_y, vis_z, c='blue', s=20, label='Camera observations')
    
    # Actual landing
    ax.scatter([throw.actual_landing[0]], [throw.actual_landing[1]], 
               [config.CATCH_PLANE_HEIGHT_M], c='green', s=100, marker='*',
               label='Actual landing')


def plot_prediction(ax, prediction: Prediction):
    """Plot predicted landing point."""
    ax.scatter([prediction.landing_x], [prediction.landing_y],
               [config.CATCH_PLANE_HEIGHT_M], c='red', s=100, marker='x',
               label=f'Predicted (conf={prediction.confidence:.2f})')


def visualize_throw(
    throw: Throw,
    prediction: Optional[Prediction] = None,
    title: str = "Trajectory Visualization"
):
    """
    Create 3D visualization of a throw and optional prediction.
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Draw environment
    plot_camera_fov(ax)
    plot_catch_plane(ax)
    
    # Draw trajectory
    plot_trajectory(ax, throw)
    
    # Draw prediction if provided
    if prediction is not None:
        plot_prediction(ax, prediction)
        
        # Draw error line
        ax.plot(
            [throw.actual_landing[0], prediction.landing_x],
            [throw.actual_landing[1], prediction.landing_y],
            [config.CATCH_PLANE_HEIGHT_M, config.CATCH_PLANE_HEIGHT_M],
            'r--', linewidth=2
        )
    
    # Labels and formatting
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title(title)
    ax.legend(loc='upper left')
    
    # Set equal aspect ratio
    max_range = 3.0
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    ax.set_zlim([0, config.CAMERA_MAX_RANGE_M])
    
    plt.tight_layout()
    return fig, ax


def animate_prediction_over_time(
    throw: Throw,
    output_path: Optional[str] = None
):
    """
    Show how prediction improves as more frames arrive.
    Creates multiple subplots showing prediction at different frame counts.
    """
    from src.predictor import predict_landing, calculate_prediction_error
    
    visible = get_visible_points(throw)
    
    if len(visible) < 5:
        print("Not enough visible points for animation")
        return
    
    # Create figure with subplots
    n_frames = min(6, len(visible) - 4)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), subplot_kw={'projection': '3d'})
    axes = axes.flatten()
    
    frame_counts = np.linspace(5, len(visible), n_frames, dtype=int)
    
    for idx, n_frames_used in enumerate(frame_counts):
        ax = axes[idx]
        
        # Get prediction with limited frames
        prediction = predict_landing(visible[:n_frames_used])
        
        # Plot
        plot_camera_fov(ax, height=3.0)
        plot_catch_plane(ax, size=2.0)
        
        # Show points used
        used_x = [p.x_m for p in visible[:n_frames_used]]
        used_y = [p.y_m for p in visible[:n_frames_used]]
        used_z = [p.z_m for p in visible[:n_frames_used]]
        ax.scatter(used_x, used_y, used_z, c='blue', s=10)
        
        # Actual landing
        ax.scatter([throw.actual_landing[0]], [throw.actual_landing[1]], 
                   [config.CATCH_PLANE_HEIGHT_M], c='green', s=50, marker='*')
        
        if prediction:
            ax.scatter([prediction.landing_x], [prediction.landing_y],
                       [config.CATCH_PLANE_HEIGHT_M], c='red', s=50, marker='x')
            error = calculate_prediction_error(prediction, throw.actual_landing)
            ax.set_title(f'{n_frames_used} frames\nError: {error*100:.1f}cm')
        else:
            ax.set_title(f'{n_frames_used} frames\nNo prediction')
        
        ax.set_xlim([-2, 2])
        ax.set_ylim([-2, 2])
        ax.set_zlim([0, 3])
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
    
    plt.suptitle('Prediction Improvement Over Time')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
        print(f"Saved to {output_path}")
    
    return fig


if __name__ == "__main__":
    # Quick test
    from src.simulator import generate_throw
    from src.predictor import predict_landing
    
    np.random.seed(42)
    throw = generate_throw()
    visible = get_visible_points(throw)
    prediction = predict_landing(visible)
    
    visualize_throw(throw, prediction, "Test Visualization")
    plt.show()
