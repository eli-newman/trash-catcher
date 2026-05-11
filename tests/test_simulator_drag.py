"""Tests for the air-drag-enabled simulator."""

import math
import numpy as np
import pytest

import config
from src.objects import PhysicalObject
from src.simulator import calculate_landing, get_visible_points
from src.simulator_drag import (
    generate_throw_with_drag,
    terminal_velocity,
)
from src.predictor import predict_landing


# Test fixtures: lightweight stand-ins for the catalog the parallel agent
# is producing. Numbers are realistic-but-illustrative, not authoritative.
PAPER_SHEET = PhysicalObject(
    name="Paper Sheet (flat)",
    short_name="paper_sheet_flat",
    mass_kg=0.005,
    drag_coefficient=1.3,
    cross_section_m2=0.06,
    color="white",
    emoji="paper",
)

SODA_CAN_FULL = PhysicalObject(
    name="Soda Can (full)",
    short_name="soda_can_full",
    mass_kg=0.385,
    drag_coefficient=1.0,
    cross_section_m2=0.005,
    color="silver",
    emoji="can",
)


# ---------------------------------------------------------------------------
# Drag-zero matches the closed-form vacuum solver
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 7, 42, 123])
def test_drag_zero_matches_vacuum(seed):
    """With air_density=0, drag simulator must match closed-form vacuum motion."""
    rng = np.random.default_rng(seed)
    start_pos = (
        float(rng.uniform(-1.0, 1.0)),
        float(rng.uniform(-1.0, 1.0)),
        float(rng.uniform(2.0, 3.0)),
    )
    start_vel = (
        float(rng.uniform(-2.0, 2.0)),
        float(rng.uniform(-2.0, 2.0)),
        float(rng.uniform(-1.0, 2.0)),
    )

    # Use the soda can (mass + Cd irrelevant since rho=0 zeroes the drag term)
    np.random.seed(seed)  # noise/dropout determinism inside the simulator
    throw = generate_throw_with_drag(
        SODA_CAN_FULL,
        start_position=start_pos,
        start_velocity=start_vel,
        add_measurement_noise=False,
        dropout_probability=0.0,
        air_density=0.0,
    )

    expected_landing, expected_time = calculate_landing(start_pos, start_vel)

    dx = throw.actual_landing[0] - expected_landing[0]
    dy = throw.actual_landing[1] - expected_landing[1]
    err = math.hypot(dx, dy)
    assert err < 0.01, f"vacuum mismatch {err:.4f} m (seed={seed})"
    # Flight time should also align well.
    assert abs(throw.actual_flight_time - expected_time) < 0.01


# ---------------------------------------------------------------------------
# Drag dominates light, broad objects
# ---------------------------------------------------------------------------

def test_drag_slows_paper_far_more_than_can():
    """Paper sheet should fall much slower than a soda can due to drag."""
    np.random.seed(0)
    paper_throw = generate_throw_with_drag(
        PAPER_SHEET,
        start_position=(0.0, 0.0, 2.0),
        start_velocity=(0.0, 0.0, 0.0),
        add_measurement_noise=False,
        dropout_probability=0.0,
    )
    can_throw = generate_throw_with_drag(
        SODA_CAN_FULL,
        start_position=(0.0, 0.0, 2.0),
        start_velocity=(0.0, 0.0, 0.0),
        add_measurement_noise=False,
        dropout_probability=0.0,
    )
    ratio = paper_throw.actual_flight_time / can_throw.actual_flight_time
    assert ratio > 1.5, (
        f"Expected paper to take >1.5x longer than can; got ratio={ratio:.2f} "
        f"(paper={paper_throw.actual_flight_time:.3f}s, can={can_throw.actual_flight_time:.3f}s)"
    )


# ---------------------------------------------------------------------------
# Terminal velocity: long-fall paper converges to analytic v_t
# ---------------------------------------------------------------------------

def test_paper_terminal_velocity_convergence():
    """Drop paper from 50m; final vz should be within 10% of analytic v_t."""
    v_t = terminal_velocity(PAPER_SHEET)

    # Reach-deep integrate to get the final velocity from the camera samples.
    # We need vz at landing. The simulator returns positions only; we'll re-run
    # the RK4 inline to read off the final velocity vector.
    from src.simulator_drag import _rk4_step

    pos = np.array([0.0, 0.0, 50.0])
    vel = np.array([0.0, 0.0, 0.0])
    drag_per_mass = (
        0.5
        * 1.225
        * PAPER_SHEET.drag_coefficient
        * PAPER_SHEET.cross_section_m2
        / PAPER_SHEET.mass_kg
    )
    dt = 0.001
    for _ in range(int(20.0 / dt)):  # cap at 20 s of fall
        pos, vel = _rk4_step(pos, vel, dt, drag_per_mass, config.GRAVITY_M_S2)
        if pos[2] <= 0.5:  # close to ground
            break

    final_vz = abs(float(vel[2]))
    rel_err = abs(final_vz - v_t) / v_t
    assert rel_err < 0.10, (
        f"Terminal-velocity convergence off: final |vz|={final_vz:.3f} m/s, "
        f"analytic v_t={v_t:.3f} m/s, rel_err={rel_err:.2%}"
    )


def test_terminal_velocity_formula():
    """Helper formula matches v_t = sqrt(2mg / (rho Cd A))."""
    rho = 1.225
    expected = math.sqrt(
        2.0 * SODA_CAN_FULL.mass_kg * config.GRAVITY_M_S2
        / (rho * SODA_CAN_FULL.drag_coefficient * SODA_CAN_FULL.cross_section_m2)
    )
    assert math.isclose(terminal_velocity(SODA_CAN_FULL, rho), expected, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Energy must be dissipated when drag is on
# ---------------------------------------------------------------------------

def test_drag_dissipates_energy():
    """KE + PE at landing must be strictly less than at launch when drag is on."""
    np.random.seed(0)
    start_pos = (0.0, 0.0, 2.5)
    start_vel = (1.5, -0.5, 2.0)

    throw = generate_throw_with_drag(
        PAPER_SHEET,
        start_position=start_pos,
        start_velocity=start_vel,
        add_measurement_noise=False,
        dropout_probability=0.0,
    )

    # Reproduce the integration to recover landing velocity.
    from src.simulator_drag import _rk4_step

    pos = np.array(start_pos, dtype=float)
    vel = np.array(start_vel, dtype=float)
    drag_per_mass = (
        0.5
        * 1.225
        * PAPER_SHEET.drag_coefficient
        * PAPER_SHEET.cross_section_m2
        / PAPER_SHEET.mass_kg
    )
    dt = 0.001
    while pos[2] > config.CATCH_PLANE_HEIGHT_M:
        pos, vel = _rk4_step(pos, vel, dt, drag_per_mass, config.GRAVITY_M_S2)

    m = PAPER_SHEET.mass_kg
    g = config.GRAVITY_M_S2
    e_start = 0.5 * m * float(np.dot(np.array(start_vel), np.array(start_vel))) + m * g * start_pos[2]
    e_end = 0.5 * m * float(np.dot(vel, vel)) + m * g * float(pos[2])

    assert e_end < e_start - 1e-9, (
        f"Energy not dissipated: E_start={e_start:.6f} J, E_end={e_end:.6f} J"
    )
    # Landing time consistent
    assert throw.actual_flight_time > 0.0


# ---------------------------------------------------------------------------
# API compatibility: Throw shape + frame spacing
# ---------------------------------------------------------------------------

def test_throw_api_compat_and_frame_spacing():
    """Returned Throw has all fields and observed_points are evenly spaced."""
    np.random.seed(123)
    throw = generate_throw_with_drag(
        SODA_CAN_FULL,
        start_position=(0.0, 0.0, 2.5),
        start_velocity=(0.5, 0.0, 1.0),
        add_measurement_noise=False,
        dropout_probability=0.0,
    )

    # Required fields exist and have correct types
    assert isinstance(throw.start_position, tuple) and len(throw.start_position) == 3
    assert isinstance(throw.start_velocity, tuple) and len(throw.start_velocity) == 3
    assert isinstance(throw.actual_landing, tuple) and len(throw.actual_landing) == 2
    assert isinstance(throw.actual_flight_time, float)
    assert isinstance(throw.observed_points, list)
    assert len(throw.observed_points) >= 2

    # Sample spacing must equal 1/CAMERA_FPS (with no dropout).
    expected_dt = 1.0 / config.CAMERA_FPS
    times = [p.time_sec for p in throw.observed_points]
    diffs = np.diff(times)
    assert np.allclose(diffs, expected_dt, atol=1e-6), (
        f"Frames not evenly spaced at 1/{config.CAMERA_FPS}s: diffs={diffs}"
    )


# ---------------------------------------------------------------------------
# Existing predictor still runs on a draggy throw (may be inaccurate)
# ---------------------------------------------------------------------------

def test_predictor_runs_on_draggy_throw():
    """predict_landing should not crash on a paper-sheet drag trajectory."""
    np.random.seed(0)
    throw = generate_throw_with_drag(
        PAPER_SHEET,
        start_position=(0.5, 0.5, 2.5),
        start_velocity=(0.5, -0.5, 1.0),
        add_measurement_noise=True,
        dropout_probability=0.0,
    )
    visible = get_visible_points(throw)
    # Need at least the predictor's minimum frame count.
    assert len(visible) >= config.MIN_FRAMES_FOR_PREDICTION

    pred = predict_landing(visible)
    # We don't require accuracy — only that the call returns a Prediction.
    assert pred is not None
    assert hasattr(pred, "landing_x")
    assert hasattr(pred, "landing_y")


# ---------------------------------------------------------------------------
# No-fly case: thrown sharply downward from below catch height
# ---------------------------------------------------------------------------

def test_no_fly_below_catch_height_raises():
    """Object starting below catch plane moving down should raise ValueError."""
    with pytest.raises(ValueError):
        generate_throw_with_drag(
            SODA_CAN_FULL,
            start_position=(0.0, 0.0, 0.1),  # below CATCH_PLANE_HEIGHT_M (0.3)
            start_velocity=(0.0, 0.0, -2.0),  # moving downward
            add_measurement_noise=False,
            dropout_probability=0.0,
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
