"""
Simple live simulation with slider controls - just like the original interactive sim.

Adjust throw parameters in real-time and watch the prediction.
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D

from src.simulator import generate_throw, get_visible_points
from src.predictor import ContinuousPredictor, calculate_prediction_error
import config


class SimpleInteractiveSim:
    """Simple interactive simulation with sliders."""

    def __init__(self):
        # Default parameters
        self.start_x = 1.0
        self.start_y = 0.5
        self.start_z = 2.5
        self.vel_x = -0.5
        self.vel_y = 0.3
        self.vel_z = 1.0
        self.seed = 42

        self.throw = None
        self.predictor = None
        self.frame_idx = 0
        self.playing = False
        self.anim = None

        self._setup_ui()
        self._generate_throw()

    def _setup_ui(self):
        """Setup matplotlib UI with sliders."""
        self.fig = plt.figure(figsize=(14, 8))

        # 3D plot
        self.ax_3d = self.fig.add_subplot(121, projection='3d')

        # Top-down plot
        self.ax_top = self.fig.add_subplot(122)

        # Sliders
        slider_left = 0.15
        slider_width = 0.3
        slider_height = 0.03
        slider_spacing = 0.04

        bottom = 0.05

        # Position sliders
        self.slider_x = Slider(
            plt.axes([slider_left, bottom + slider_spacing * 5, slider_width, slider_height]),
            'Start X', -2.0, 2.0, valinit=self.start_x
        )
        self.slider_y = Slider(
            plt.axes([slider_left, bottom + slider_spacing * 4, slider_width, slider_height]),
            'Start Y', -2.0, 2.0, valinit=self.start_y
        )
        self.slider_z = Slider(
            plt.axes([slider_left, bottom + slider_spacing * 3, slider_width, slider_height]),
            'Start Z', 1.0, 4.0, valinit=self.start_z
        )

        # Velocity sliders
        self.slider_vx = Slider(
            plt.axes([slider_left, bottom + slider_spacing * 2, slider_width, slider_height]),
            'Velocity X', -3.0, 3.0, valinit=self.vel_x
        )
        self.slider_vy = Slider(
            plt.axes([slider_left, bottom + slider_spacing * 1, slider_width, slider_height]),
            'Velocity Y', -3.0, 3.0, valinit=self.vel_y
        )
        self.slider_vz = Slider(
            plt.axes([slider_left, bottom + slider_spacing * 0, slider_width, slider_height]),
            'Velocity Z', -2.0, 3.0, valinit=self.vel_z
        )

        # Buttons
        self.btn_play = Button(plt.axes([0.55, 0.05, 0.1, 0.04]), 'Play')
        self.btn_reset = Button(plt.axes([0.66, 0.05, 0.1, 0.04]), 'Reset')
        self.btn_regen = Button(plt.axes([0.77, 0.05, 0.1, 0.04]), 'New Throw')

        # Connect events
        self.slider_x.on_changed(self._on_slider_change)
        self.slider_y.on_changed(self._on_slider_change)
        self.slider_z.on_changed(self._on_slider_change)
        self.slider_vx.on_changed(self._on_slider_change)
        self.slider_vy.on_changed(self._on_slider_change)
        self.slider_vz.on_changed(self._on_slider_change)

        self.btn_play.on_clicked(self._on_play)
        self.btn_reset.on_clicked(self._on_reset)
        self.btn_regen.on_clicked(self._on_regen)

    def _on_slider_change(self, val):
        """Handle slider changes."""
        self.start_x = self.slider_x.val
        self.start_y = self.slider_y.val
        self.start_z = self.slider_z.val
        self.vel_x = self.slider_vx.val
        self.vel_y = self.slider_vy.val
        self.vel_z = self.slider_vz.val

        self._generate_throw()
        self.frame_idx = 0
        self._update_plot()

    def _on_play(self, event):
        """Toggle play/pause."""
        self.playing = not self.playing
        if self.playing:
            self.btn_play.label.set_text('Pause')
            if self.anim is None:
                self.anim = FuncAnimation(self.fig, self._animate, interval=100, repeat=True)
        else:
            self.btn_play.label.set_text('Play')

    def _on_reset(self, event):
        """Reset to frame 0."""
        self.frame_idx = 0
        self._update_plot()

    def _on_regen(self, event):
        """Generate new random throw with current parameters."""
        self.seed += 1
        self._generate_throw()
        self.frame_idx = 0
        self._update_plot()

    def _generate_throw(self):
        """Generate throw with current parameters."""
        np.random.seed(self.seed)
        self.throw = generate_throw(
            start_position=(self.start_x, self.start_y, self.start_z),
            start_velocity=(self.vel_x, self.vel_y, self.vel_z),
            add_measurement_noise=True,
            dropout_probability=0.05
        )
        self.visible_points = get_visible_points(self.throw)
        self.predictor = ContinuousPredictor()

    def _animate(self, frame):
        """Animation update."""
        if not self.playing:
            return

        if self.frame_idx < len(self.visible_points):
            self.frame_idx += 1
            self._update_plot()
        else:
            self.playing = False
            self.btn_play.label.set_text('Play')
            self.frame_idx = 0

    def _update_plot(self):
        """Update plots with current frame."""
        # Clear
        self.ax_3d.clear()
        self.ax_top.clear()

        # Setup 3D view
        self.ax_3d.set_xlabel('X (m)')
        self.ax_3d.set_ylabel('Y (m)')
        self.ax_3d.set_zlabel('Z (m)')
        self.ax_3d.set_title('3D View')
        self.ax_3d.set_xlim([-2, 2])
        self.ax_3d.set_ylim([-2, 2])
        self.ax_3d.set_zlim([0, 4])

        # Draw FOV cone
        half_angle = np.radians(config.CAMERA_FOV_DEGREES / 2)
        theta = np.linspace(0, 2*np.pi, 30)
        for zi in [3.0]:
            r = zi * np.tan(half_angle)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            self.ax_3d.plot(x, y, [zi]*len(theta), 'b--', alpha=0.2)

        # Draw catch plane
        catch_h = config.CATCH_PLANE_HEIGHT_M
        x_plane = [-1.5, 1.5, 1.5, -1.5, -1.5]
        y_plane = [-1.5, -1.5, 1.5, 1.5, -1.5]
        self.ax_3d.plot(x_plane, y_plane, [catch_h]*5, 'g-', linewidth=2, alpha=0.5)

        # Plot trajectory up to current frame
        if self.frame_idx > 0:
            points = self.visible_points[:self.frame_idx]
            xs = [p.x_m for p in points]
            ys = [p.y_m for p in points]
            zs = [p.z_m for p in points]
            self.ax_3d.plot(xs, ys, zs, 'b-', linewidth=2, alpha=0.6)
            self.ax_3d.scatter(xs[-1:], ys[-1:], zs[-1:], c='cyan', s=100, marker='o')

            # Get prediction
            for point in points:
                pred = self.predictor.add_frame(point)

            if pred:
                error = calculate_prediction_error(pred, self.throw.actual_landing)

                # Show prediction
                color = 'red' if pred.is_actionable(0.7) else 'orange'
                self.ax_3d.scatter(
                    [pred.landing_x], [pred.landing_y], [catch_h],
                    c=color, s=200, marker='x', linewidths=3
                )

                # Error line
                self.ax_3d.plot(
                    [self.throw.actual_landing[0], pred.landing_x],
                    [self.throw.actual_landing[1], pred.landing_y],
                    [catch_h, catch_h], 'r--', linewidth=2
                )

                # Show info
                status = 'ACTIONABLE' if pred.is_actionable(0.7) else 'WAIT'
                self.ax_3d.text2D(0.05, 0.95,
                    f'Frame: {self.frame_idx}/{len(self.visible_points)}\n'
                    f'Error: {error*100:.1f} cm\n'
                    f'Confidence: {pred.confidence:.2f}\n'
                    f'Status: {status}',
                    transform=self.ax_3d.transAxes,
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
                )

        # Show actual landing
        self.ax_3d.scatter(
            [self.throw.actual_landing[0]],
            [self.throw.actual_landing[1]],
            [catch_h], c='green', s=200, marker='*'
        )

        # Top-down view
        self.ax_top.set_xlabel('X (m)')
        self.ax_top.set_ylabel('Y (m)')
        self.ax_top.set_title('Top-Down View')
        self.ax_top.set_xlim([-1.5, 1.5])
        self.ax_top.set_ylim([-1.5, 1.5])
        self.ax_top.set_aspect('equal')
        self.ax_top.grid(True, alpha=0.3)

        # FOV circle
        r_fov = catch_h * np.tan(half_angle)
        circle = plt.Circle((0, 0), r_fov, color='blue', fill=False, linestyle='--', alpha=0.3)
        self.ax_top.add_patch(circle)

        # Trajectory
        if self.frame_idx > 0:
            points = self.visible_points[:self.frame_idx]
            xs = [p.x_m for p in points]
            ys = [p.y_m for p in points]
            self.ax_top.plot(xs, ys, 'b-', linewidth=2)
            self.ax_top.scatter(xs[-1:], ys[-1:], c='cyan', s=100)

            if pred:
                self.ax_top.scatter([pred.landing_x], [pred.landing_y],
                                  c=color, s=200, marker='x', linewidths=3)

        # Actual landing
        self.ax_top.scatter(
            [self.throw.actual_landing[0]],
            [self.throw.actual_landing[1]],
            c='green', s=200, marker='*'
        )

        plt.draw()

    def run(self):
        """Show the UI."""
        self._update_plot()
        plt.show()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SIMPLE LIVE SIMULATION")
    print("="*70)
    print("\nControls:")
    print("  • Adjust sliders to change throw parameters")
    print("  • Click 'Play' to watch frame-by-frame")
    print("  • Click 'Reset' to go back to frame 0")
    print("  • Click 'New Throw' to regenerate with random noise")
    print("\nVisualization:")
    print("  • Blue line: Trajectory so far")
    print("  • Cyan dot: Current frame")
    print("  • Green star: Actual landing")
    print("  • Red/Orange X: Predicted landing")
    print("  • Red = High confidence (servo moves)")
    print("  • Orange = Low confidence (servo waits)")
    print()

    sim = SimpleInteractiveSim()
    sim.run()
