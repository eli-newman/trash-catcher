#!/usr/bin/env python3
"""
Clean, simple FOV-focused simulator.
Adjust throw path with sliders, see what's visible in FOV.
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from mpl_toolkits.mplot3d import Axes3D

from src.simulator import generate_throw, get_visible_points
from src.predictor import predict_landing, calculate_prediction_error
import config


class CleanSimulator:
    def __init__(self):
        self.fig = plt.figure(figsize=(15, 7))

        # 3D plot - focus on FOV
        self.ax_3d = self.fig.add_subplot(121, projection='3d')

        # Top-down plot - show FOV circle
        self.ax_2d = self.fig.add_subplot(122)

        # Default params
        self.start_x = 1.5
        self.start_y = 0.0
        self.start_z = 2.5
        self.speed = 3.0
        self.angle_h = -90  # toward camera
        self.angle_v = 45   # upward

        self._setup_controls()
        self._update()

    def _setup_controls(self):
        """Create sliders."""
        self.fig.subplots_adjust(bottom=0.25)

        # Position sliders
        ax_x = self.fig.add_axes([0.15, 0.15, 0.25, 0.02])
        self.s_x = Slider(ax_x, 'X', -3, 3, valinit=self.start_x)

        ax_y = self.fig.add_axes([0.15, 0.12, 0.25, 0.02])
        self.s_y = Slider(ax_y, 'Y', -3, 3, valinit=self.start_y)

        ax_z = self.fig.add_axes([0.15, 0.09, 0.25, 0.02])
        self.s_z = Slider(ax_z, 'Z', 0.5, 4, valinit=self.start_z)

        # Throw params
        ax_speed = self.fig.add_axes([0.15, 0.05, 0.25, 0.02])
        self.s_speed = Slider(ax_speed, 'Speed', 0.5, 6, valinit=self.speed)

        ax_ah = self.fig.add_axes([0.6, 0.15, 0.25, 0.02])
        self.s_ah = Slider(ax_ah, 'Direction', -180, 180, valinit=self.angle_h)

        ax_av = self.fig.add_axes([0.6, 0.12, 0.25, 0.02])
        self.s_av = Slider(ax_av, 'Up Angle', -30, 90, valinit=self.angle_v)

        # Buttons
        ax_preset1 = self.fig.add_axes([0.6, 0.06, 0.08, 0.03])
        self.btn1 = Button(ax_preset1, 'Center')

        ax_preset2 = self.fig.add_axes([0.69, 0.06, 0.08, 0.03])
        self.btn2 = Button(ax_preset2, 'Side')

        ax_preset3 = self.fig.add_axes([0.78, 0.06, 0.08, 0.03])
        self.btn3 = Button(ax_preset3, 'FOV Entry')

        # Connect
        self.s_x.on_changed(lambda v: self._update())
        self.s_y.on_changed(lambda v: self._update())
        self.s_z.on_changed(lambda v: self._update())
        self.s_speed.on_changed(lambda v: self._update())
        self.s_ah.on_changed(lambda v: self._update())
        self.s_av.on_changed(lambda v: self._update())
        self.btn1.on_clicked(lambda e: self._preset(0, 0, 2.5, 1.5, 0, 10))
        self.btn2.on_clicked(lambda e: self._preset(1.5, 0.5, 2, 3, -120, 40))
        self.btn3.on_clicked(lambda e: self._preset(3, 0, 3.5, 4, 180, 30))

    def _preset(self, x, y, z, speed, ah, av):
        """Load preset."""
        self.s_x.set_val(x)
        self.s_y.set_val(y)
        self.s_z.set_val(z)
        self.s_speed.set_val(speed)
        self.s_ah.set_val(ah)
        self.s_av.set_val(av)

    def _get_velocity(self):
        """Convert to velocity vector."""
        s = self.s_speed.val
        h = np.radians(self.s_ah.val)
        v = np.radians(self.s_av.val)
        return (s * np.cos(v) * np.cos(h),
                s * np.cos(v) * np.sin(h),
                s * np.sin(v))

    def _update(self):
        """Regenerate and replot."""
        pos = (self.s_x.val, self.s_y.val, self.s_z.val)
        vel = self._get_velocity()

        try:
            throw = generate_throw(pos, vel, add_measurement_noise=False, dropout_probability=0)
            visible = get_visible_points(throw)
            pred = predict_landing(visible) if len(visible) >= 5 else None

            self._plot_3d(throw, visible, pred)
            self._plot_2d(throw, visible, pred)
            self.fig.canvas.draw_idle()
        except:
            pass

    def _plot_3d(self, throw, visible, pred):
        """3D view with FOV cone."""
        self.ax_3d.clear()

        # FOV cone (wireframe)
        half = np.radians(config.CAMERA_FOV_DEGREES / 2)
        h = np.linspace(0.1, 4, 10)
        theta = np.linspace(0, 2*np.pi, 20)
        H, T = np.meshgrid(h, theta)
        R = H * np.tan(half)
        X = R * np.cos(T)
        Y = R * np.sin(T)
        self.ax_3d.plot_wireframe(X, Y, H, color='lightblue', alpha=0.15, linewidth=0.5)

        # Trajectory - split by FOV
        all_pts = throw.observed_points
        out_fov = [p for p in all_pts if not p.in_fov]
        in_fov = [p for p in all_pts if p.in_fov]

        if out_fov:
            self.ax_3d.plot([p.x_m for p in out_fov],
                          [p.y_m for p in out_fov],
                          [p.z_m for p in out_fov],
                          'r-', linewidth=3, alpha=0.4, label='Outside FOV')

        if in_fov:
            self.ax_3d.plot([p.x_m for p in in_fov],
                          [p.y_m for p in in_fov],
                          [p.z_m for p in in_fov],
                          'g-', linewidth=3, label='Inside FOV')

        # Catch plane
        catch = config.CATCH_PLANE_HEIGHT_M
        self.ax_3d.plot([-2, 2, 2, -2, -2],
                       [-2, -2, 2, 2, -2],
                       [catch]*5, 'k-', linewidth=2, alpha=0.3)

        # Markers
        self.ax_3d.scatter([0], [0], [0], c='black', s=100, marker='^', label='Camera')
        self.ax_3d.scatter([throw.actual_landing[0]], [throw.actual_landing[1]],
                          [catch], c='orange', s=200, marker='*', label='Actual')

        if pred:
            err = calculate_prediction_error(pred, throw.actual_landing)
            self.ax_3d.scatter([pred.landing_x], [pred.landing_y],
                             [catch], c='lime', s=150, marker='X', label='Predicted')

            # Error line
            self.ax_3d.plot([throw.actual_landing[0], pred.landing_x],
                          [throw.actual_landing[1], pred.landing_y],
                          [catch, catch], 'r--', linewidth=2, alpha=0.7)

            title = f'Visible: {len(in_fov)}/{len(all_pts)} frames | Error: {err*100:.1f}cm'
        else:
            title = f'Visible: {len(in_fov)}/{len(all_pts)} frames | Need 5+ for prediction'

        self.ax_3d.set_xlabel('X (m)')
        self.ax_3d.set_ylabel('Y (m)')
        self.ax_3d.set_zlabel('Z (m)')
        self.ax_3d.set_xlim(-3, 3)
        self.ax_3d.set_ylim(-3, 3)
        self.ax_3d.set_zlim(0, 4)
        self.ax_3d.legend(loc='upper left', fontsize=9)
        self.ax_3d.set_title(title, fontsize=11, fontweight='bold')
        self.ax_3d.view_init(elev=25, azim=45)

    def _plot_2d(self, throw, visible, pred):
        """Top-down view with FOV circles."""
        self.ax_2d.clear()

        # FOV circles at different heights
        half = np.radians(config.CAMERA_FOV_DEGREES / 2)
        for h in [1, 2, 3, 4]:
            r = h * np.tan(half)
            c = plt.Circle((0, 0), r, fill=False, color='lightblue',
                          alpha=0.3, linestyle='--', linewidth=1)
            self.ax_2d.add_patch(c)
            self.ax_2d.text(0, r+0.1, f'z={h}m', ha='center', fontsize=8, alpha=0.5)

        # Trajectory
        all_pts = throw.observed_points
        out_fov = [p for p in all_pts if not p.in_fov]
        in_fov = [p for p in all_pts if p.in_fov]

        if out_fov:
            self.ax_2d.plot([p.x_m for p in out_fov], [p.y_m for p in out_fov],
                          'r-', linewidth=3, alpha=0.4)

        if in_fov:
            self.ax_2d.plot([p.x_m for p in in_fov], [p.y_m for p in in_fov],
                          'g-', linewidth=3)

        # Markers
        self.ax_2d.scatter([0], [0], c='black', s=100, marker='^', zorder=5)
        self.ax_2d.scatter([throw.actual_landing[0]], [throw.actual_landing[1]],
                         c='orange', s=200, marker='*', zorder=5)

        if pred:
            self.ax_2d.scatter([pred.landing_x], [pred.landing_y],
                             c='lime', s=150, marker='X', zorder=5)
            err = calculate_prediction_error(pred, throw.actual_landing)
            title = f'FOV at Catch Plane | Error: {err*100:.1f}cm'
        else:
            title = 'FOV at Catch Plane | No prediction yet'

        self.ax_2d.set_xlabel('X (m)')
        self.ax_2d.set_ylabel('Y (m)')
        self.ax_2d.set_title(title, fontsize=11, fontweight='bold')
        self.ax_2d.set_aspect('equal')
        self.ax_2d.grid(True, alpha=0.2)
        self.ax_2d.set_xlim(-3, 3)
        self.ax_2d.set_ylim(-3, 3)

    def run(self):
        plt.show()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("CLEAN FOV SIMULATOR")
    print("="*70)
    print("\nSliders:")
    print("  X, Y, Z     - Start position")
    print("  Speed       - Throw speed")
    print("  Direction   - Horizontal angle (0° = +X axis)")
    print("  Up Angle    - Vertical angle (0° = horizontal)")
    print("\nColors:")
    print("  RED trajectory   = Outside FOV (camera can't see)")
    print("  GREEN trajectory = Inside FOV (camera sees)")
    print("  Orange star      = Actual landing")
    print("  Lime X           = Predicted landing")
    print("\nFOV = Field of View = Camera's vision cone")
    print("Blue wireframe cone = What camera can see")
    print("Blue circles (top-down) = FOV at different heights")
    print("\nPresets:")
    print("  Center    - Simple drop")
    print("  Side      - Throw from side")
    print("  FOV Entry - Starts OUTSIDE fov, enters mid-flight!")
    print()

    sim = CleanSimulator()
    sim.run()
