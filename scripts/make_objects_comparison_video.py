#!/usr/bin/env python3
"""
Hero video — one object at a time, same throw conditions.

Each object gets its own scene: trajectory unfolds live, predictor's guess
shrinks toward the actual landing, verdict appears. The leaderboard on the
right fills in cumulatively — by the end you see how each object scored.

Paper sheet (A4 flat) is intentionally faded: it's the "expected fail"
that exposes the vacuum-physics predictor's inability to handle drag-
dominated trajectories.

Outputs:
    objects_comparison.mp4   (1280x720, ~17s, H.264)
    objects_comparison.gif   (smaller looping fallback)
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
from matplotlib.patches import Circle

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator_drag import generate_throw_with_drag, terminal_velocity
from src.predictor import ContinuousPredictor, calculate_prediction_error
from src.objects import OBJECT_LIBRARY
import config


# ---- Style ---------------------------------------------------------------

BG       = "#070b14"
PANEL    = "#0d1422"
GRID     = "#1d2840"
TEXT     = "#e6edf7"
DIM      = "#7d8aa3"
LIME     = "#a3e635"
AMBER    = "#fbbf24"
RED      = "#f87171"
CYAN     = "#22d3ee"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "axes.edgecolor": GRID, "axes.labelcolor": DIM,
    "xtick.color": DIM, "ytick.color": DIM, "text.color": TEXT,
    "font.family": "DejaVu Sans", "font.size": 9,
})


# ---- Scene ---------------------------------------------------------------

START_POS = (1.0, 0.6, 2.6)
START_VEL = (-1.5, -0.9, 1.0)

# Order matters: ballistic → leaf-like (saves the dramatic miss for last)
SELECTED = [
    "soda_can_full",
    "tennis_ball",
    "beer_can_empty",
    "paper_ball_crumpled",
    "banana_peel",
    "paper_sheet_flat",   # expected miss — rendered faded
]

FADED_OBJECTS = {"paper_sheet_flat"}

TARGET_LIVE_FRAMES = 48     # ~2.0s at 24fps per object live phase
HOLD_FRAMES = 30            # 1.25s post-impact hold per object
PLAYBACK_FPS = 24
SEED = 4242


# ---- Sim -----------------------------------------------------------------

def simulate(obj_key):
    np.random.seed(SEED)
    obj = OBJECT_LIBRARY[obj_key]
    try:
        throw = generate_throw_with_drag(
            obj=obj,
            start_position=START_POS,
            start_velocity=START_VEL,
            add_measurement_noise=True,
            dropout_probability=0.0,
        )
    except ValueError as e:
        print(f"  ! {obj.name}: {e}")
        return None

    predictor = ContinuousPredictor()
    preds = []
    last_good = None
    for p in throw.observed_points:
        pred = predictor.add_frame(p) if p.in_fov else predictor._latest_prediction
        if pred is not None:
            last_good = pred
        preds.append(pred if pred is not None else last_good)
    return obj, throw, preds


# ---- Plot helpers --------------------------------------------------------

def style_3d(ax):
    ax.set_facecolor(BG)
    ax.set_xlim(-2.4, 2.4); ax.set_ylim(-2.4, 2.4); ax.set_zlim(0, 3.4)
    ax.set_box_aspect((1, 1, 0.85))
    ax.view_init(elev=18, azim=-58)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor(BG); axis.pane.set_edgecolor(GRID)
        axis.pane.set_alpha(0.6); axis.line.set_color(GRID)
    ax.tick_params(colors=DIM, labelsize=7, pad=-2)
    ax.set_xlabel("X (m)", color=DIM, labelpad=-6, fontsize=8)
    ax.set_ylabel("Y (m)", color=DIM, labelpad=-6, fontsize=8)
    ax.set_zlabel("Z (m)", color=DIM, labelpad=-6, fontsize=8)
    ax.grid(False)


def style_2d(ax):
    ax.set_facecolor(PANEL)
    ax.set_xlim(-2.4, 2.4); ax.set_ylim(-2.4, 2.4); ax.set_aspect("equal")
    ax.tick_params(colors=DIM, labelsize=7)
    for s in ax.spines.values(): s.set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)
    ax.set_title("CATCH PLANE  ·  TOP-DOWN", color=TEXT,
                 fontsize=9, pad=6, weight="bold", loc="left")


def style_hud(ax):
    ax.set_facecolor(PANEL)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color(GRID)
    ax.set_title("LEADERBOARD  ·  PREDICTOR vs DRAG-AWARE PHYSICS",
                 color=TEXT, fontsize=9, pad=6, weight="bold", loc="left")


def draw_static_3d(ax):
    ax.scatter([0], [0], [0], c=CYAN, marker="^", s=140,
               edgecolors=TEXT, linewidths=1.0, zorder=10)
    ax.text(0, 0, -0.25, "CAMERA", color=DIM, fontsize=7, ha="center")
    half = np.radians(config.CAMERA_FOV_DEGREES / 2)
    z = np.linspace(0.05, 3.2, 14); th = np.linspace(0, 2*np.pi, 28)
    Z, T = np.meshgrid(z, th); R = Z * np.tan(half)
    ax.plot_wireframe(R*np.cos(T), R*np.sin(T), Z,
                      color=CYAN, alpha=0.07, linewidth=0.5)
    cz = config.CATCH_PLANE_HEIGHT_M
    edge = 2.4
    ax.plot([-edge, edge, edge, -edge, -edge],
            [-edge, -edge, edge, edge, -edge],
            [cz]*5, color=CYAN, alpha=0.25, linewidth=0.8)


def draw_static_2d(ax):
    half = np.radians(config.CAMERA_FOV_DEGREES / 2)
    for h in (1.0, 2.0, 3.0):
        ax.add_patch(Circle((0, 0), h*np.tan(half), fill=False,
                            color=CYAN, alpha=0.18, linestyle="--", lw=0.7))
    ax.scatter([0], [0], c=CYAN, marker="^", s=110,
               edgecolors=TEXT, linewidths=1, zorder=5)
    sx, sy, _ = START_POS
    ax.scatter([sx], [sy], c=DIM, marker="o", s=70,
               edgecolors=TEXT, linewidths=0.8, zorder=4, alpha=0.6)
    ax.text(sx + 0.15, sy + 0.15, "START", color=DIM, fontsize=7)


# ---- Render --------------------------------------------------------------

def alpha_for(obj):
    """Faded objects get half opacity throughout."""
    return 0.55 if obj.short_name in FADED_OBJECTS else 1.0


def build_object_timeline(obj, throw):
    """Sample frames so every object's scene is roughly the same length."""
    n = len(throw.observed_points)
    if n >= TARGET_LIVE_FRAMES:
        stride = max(1, n // TARGET_LIVE_FRAMES + 1)
        frame_indices = list(range(0, n, stride))
        if frame_indices[-1] != n - 1:
            frame_indices.append(n - 1)
        repeats = 1
    else:
        stride = 1
        frame_indices = list(range(n))
        repeats = max(1, TARGET_LIVE_FRAMES // n)
    return frame_indices, repeats


def render():
    print("Simulating throws...")
    sims = []
    for key in SELECTED:
        result = simulate(key)
        if result is None:
            continue
        obj, throw, preds = result
        v_t = terminal_velocity(obj)
        sims.append((obj, throw, preds, v_t))
        print(f"  • {obj.name:<32}  flight={throw.actual_flight_time:.2f}s  "
              f"v_t={v_t:.1f} m/s  frames={len(throw.observed_points)}")

    # Final stats per object (for cumulative leaderboard)
    final_results = []
    for obj, throw, preds, v_t in sims:
        last_pred = preds[-1] if preds else None
        if last_pred is None:
            err_cm, status = None, "NO PRED"
        else:
            err_cm = calculate_prediction_error(last_pred, throw.actual_landing)*100
            status = "✓ CAUGHT" if err_cm < 10 else "✗ MISS"
        final_results.append(dict(obj=obj, throw=throw, v_t=v_t,
                                  err_cm=err_cm, status=status, pred=last_pred))

    # Build sequential timeline
    timeline = []
    for obj_idx, (obj, throw, preds, _v_t) in enumerate(sims):
        frame_indices, repeats = build_object_timeline(obj, throw)
        for fi in frame_indices:
            for _ in range(repeats):
                timeline.append((obj_idx, fi, "live"))
        for _ in range(HOLD_FRAMES):
            timeline.append((obj_idx, len(throw.observed_points) - 1, "hold"))

    print(f"\nTimeline: {len(timeline)} frames "
          f"(~{len(timeline)/PLAYBACK_FPS:.1f}s at {PLAYBACK_FPS}fps)")

    # Figure
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor(BG)
    ax3d = fig.add_subplot(1, 2, 1, projection="3d")
    ax2d = fig.add_subplot(2, 2, 2)
    axhud = fig.add_subplot(2, 2, 4)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.91, bottom=0.06,
                        wspace=0.18, hspace=0.28)
    fig.text(0.5, 0.965,
             "T R A S H   C A T C H E R   ·   O B J E C T   D R A G   S T U D Y",
             ha="center", color=TEXT, fontsize=13, weight="bold")
    fig.text(0.5, 0.935,
             "Same throw, different objects — air drag shifts every landing",
             ha="center", color=DIM, fontsize=9)

    def draw(state):
        active_idx, frame_idx, phase = state
        ax3d.cla(); ax2d.cla(); axhud.cla()
        style_3d(ax3d); style_2d(ax2d); style_hud(axhud)
        draw_static_3d(ax3d); draw_static_2d(ax2d)

        cz = config.CATCH_PLANE_HEIGHT_M
        active_obj, active_throw, active_preds, _ = sims[active_idx]
        active_alpha = alpha_for(active_obj)

        # --- Ghost prior objects: just their landing stars ---
        for i in range(active_idx):
            obj_g, throw_g, _, _ = sims[i]
            gx, gy = throw_g.actual_landing
            ax3d.scatter([gx], [gy], [cz], marker="*",
                         c=obj_g.color, s=110, edgecolors=TEXT,
                         linewidths=0.5, alpha=0.45, zorder=12)
            ax2d.scatter([gx], [gy], marker="*", c=obj_g.color,
                         s=110, edgecolors=TEXT, linewidths=0.5,
                         alpha=0.45, zorder=8)

        # --- Active object: full bright trail + head ---
        seen = active_throw.observed_points[: frame_idx + 1]
        visible = [p for p in seen if p.in_fov]

        if visible:
            xs = np.array([p.x_m for p in visible])
            ys = np.array([p.y_m for p in visible])
            zs = np.array([p.z_m for p in visible])

            for j in range(1, len(xs)):
                a = (0.20 + 0.80 * (j / len(xs))) * active_alpha
                ax3d.plot(xs[j-1:j+1], ys[j-1:j+1], zs[j-1:j+1],
                          color=active_obj.color, linewidth=2.4, alpha=a)
            ax3d.scatter(xs, ys, zs, c=active_obj.color, s=12,
                         alpha=0.55*active_alpha, edgecolors="none")

            ax2d.plot(xs, ys, color=active_obj.color, linewidth=1.8,
                      alpha=0.85*active_alpha)
            ax2d.scatter(xs, ys, c=active_obj.color, s=10,
                         alpha=0.6*active_alpha, edgecolors="none")

            still_flying = frame_idx < len(active_throw.observed_points) - 1
            head = visible[-1]
            if still_flying:
                ax3d.scatter([head.x_m], [head.y_m], [head.z_m],
                             c=TEXT, s=110, edgecolors=active_obj.color,
                             linewidths=2.0, zorder=20, alpha=active_alpha)
                ax2d.scatter([head.x_m], [head.y_m], c=TEXT, s=85,
                             edgecolors=active_obj.color, linewidths=1.6,
                             zorder=10, alpha=active_alpha)

        # --- Active prediction marker on catch plane ---
        cur_pred = active_preds[frame_idx] if active_preds else None
        if cur_pred is not None:
            confidence = cur_pred.confidence
            r = max(0.06, 0.55 * (1 - confidence))
            actionable = cur_pred.is_actionable(min_confidence=0.6)
            mcolor = LIME if actionable else active_obj.color

            theta = np.linspace(0, 2*np.pi, 60)
            ax3d.plot(cur_pred.landing_x + r*np.cos(theta),
                      cur_pred.landing_y + r*np.sin(theta),
                      np.full_like(theta, cz),
                      color=mcolor, linewidth=2, alpha=0.85*active_alpha)
            ax2d.add_patch(Circle((cur_pred.landing_x, cur_pred.landing_y),
                                  r, fill=False, color=mcolor, linewidth=2,
                                  alpha=0.85*active_alpha))
            ax2d.add_patch(Circle((cur_pred.landing_x, cur_pred.landing_y),
                                  max(0.02, r*0.25), fill=True,
                                  color=mcolor, alpha=0.85*active_alpha))

        # --- Reveal active landing during hold ---
        if phase == "hold":
            ax_x, ax_y = active_throw.actual_landing
            ax3d.scatter([ax_x], [ax_y], [cz], marker="*",
                         c=AMBER, s=240, edgecolors=TEXT,
                         linewidths=0.8, zorder=22, alpha=active_alpha)
            ax2d.scatter([ax_x], [ax_y], marker="*", c=AMBER,
                         s=240, edgecolors=TEXT, linewidths=0.8,
                         zorder=12, alpha=active_alpha)
            if cur_pred is not None:
                ax2d.plot([cur_pred.landing_x, ax_x],
                          [cur_pred.landing_y, ax_y],
                          color=AMBER, linewidth=1.2, alpha=0.7,
                          linestyle=":")

        # --- 3D corner labels ---
        ax3d.text2D(0.02, 0.95,
                    f"NOW THROWING:  {active_obj.name.upper()}",
                    transform=ax3d.transAxes, color=active_obj.color,
                    fontsize=11, weight="bold",
                    alpha=active_alpha)
        if active_obj.short_name in FADED_OBJECTS:
            ax3d.text2D(0.02, 0.90, "EXPECTED FAIL  ·  drag-dominated",
                        transform=ax3d.transAxes, color=AMBER,
                        fontsize=9, weight="bold", alpha=0.85)

        sim_t = frame_idx / config.CAMERA_FPS
        ax3d.text2D(0.78, 0.95, f"t = {sim_t:.2f}s",
                    transform=ax3d.transAxes, color=DIM,
                    fontsize=10, family="monospace")

        # --- HUD: cumulative leaderboard ---
        n_rows = len(sims)
        row_h = 0.86 / n_rows
        y0 = 0.93
        for x, label in [(0.04, "OBJECT"),
                         (0.50, "FLIGHT"),
                         (0.66, "v_t"),
                         (0.81, "ERROR"),
                         (0.96, "STATUS")]:
            axhud.text(x, y0, label, color=DIM, fontsize=7,
                       weight="bold",
                       ha="left" if x < 0.5 else "right",
                       transform=axhud.transAxes)

        for i, fr in enumerate(final_results):
            obj_i = fr["obj"]
            y = y0 - row_h * (i + 0.7)
            is_active = (i == active_idx)
            is_done = (i < active_idx) or (i == active_idx and phase == "hold")
            row_alpha = 0.06 if not is_active else 0.18

            # Row strip
            axhud.add_patch(plt.Rectangle((0.02, y - row_h*0.4), 0.96,
                                          row_h*0.85, facecolor=obj_i.color,
                                          alpha=row_alpha, edgecolor="none",
                                          transform=axhud.transAxes))
            # Active row indicator bar
            if is_active:
                axhud.add_patch(plt.Rectangle((0.005, y - row_h*0.4), 0.012,
                                              row_h*0.85,
                                              facecolor=obj_i.color,
                                              alpha=0.95, edgecolor="none",
                                              transform=axhud.transAxes))

            # Color dot + name
            tcol = TEXT if is_done or is_active else DIM
            axhud.scatter([0.045], [y], color=obj_i.color, s=90,
                          edgecolors=TEXT, linewidths=0.8,
                          alpha=1.0 if is_active or is_done else 0.4,
                          transform=axhud.transAxes)
            axhud.text(0.085, y, obj_i.name, color=tcol,
                       fontsize=9, weight="bold",
                       va="center", ha="left",
                       transform=axhud.transAxes)

            # Stats
            ft_text = f"{fr['throw'].actual_flight_time:.2f}s"
            axhud.text(0.50, y, ft_text, color=DIM, fontsize=8,
                       family="monospace", va="center", ha="right",
                       transform=axhud.transAxes)
            axhud.text(0.66, y, f"{fr['v_t']:4.1f}", color=DIM, fontsize=8,
                       family="monospace", va="center", ha="right",
                       transform=axhud.transAxes)

            # Error / status: only show after the object has been thrown
            if is_done:
                if fr["err_cm"] is not None:
                    err_color = (LIME if fr["err_cm"] < 10
                                 else AMBER if fr["err_cm"] < 30
                                 else RED)
                    err_text = f"{fr['err_cm']:5.1f}cm"
                else:
                    err_color, err_text = RED, "  -- "
                axhud.text(0.81, y, err_text, color=err_color, fontsize=9,
                           weight="bold", family="monospace",
                           va="center", ha="right",
                           transform=axhud.transAxes)
                scolor = (LIME if fr["status"] == "✓ CAUGHT"
                          else RED if fr["status"] == "✗ MISS"
                          else DIM)
                axhud.text(0.96, y, fr["status"], color=scolor, fontsize=8,
                           weight="bold", va="center", ha="right",
                           transform=axhud.transAxes)
            elif is_active:
                # Live error from current prediction
                if cur_pred is not None:
                    live_err = (calculate_prediction_error(
                        cur_pred, active_throw.actual_landing)*100)
                    axhud.text(0.81, y, f"{live_err:5.1f}cm", color=obj_i.color,
                               fontsize=9, weight="bold", family="monospace",
                               va="center", ha="right",
                               transform=axhud.transAxes)
                else:
                    axhud.text(0.81, y, "  -- ", color=DIM, fontsize=9,
                               family="monospace", va="center", ha="right",
                               transform=axhud.transAxes)
                axhud.text(0.96, y, "FLYING…", color=obj_i.color, fontsize=8,
                           weight="bold", va="center", ha="right",
                           transform=axhud.transAxes)
            else:
                axhud.text(0.81, y, "—", color=DIM, fontsize=9,
                           family="monospace", va="center", ha="right",
                           transform=axhud.transAxes)
                axhud.text(0.96, y, "QUEUED", color=DIM, fontsize=8,
                           weight="bold", va="center", ha="right",
                           transform=axhud.transAxes)

    def init():
        draw(timeline[0]); return []

    def update(i):
        draw(timeline[i]); return []

    out_mp4 = "objects_comparison.mp4"
    print(f"Encoding MP4 → {out_mp4}")
    writer = FFMpegWriter(fps=PLAYBACK_FPS, bitrate=5500,
                          codec="libx264",
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "medium",
                                      "-movflags", "+faststart"])
    anim = FuncAnimation(fig, update, init_func=init,
                         frames=len(timeline),
                         interval=1000/PLAYBACK_FPS, blit=False)
    anim.save(out_mp4, writer=writer, dpi=100)
    print(f"  saved: {os.path.getsize(out_mp4)/1024:.0f} KB")

    out_gif = "objects_comparison.gif"
    print(f"Encoding GIF → {out_gif}")
    anim_gif = FuncAnimation(fig, update, init_func=init,
                             frames=range(0, len(timeline), 2),
                             interval=1000/12, blit=False)
    anim_gif.save(out_gif, writer=PillowWriter(fps=12), dpi=72)
    print(f"  saved: {os.path.getsize(out_gif)/1024:.0f} KB")

    plt.close(fig)
    print("Done.")


if __name__ == "__main__":
    render()
