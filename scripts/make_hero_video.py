#!/usr/bin/env python3
"""
Hero video for the website.

Renders 3 throws cycling, dark theme, 16:9. Shows the trajectory forming,
the live prediction pulsing on the catch plane (radius ~ uncertainty),
the basket snapping to the actionable prediction, and the actual landing
revealed at impact with the error.

Outputs:
    hero_simulation.mp4  (1280x720, ~12-15s, H.264)
    hero_simulation.gif  (smaller, looping fallback)
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
from matplotlib.patches import Circle
from matplotlib import patheffects

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator import generate_throw, get_visible_points
from src.predictor import ContinuousPredictor, calculate_prediction_error
import config


# ---- Style ---------------------------------------------------------------

BG       = "#070b14"
PANEL    = "#0d1422"
GRID     = "#1d2840"
TEXT     = "#e6edf7"
DIM      = "#7d8aa3"
CYAN     = "#22d3ee"   # trajectory
MAGENTA  = "#e879f9"   # prediction
LIME     = "#a3e635"   # basket / actionable
AMBER    = "#fbbf24"   # actual landing
RED      = "#f87171"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor":   BG,
    "savefig.facecolor": BG,
    "axes.edgecolor":   GRID,
    "axes.labelcolor":  DIM,
    "xtick.color":      DIM,
    "ytick.color":      DIM,
    "text.color":       TEXT,
    "font.family":      "DejaVu Sans",
    "font.size":        9,
})


# ---- Throws --------------------------------------------------------------

THROWS = [
    dict(start=( 1.2,  0.8, 2.6), vel=(-1.6, -1.0, 1.4), label="THROW 01  ·  ARC TOSS"),
    dict(start=(-1.4, -0.6, 2.4), vel=( 1.8,  0.7, 0.9), label="THROW 02  ·  CROSS-COURT"),
    dict(start=( 0.0,  1.6, 3.0), vel=( 0.2, -1.5, 0.4), label="THROW 03  ·  HIGH DROP"),
]

PAUSE_FRAMES = 48      # post-impact hold per throw (verdict readable)
LIVE_FRAME_REPEAT = 2  # slow the live action by duplicating frames
PLAYBACK_FPS = 24      # cinematic pacing


def build_throw_data(seed: int, params: dict):
    np.random.seed(seed)
    throw = generate_throw(
        start_position=params["start"],
        start_velocity=params["vel"],
        add_measurement_noise=True,
        dropout_probability=0.0,
    )
    visible = get_visible_points(throw)

    predictor = ContinuousPredictor()
    predictions = []
    for p in throw.observed_points:
        if p.in_fov:
            pred = predictor.add_frame(p)
        else:
            pred = predictor.get_latest_prediction() if hasattr(predictor, "get_latest_prediction") else None
        predictions.append(pred)
    return throw, visible, predictions


# ---- Render --------------------------------------------------------------

def make_figure():
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor(BG)

    # 3D view on the left, top-down + stats on the right
    ax3d = fig.add_subplot(1, 2, 1, projection="3d")
    ax2d = fig.add_subplot(2, 2, 2)
    axhud = fig.add_subplot(2, 2, 4)

    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.06,
                        wspace=0.18, hspace=0.25)
    return fig, ax3d, ax2d, axhud


def style_3d(ax):
    ax.set_facecolor(BG)
    ax.set_xlim(-2.2, 2.2)
    ax.set_ylim(-2.2, 2.2)
    ax.set_zlim(0, 3.4)
    ax.set_box_aspect((1, 1, 0.85))
    ax.view_init(elev=18, azim=-58)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor(BG)
        axis.pane.set_edgecolor(GRID)
        axis.pane.set_alpha(0.6)
        axis.line.set_color(GRID)
    ax.tick_params(colors=DIM, labelsize=7, pad=-2)
    ax.set_xlabel("X (m)", color=DIM, labelpad=-6, fontsize=8)
    ax.set_ylabel("Y (m)", color=DIM, labelpad=-6, fontsize=8)
    ax.set_zlabel("Z (m)", color=DIM, labelpad=-6, fontsize=8)
    ax.grid(False)


def style_2d(ax):
    ax.set_facecolor(PANEL)
    ax.set_xlim(-2.2, 2.2)
    ax.set_ylim(-2.2, 2.2)
    ax.set_aspect("equal")
    ax.tick_params(colors=DIM, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)
    ax.set_title("CATCH PLANE  ·  TOP-DOWN", color=TEXT,
                 fontsize=9, pad=6, weight="bold", loc="left")


def style_hud(ax):
    ax.set_facecolor(PANEL)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.set_title("PREDICTOR TELEMETRY", color=TEXT,
                 fontsize=9, pad=6, weight="bold", loc="left")


def draw_static_3d(ax):
    # Camera marker
    ax.scatter([0], [0], [0], c=CYAN, marker="^", s=140,
               edgecolors=TEXT, linewidths=1.0, zorder=10)
    ax.text(0, 0, -0.25, "CAMERA", color=DIM, fontsize=7, ha="center")

    # FOV cone wireframe
    half = np.radians(config.CAMERA_FOV_DEGREES / 2)
    z = np.linspace(0.05, 3.2, 14)
    th = np.linspace(0, 2 * np.pi, 28)
    Z, T = np.meshgrid(z, th)
    R = Z * np.tan(half)
    ax.plot_wireframe(R * np.cos(T), R * np.sin(T), Z,
                      color=CYAN, alpha=0.08, linewidth=0.5)

    # Catch plane
    cz = config.CATCH_PLANE_HEIGHT_M
    side = np.linspace(-2.2, 2.2, 2)
    XX, YY = np.meshgrid(side, side)
    ax.plot_surface(XX, YY, np.full_like(XX, cz),
                    color=MAGENTA, alpha=0.04, edgecolor="none")
    # Plane outline
    edge = 2.2
    ax.plot([-edge, edge, edge, -edge, -edge],
            [-edge, -edge, edge, edge, -edge],
            [cz] * 5, color=MAGENTA, alpha=0.35, linewidth=0.8)


def draw_static_2d(ax):
    half = np.radians(config.CAMERA_FOV_DEGREES / 2)
    for h in (1.0, 2.0, 3.0):
        r = h * np.tan(half)
        ax.add_patch(Circle((0, 0), r, fill=False,
                            color=CYAN, alpha=0.18, linestyle="--", lw=0.7))
    ax.scatter([0], [0], c=CYAN, marker="^", s=110,
               edgecolors=TEXT, linewidths=1, zorder=5)


def render_video(out_mp4="hero_simulation.mp4", out_gif="hero_simulation.gif",
                 also_gif=True):
    print("Building throw data...")
    seeds = [101, 202, 303]
    throws = [build_throw_data(s, p) for s, p in zip(seeds, THROWS)]

    # Build a flat timeline: for each throw, a list of "scene frames"
    timeline = []  # (throw_idx, point_idx_or_None, prediction_or_None, phase)
    for ti, (throw, _vis, preds) in enumerate(throws):
        for pi, pred in enumerate(preds):
            for _ in range(LIVE_FRAME_REPEAT):
                timeline.append((ti, pi, pred, "live"))
        for _ in range(PAUSE_FRAMES):
            timeline.append((ti, len(throw.observed_points) - 1,
                             preds[-1] if preds else None, "hold"))

    fig, ax3d, ax2d, axhud = make_figure()

    # Title bar
    title = fig.text(0.5, 0.96, "T R A S H   C A T C H E R   ·   L I V E   T R A J E C T O R Y   P R E D I C T I O N",
                     ha="center", color=TEXT, fontsize=13, weight="bold")
    subtitle = fig.text(0.5, 0.93, "physics-based · 30 FPS · refined every frame",
                        ha="center", color=DIM, fontsize=9)

    style_3d(ax3d); style_2d(ax2d); style_hud(axhud)
    draw_static_3d(ax3d); draw_static_2d(ax2d)

    # Mutable artists per render
    artists = {}

    def reset_axes_for_throw():
        # Clear everything but the static layer by re-drawing
        ax3d.cla(); ax2d.cla(); axhud.cla()
        style_3d(ax3d); style_2d(ax2d); style_hud(axhud)
        draw_static_3d(ax3d); draw_static_2d(ax2d)

    def draw_frame(state):
        ti, pi, pred, phase = state
        throw, _vis, preds = throws[ti]

        reset_axes_for_throw()

        params = THROWS[ti]
        fig.suptitle("")  # avoid duplication

        # Throw label (top-left of 3d panel)
        ax3d.text2D(0.02, 0.95, params["label"], transform=ax3d.transAxes,
                    color=CYAN, fontsize=10, weight="bold",
                    path_effects=[patheffects.withStroke(linewidth=2, foreground=BG)])

        # Trajectory so far
        seen = throw.observed_points[: pi + 1]
        visible_seen = [p for p in seen if p.in_fov]
        if visible_seen:
            xs = np.array([p.x_m for p in visible_seen])
            ys = np.array([p.y_m for p in visible_seen])
            zs = np.array([p.z_m for p in visible_seen])

            # 3D trail with fading alpha
            for i in range(1, len(xs)):
                a = 0.15 + 0.85 * (i / len(xs))
                ax3d.plot(xs[i-1:i+1], ys[i-1:i+1], zs[i-1:i+1],
                          color=CYAN, alpha=a, linewidth=2.2)
            ax3d.scatter(xs, ys, zs, c=CYAN, s=14, alpha=0.6, edgecolors="none")

            # Current head
            ax3d.scatter([xs[-1]], [ys[-1]], [zs[-1]],
                         c=TEXT, s=90, edgecolors=CYAN, linewidths=1.6, zorder=20)

            # 2D trail
            ax2d.plot(xs, ys, color=CYAN, alpha=0.6, linewidth=1.6)
            ax2d.scatter([xs[-1]], [ys[-1]], c=TEXT, s=70,
                         edgecolors=CYAN, linewidths=1.4, zorder=8)

        # Prediction marker (live)
        confidence = pred.confidence if pred else 0.0
        actionable = bool(pred and pred.is_actionable(min_confidence=0.6))
        cz = config.CATCH_PLANE_HEIGHT_M

        if pred:
            px, py = pred.landing_x, pred.landing_y
            # Uncertainty radius shrinks with confidence
            r = max(0.06, 0.6 * (1.0 - confidence))
            color = LIME if actionable else MAGENTA

            # 3D pulse ring
            theta = np.linspace(0, 2*np.pi, 60)
            ax3d.plot(px + r*np.cos(theta), py + r*np.sin(theta),
                      np.full_like(theta, cz), color=color, linewidth=2, alpha=0.9)
            ax3d.scatter([px], [py], [cz], c=color, s=80, edgecolors=TEXT,
                         linewidths=1, zorder=15)

            # 2D pulse ring + crosshair
            ax2d.add_patch(Circle((px, py), r, fill=False, color=color,
                                  linewidth=2, alpha=0.9))
            ax2d.add_patch(Circle((px, py), max(0.02, r*0.25), fill=True,
                                  color=color, alpha=0.85))
            ax2d.plot([px-0.15, px+0.15], [py, py], color=color, lw=1, alpha=0.7)
            ax2d.plot([px, px], [py-0.15, py+0.15], color=color, lw=1, alpha=0.7)

            if actionable:
                # Basket icon at predicted spot
                ax2d.scatter([px], [py], marker="s", s=260, facecolors="none",
                             edgecolors=LIME, linewidths=1.6, alpha=0.9, zorder=9)

        # Reveal actual landing during hold
        actual_x, actual_y = throw.actual_landing
        if phase == "hold":
            ax3d.scatter([actual_x], [actual_y], [cz], c=AMBER, marker="*",
                         s=260, edgecolors=TEXT, linewidths=0.8, zorder=18)
            ax2d.scatter([actual_x], [actual_y], c=AMBER, marker="*",
                         s=260, edgecolors=TEXT, linewidths=0.8, zorder=10)
            # Connect prediction to actual
            if pred:
                ax2d.plot([pred.landing_x, actual_x],
                          [pred.landing_y, actual_y],
                          color=AMBER, linewidth=1.2, alpha=0.7, linestyle=":")

        # ---- HUD telemetry ----
        frame_n = pi + 1
        total_n = len(throw.observed_points)
        seen_n = len([p for p in seen if p.in_fov])

        if pred:
            err_cm = calculate_prediction_error(pred, throw.actual_landing) * 100
            ttl_ms = pred.time_to_landing * 1000
            err_text = f"{err_cm:5.1f} cm"
            conf_text = f"{confidence*100:4.0f}%"
            status = "ACTIONABLE" if actionable else "REFINING..."
            status_color = LIME if actionable else MAGENTA
        else:
            err_text = "  --  "
            conf_text = "  -- "
            ttl_ms = 0.0
            status = "AWAITING DATA"
            status_color = DIM

        rows = [
            ("FRAME",        f"{frame_n:02d} / {total_n:02d}",   TEXT),
            ("VISIBLE",      f"{seen_n:02d} frames",             TEXT),
            ("CONFIDENCE",   conf_text,                          status_color),
            ("PRED ERROR",   err_text,                           AMBER if phase == "hold" else status_color),
            ("TIME-TO-CATCH",f"{ttl_ms:5.0f} ms",                TEXT),
            ("STATUS",       status,                             status_color),
        ]
        for i, (label, value, color) in enumerate(rows):
            y = 0.86 - i * 0.135
            axhud.text(0.06, y, label, color=DIM, fontsize=8.5,
                       weight="bold")
            axhud.text(0.96, y, value, color=color, fontsize=12.5,
                       weight="bold", ha="right", family="monospace")

        # Big phase pill at the bottom of HUD
        if phase == "hold" and pred:
            err_cm = calculate_prediction_error(pred, throw.actual_landing) * 100
            verdict = "✓ CAUGHT" if err_cm < 10 else "✗ MISS"
            vcolor = LIME if err_cm < 10 else RED
            axhud.text(0.5, 0.04, verdict, color=vcolor, fontsize=14,
                       weight="bold", ha="center",
                       bbox=dict(boxstyle="round,pad=0.4",
                                 facecolor=BG, edgecolor=vcolor, linewidth=1.5))

    def init():
        draw_frame(timeline[0])
        return []

    def update(i):
        draw_frame(timeline[i])
        return []

    print(f"Total frames: {len(timeline)}  (~{len(timeline)/PLAYBACK_FPS:.1f}s at {PLAYBACK_FPS}fps)")

    anim = FuncAnimation(fig, update, init_func=init,
                         frames=len(timeline), interval=1000/PLAYBACK_FPS, blit=False)

    print(f"Encoding MP4 → {out_mp4}")
    writer = FFMpegWriter(fps=PLAYBACK_FPS, bitrate=5000,
                          codec="libx264",
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "medium",
                                      "-movflags", "+faststart"])
    anim.save(out_mp4, writer=writer, dpi=100)
    print(f"  saved: {os.path.getsize(out_mp4)/1024:.0f} KB")

    if also_gif:
        print(f"Encoding GIF → {out_gif} (subsampled)")
        anim_gif = FuncAnimation(fig, update, init_func=init,
                                 frames=range(0, len(timeline), 2),
                                 interval=1000/12, blit=False)
        anim_gif.save(out_gif, writer=PillowWriter(fps=12), dpi=72)
        print(f"  saved: {os.path.getsize(out_gif)/1024:.0f} KB")

    plt.close(fig)
    print("Done.")


if __name__ == "__main__":
    render_video()
