"""
Air-drag-enabled trajectory simulator.

Adds quadratic air drag to projectile motion using RK4 integration. This is
the realistic counterpart to ``src/simulator.py``, which uses closed-form
vacuum motion. Use this when an object's mass and drag profile are known
(via ``PhysicalObject``) and the throw involves materials whose terminal
velocity is comparable to throw speeds (paper, foil, plastic film).

Force model (per unit mass):
    a = -g * z_hat - (0.5 * rho * Cd * A / m) * |v| * v_vec

Output is a ``Throw`` (same dataclass as the vacuum simulator), so the
predictor and visualizer remain drop-in compatible.
"""

import numpy as np
from typing import List, Tuple

import config
from src.simulator import (
    Throw,
    TrajectoryPoint,
    is_point_in_fov,
    add_noise,
)
from src.objects import PhysicalObject


def terminal_velocity(obj: PhysicalObject, air_density: float = 1.225) -> float:
    """
    Analytic terminal velocity for an object falling vertically with quadratic drag.

    v_t = sqrt(2 * m * g / (rho * Cd * A))

    Args:
        obj: PhysicalObject with mass, Cd, and A.
        air_density: kg/m^3 (1.225 at sea level, 15 C).

    Returns:
        Terminal velocity in m/s.
    """
    drag_factor = air_density * obj.drag_coefficient * obj.cross_section_m2
    if drag_factor <= 0.0:
        # No drag => no terminal velocity (treat as infinite).
        return float("inf")
    return float(np.sqrt(2.0 * obj.mass_kg * config.GRAVITY_M_S2 / drag_factor))


def _acceleration(
    velocity: np.ndarray,
    drag_per_mass: float,
    gravity: float,
) -> np.ndarray:
    """
    Compute acceleration vector under gravity + quadratic drag.

    a = (0, 0, -g) - (0.5 * rho * Cd * A / m) * |v| * v
    """
    speed = float(np.linalg.norm(velocity))
    # drag_per_mass already absorbs the 0.5 * rho * Cd * A / m factor
    drag_accel = -drag_per_mass * speed * velocity
    return drag_accel + np.array([0.0, 0.0, -gravity])


def _rk4_step(
    pos: np.ndarray,
    vel: np.ndarray,
    dt: float,
    drag_per_mass: float,
    gravity: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Classic 4th-order Runge-Kutta step for the coupled (pos, vel) system.

    State derivative:  d(pos)/dt = vel,  d(vel)/dt = a(vel)
    Drag depends only on velocity, so position derivative is just velocity.
    """
    # k1
    k1_v = vel
    k1_a = _acceleration(vel, drag_per_mass, gravity)

    # k2
    v2 = vel + 0.5 * dt * k1_a
    k2_v = v2
    k2_a = _acceleration(v2, drag_per_mass, gravity)

    # k3
    v3 = vel + 0.5 * dt * k2_a
    k3_v = v3
    k3_a = _acceleration(v3, drag_per_mass, gravity)

    # k4
    v4 = vel + dt * k3_a
    k4_v = v4
    k4_a = _acceleration(v4, drag_per_mass, gravity)

    new_pos = pos + (dt / 6.0) * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v)
    new_vel = vel + (dt / 6.0) * (k1_a + 2.0 * k2_a + 2.0 * k3_a + k4_a)
    return new_pos, new_vel


def generate_throw_with_drag(
    obj: PhysicalObject,
    start_position: Tuple[float, float, float],
    start_velocity: Tuple[float, float, float],
    add_measurement_noise: bool = True,
    dropout_probability: float = 0.05,
    catch_height: float = config.CATCH_PLANE_HEIGHT_M,
    air_density: float = 1.225,
    integration_dt: float = 0.001,
    max_flight_time: float = 6.0,
) -> Throw:
    """
    Generate a throw with quadratic air drag using RK4 integration.

    Force model (per unit mass):
        a = -g * z_hat - (0.5 * rho * Cd * A / m) * |v| * v_vec

    The integrator runs at ``integration_dt`` (1 ms default for accuracy);
    ``TrajectoryPoint``s are sampled at ``config.CAMERA_FPS`` and are passed
    through ``is_point_in_fov``, then optionally noised + dropped exactly
    like ``generate_throw()``.

    Args:
        obj: PhysicalObject describing mass + aerodynamics.
        start_position: (x, y, z) in meters.
        start_velocity: (vx, vy, vz) in m/s.
        add_measurement_noise: add Gaussian sensor noise (default True).
        dropout_probability: per-frame missed-frame chance (default 5%).
        catch_height: stop integration when z <= this (meters).
        air_density: kg/m^3 (default 1.225, sea level).
        integration_dt: RK4 step in seconds (default 1 ms).
        max_flight_time: hard cap to prevent infinite loops on drag-dominated
            trajectories that asymptote without crossing the catch plane.

    Returns:
        Throw with ground-truth landing and camera-rate observations.

    Raises:
        ValueError: object never reaches the catch plane within
            ``max_flight_time`` (e.g. paper sheet thrown sideways at terminal
            velocity), or it starts at/below catch height moving downward.
    """
    if obj.mass_kg <= 0.0:
        raise ValueError(f"PhysicalObject mass must be positive, got {obj.mass_kg}")

    pos = np.array(start_position, dtype=float)
    vel = np.array(start_velocity, dtype=float)

    # Reject objects starting at/below catch plane moving down/sideways: the
    # vacuum simulator also rejects these via "object already past catch plane".
    if pos[2] <= catch_height and vel[2] <= 0.0:
        raise ValueError("Object never reaches catch plane (drag-dominated trajectory)")

    drag_per_mass = 0.5 * air_density * obj.drag_coefficient * obj.cross_section_m2 / obj.mass_kg
    gravity = config.GRAVITY_M_S2

    sample_dt = 1.0 / config.CAMERA_FPS

    observed_points: List[TrajectoryPoint] = []
    t = 0.0
    next_sample_t = 0.0

    # Always emit the first frame (t=0) so the camera observation series is
    # evenly spaced starting at zero.
    def _emit_sample(sample_t: float, sample_pos: np.ndarray) -> None:
        x, y, z = float(sample_pos[0]), float(sample_pos[1]), float(sample_pos[2])
        in_fov = is_point_in_fov((x, y, z))
        if np.random.random() < dropout_probability:
            return
        if add_measurement_noise and in_fov:
            x = add_noise(x)
            y = add_noise(y)
            z = add_noise(z)
        observed_points.append(
            TrajectoryPoint(time_sec=sample_t, x_m=x, y_m=y, z_m=z, in_fov=in_fov)
        )

    _emit_sample(0.0, pos)
    next_sample_t += sample_dt

    landed = False
    actual_landing: Tuple[float, float] = (float(pos[0]), float(pos[1]))
    actual_flight_time = 0.0

    while t < max_flight_time:
        new_pos, new_vel = _rk4_step(pos, vel, integration_dt, drag_per_mass, gravity)
        new_t = t + integration_dt

        # Did we cross the catch plane during this step? Linearly interpolate
        # to estimate the exact landing moment.
        if new_pos[2] <= catch_height:
            z_old = pos[2]
            z_new = new_pos[2]
            if z_new == z_old:
                frac = 1.0
            else:
                frac = (z_old - catch_height) / (z_old - z_new)
                frac = float(np.clip(frac, 0.0, 1.0))
            land_pos = pos + frac * (new_pos - pos)
            actual_landing = (float(land_pos[0]), float(land_pos[1]))
            actual_flight_time = t + frac * integration_dt

            # Emit any remaining sample times that fall before landing.
            while next_sample_t <= actual_flight_time + 1e-9:
                interp_frac = (next_sample_t - t) / integration_dt
                interp_frac = float(np.clip(interp_frac, 0.0, 1.0))
                sample_pos = pos + interp_frac * (new_pos - pos)
                _emit_sample(next_sample_t, sample_pos)
                next_sample_t += sample_dt

            landed = True
            break

        # Emit any sampling boundaries that fall within this RK4 step.
        while next_sample_t <= new_t + 1e-9 and next_sample_t < max_flight_time:
            interp_frac = (next_sample_t - t) / integration_dt
            interp_frac = float(np.clip(interp_frac, 0.0, 1.0))
            sample_pos = pos + interp_frac * (new_pos - pos)
            _emit_sample(next_sample_t, sample_pos)
            next_sample_t += sample_dt

        pos = new_pos
        vel = new_vel
        t = new_t

    if not landed:
        raise ValueError("Object never reaches catch plane (drag-dominated trajectory)")

    return Throw(
        start_position=tuple(float(v) for v in start_position),
        start_velocity=tuple(float(v) for v in start_velocity),
        actual_landing=actual_landing,
        actual_flight_time=actual_flight_time,
        observed_points=observed_points,
    )
