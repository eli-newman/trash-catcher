#!/usr/bin/env python3
"""
Interactive trash-catching simulator with live parameter controls.
Use sliders to adjust throw angle, speed, and starting position in real-time.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from mpl_toolkits.mplot3d import Axes3D

# Add parent directory to path
sys.path.insert(0, '.')

from src.simulator import generate_throw, get_visible_points
from src.predictor import predict_landing, calculate_prediction_error
import config

class InteractiveSimulator:
    def __init__(self):
        # Create figure with 3D and 2D plots
        self.fig = plt.figure(figsize=(16, 8))
        self.ax_3d = self.fig.add_subplot(121, projection='3d')
        self.ax_2d = self.fig.add_subplot(122)

        # Initial parameters
        self.params = {
            'start_x': 2.0,
            'start_y': 0.0,
            'start_z': 1.5,
            'speed': 3.5,
            'angle_horizontal': -45,  # degrees from +x axis
            'angle_vertical': 60,     # degrees from horizontal
        }

        # Storage for plot objects
        self.plot_objects = {}

        # Create sliders
        self.create_controls()

        # Initial plot
        self.update_simulation(None)

    def create_controls(self):
        """Create interactive sliders and buttons."""
        # Make room for sliders at bottom
        self.fig.subplots_adjust(bottom=0.35)

        slider_color = 'lightgoldenrodyellow'

        # Starting position X
        ax_start_x = self.fig.add_axes([0.15, 0.25, 0.3, 0.02])
        self.slider_start_x = Slider(ax_start_x, 'Start X (m)', -3.0, 3.0,
                                     valinit=self.params['start_x'], color=slider_color)

        # Starting position Y
        ax_start_y = self.fig.add_axes([0.15, 0.22, 0.3, 0.02])
        self.slider_start_y = Slider(ax_start_y, 'Start Y (m)', -2.0, 2.0,
                                     valinit=self.params['start_y'], color=slider_color)

        # Starting height Z
        ax_start_z = self.fig.add_axes([0.15, 0.19, 0.3, 0.02])
        self.slider_start_z = Slider(ax_start_z, 'Start Z (m)', 0.5, 3.5,
                                     valinit=self.params['start_z'], color=slider_color)

        # Speed
        ax_speed = self.fig.add_axes([0.15, 0.15, 0.3, 0.02])
        self.slider_speed = Slider(ax_speed, 'Speed (m/s)', 0.5, 6.0,
                                   valinit=self.params['speed'], color=slider_color)

        # Horizontal angle
        ax_angle_h = self.fig.add_axes([0.15, 0.11, 0.3, 0.02])
        self.slider_angle_h = Slider(ax_angle_h, 'Horizontal Angle (°)', -180, 180,
                                     valinit=self.params['angle_horizontal'], color=slider_color)

        # Vertical angle
        ax_angle_v = self.fig.add_axes([0.15, 0.07, 0.3, 0.02])
        self.slider_angle_v = Slider(ax_angle_v, 'Vertical Angle (°)', -30, 90,
                                     valinit=self.params['angle_vertical'], color=slider_color)

        # Reset button
        ax_reset = self.fig.add_axes([0.15, 0.02, 0.1, 0.03])
        self.btn_reset = Button(ax_reset, 'Reset', color=slider_color)

        # Preset buttons
        ax_preset1 = self.fig.add_axes([0.55, 0.25, 0.12, 0.03])
        self.btn_preset1 = Button(ax_preset1, 'Center Drop', color='lightblue')

        ax_preset2 = self.fig.add_axes([0.68, 0.25, 0.12, 0.03])
        self.btn_preset2 = Button(ax_preset2, 'Side Arc', color='lightgreen')

        ax_preset3 = self.fig.add_axes([0.55, 0.21, 0.12, 0.03])
        self.btn_preset3 = Button(ax_preset3, 'Fast Toss', color='lightyellow')

        ax_preset4 = self.fig.add_axes([0.68, 0.21, 0.12, 0.03])
        self.btn_preset4 = Button(ax_preset4, 'FOV Entry', color='lightcoral')

        # Connect callbacks
        self.slider_start_x.on_changed(self.update_simulation)
        self.slider_start_y.on_changed(self.update_simulation)
        self.slider_start_z.on_changed(self.update_simulation)
        self.slider_speed.on_changed(self.update_simulation)
        self.slider_angle_h.on_changed(self.update_simulation)
        self.slider_angle_v.on_changed(self.update_simulation)
        self.btn_reset.on_clicked(self.reset)
        self.btn_preset1.on_clicked(self.preset_center_drop)
        self.btn_preset2.on_clicked(self.preset_side_arc)
        self.btn_preset3.on_clicked(self.preset_fast_toss)
        self.btn_preset4.on_clicked(self.preset_fov_entry)

    def get_velocity_from_angles(self):
        """Convert speed and angles to velocity vector."""
        speed = self.params['speed']
        angle_h = np.radians(self.params['angle_horizontal'])
        angle_v = np.radians(self.params['angle_vertical'])

        # Velocity components
        vx = speed * np.cos(angle_v) * np.cos(angle_h)
        vy = speed * np.cos(angle_v) * np.sin(angle_h)
        vz = speed * np.sin(angle_v)

        return (vx, vy, vz)

    def update_simulation(self, val):
        """Update simulation with current parameters."""
        # Get current values
        self.params['start_x'] = self.slider_start_x.val
        self.params['start_y'] = self.slider_start_y.val
        self.params['start_z'] = self.slider_start_z.val
        self.params['speed'] = self.slider_speed.val
        self.params['angle_horizontal'] = self.slider_angle_h.val
        self.params['angle_vertical'] = self.slider_angle_v.val

        start_pos = (self.params['start_x'], self.params['start_y'], self.params['start_z'])
        start_vel = self.get_velocity_from_angles()

        # Generate throw
        try:
            throw = generate_throw(
                start_position=start_pos,
                start_velocity=start_vel,
                add_measurement_noise=False,
                dropout_probability=0.0
            )

            visible_points = get_visible_points(throw)

            # Make prediction if enough visible points
            prediction = None
            if len(visible_points) >= 5:
                prediction = predict_landing(visible_points)

            # Update plots
            self.plot_3d(throw, visible_points, prediction)
            self.plot_2d(throw, visible_points, prediction)

            self.fig.canvas.draw_idle()

        except Exception as e:
            # If trajectory is invalid, show error
            self.ax_3d.clear()
            self.ax_2d.clear()
            self.ax_3d.text(0, 0, 2, f"Invalid trajectory:\n{str(e)}",
                          ha='center', va='center', fontsize=12, color='red')
            self.fig.canvas.draw_idle()

    def plot_3d(self, throw, visible_points, prediction):
        """Update 3D plot."""
        self.ax_3d.clear()

        # FOV cone
        half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
        z = np.linspace(0.1, 3.5, 15)
        theta = np.linspace(0, 2*np.pi, 15)
        Z, Theta = np.meshgrid(z, theta)
        R = Z * np.tan(half_angle)
        X = R * np.cos(Theta)
        Y = R * np.sin(Theta)
        self.ax_3d.plot_wireframe(X, Y, Z, alpha=0.1, color='gray', linewidth=0.5)

        # Trajectory
        all_points = throw.observed_points
        outside_fov = [p for p in all_points if not p.in_fov]
        inside_fov = [p for p in all_points if p.in_fov]

        if outside_fov:
            xs = [p.x_m for p in outside_fov]
            ys = [p.y_m for p in outside_fov]
            zs = [p.z_m for p in outside_fov]
            self.ax_3d.plot(xs, ys, zs, 'r--', alpha=0.5, linewidth=2, label='Outside FOV')

        if inside_fov:
            xs = [p.x_m for p in inside_fov]
            ys = [p.y_m for p in inside_fov]
            zs = [p.z_m for p in inside_fov]
            self.ax_3d.plot(xs, ys, zs, 'g-', linewidth=2, label='Inside FOV')

        # Markers
        self.ax_3d.scatter([0], [0], [0], c='black', marker='^', s=100, label='Camera')
        self.ax_3d.scatter([throw.start_position[0]], [throw.start_position[1]],
                          [throw.start_position[2]], c='blue', marker='o', s=100, label='Start')
        self.ax_3d.scatter([throw.actual_landing[0]], [throw.actual_landing[1]],
                          [config.CATCH_PLANE_HEIGHT_M], c='orange', marker='*', s=200,
                          label='Actual Landing')

        if prediction:
            self.ax_3d.scatter([prediction.landing_x], [prediction.landing_y],
                              [config.CATCH_PLANE_HEIGHT_M], c='purple', marker='s', s=100,
                              label='Predicted')

        self.ax_3d.set_xlabel('X (m)')
        self.ax_3d.set_ylabel('Y (m)')
        self.ax_3d.set_zlabel('Z (m)')
        self.ax_3d.set_xlim(-3, 3)
        self.ax_3d.set_ylim(-2, 2)
        self.ax_3d.set_zlim(0, 3.5)
        self.ax_3d.legend(loc='upper left', fontsize=8)
        self.ax_3d.view_init(elev=20, azim=45)

        # Title with stats
        title = f'3D View | Visible: {len(visible_points)}/{len(all_points)}'
        if prediction:
            error = calculate_prediction_error(prediction, throw.actual_landing)
            title += f' | Error: {error*100:.1f}cm'
        self.ax_3d.set_title(title, fontsize=10)

    def plot_2d(self, throw, visible_points, prediction):
        """Update 2D top-down plot."""
        self.ax_2d.clear()

        # FOV circles
        half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
        for h in [1.0, 1.5, 2.0, 2.5, 3.0]:
            radius = h * np.tan(half_angle)
            circle = plt.Circle((0, 0), radius, fill=False, color='gray',
                               alpha=0.2, linestyle='--', linewidth=1)
            self.ax_2d.add_patch(circle)

        # Trajectory
        all_points = throw.observed_points
        outside_fov = [p for p in all_points if not p.in_fov]
        inside_fov = [p for p in all_points if p.in_fov]

        if outside_fov:
            xs = [p.x_m for p in outside_fov]
            ys = [p.y_m for p in outside_fov]
            self.ax_2d.plot(xs, ys, 'r--', alpha=0.5, linewidth=2)

        if inside_fov:
            xs = [p.x_m for p in inside_fov]
            ys = [p.y_m for p in inside_fov]
            self.ax_2d.plot(xs, ys, 'g-', linewidth=2)

        # Markers
        self.ax_2d.scatter([0], [0], c='black', marker='^', s=100, zorder=5)
        self.ax_2d.scatter([throw.start_position[0]], [throw.start_position[1]],
                          c='blue', marker='o', s=100, zorder=5)
        self.ax_2d.scatter([throw.actual_landing[0]], [throw.actual_landing[1]],
                          c='orange', marker='*', s=200, zorder=5)

        if prediction:
            self.ax_2d.scatter([prediction.landing_x], [prediction.landing_y],
                              c='purple', marker='s', s=100, zorder=5)
            error = calculate_prediction_error(prediction, throw.actual_landing)
            self.ax_2d.set_title(f'Top-Down View | Prediction Error: {error*100:.1f}cm', fontsize=10)
        else:
            self.ax_2d.set_title('Top-Down View | Not enough visible frames', fontsize=10)

        self.ax_2d.set_xlabel('X (m)')
        self.ax_2d.set_ylabel('Y (m)')
        self.ax_2d.set_aspect('equal')
        self.ax_2d.grid(True, alpha=0.3)
        self.ax_2d.set_xlim(-3, 3)
        self.ax_2d.set_ylim(-2, 2)

    def reset(self, event):
        """Reset to default values."""
        self.slider_start_x.reset()
        self.slider_start_y.reset()
        self.slider_start_z.reset()
        self.slider_speed.reset()
        self.slider_angle_h.reset()
        self.slider_angle_v.reset()

    def preset_center_drop(self, event):
        """Preset: Center drop."""
        self.slider_start_x.set_val(0.0)
        self.slider_start_y.set_val(0.0)
        self.slider_start_z.set_val(2.5)
        self.slider_speed.set_val(1.0)
        self.slider_angle_h.set_val(0)
        self.slider_angle_v.set_val(0)

    def preset_side_arc(self, event):
        """Preset: Side arc."""
        self.slider_start_x.set_val(1.5)
        self.slider_start_y.set_val(0.5)
        self.slider_start_z.set_val(2.0)
        self.slider_speed.set_val(2.5)
        self.slider_angle_h.set_val(-120)
        self.slider_angle_v.set_val(30)

    def preset_fast_toss(self, event):
        """Preset: Fast toss."""
        self.slider_start_x.set_val(0.5)
        self.slider_start_y.set_val(-0.5)
        self.slider_start_z.set_val(1.5)
        self.slider_speed.set_val(5.0)
        self.slider_angle_h.set_val(45)
        self.slider_angle_v.set_val(70)

    def preset_fov_entry(self, event):
        """Preset: FOV entry scenario."""
        self.slider_start_x.set_val(2.5)
        self.slider_start_y.set_val(0.0)
        self.slider_start_z.set_val(1.5)
        self.slider_speed.set_val(4.24)  # Results in velocity (-3, 0, 3)
        self.slider_angle_h.set_val(180)
        self.slider_angle_v.set_val(45)

def main():
    print("="*70)
    print("INTERACTIVE TRASH-CATCHING SIMULATOR")
    print("="*70)
    print("\nControls:")
    print("  - Use sliders to adjust throw parameters")
    print("  - Start X/Y/Z: Starting position")
    print("  - Speed: Throw speed (m/s)")
    print("  - Horizontal Angle: Direction in XY plane (0° = +X axis)")
    print("  - Vertical Angle: Angle from horizontal (0° = horizontal, 90° = straight up)")
    print("\nPresets:")
    print("  - Center Drop: Simple drop from directly above camera")
    print("  - Side Arc: Arc from the side")
    print("  - Fast Toss: High-speed upward toss")
    print("  - FOV Entry: Object enters FOV mid-flight\n")

    simulator = InteractiveSimulator()
    plt.show()

    print("\nSimulation closed.")

if __name__ == "__main__":
    main()
