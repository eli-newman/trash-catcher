"""
Trajectory simulator.
Generates realistic throw data as the ToF camera would see it.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import config


@dataclass
class TrajectoryPoint:
    """Single point in a trajectory as seen by camera."""
    time_sec: float      # seconds since first detection
    x_m: float           # horizontal position (meters)
    y_m: float           # horizontal position (meters)  
    z_m: float           # height (meters)
    in_fov: bool         # is this point visible to camera?


@dataclass
class Throw:
    """Complete throw with ground truth and camera observations."""
    # Ground truth (what actually happens)
    start_position: Tuple[float, float, float]  # x, y, z
    start_velocity: Tuple[float, float, float]  # vx, vy, vz
    actual_landing: Tuple[float, float]         # x, y where it lands
    actual_flight_time: float                   # seconds in air
    
    # What camera sees (may have noise, missing frames)
    observed_points: List[TrajectoryPoint]


def calculate_landing(
    start_pos: Tuple[float, float, float],
    start_vel: Tuple[float, float, float],
    catch_height: float = config.CATCH_PLANE_HEIGHT_M,
    gravity: float = config.GRAVITY_M_S2
) -> Tuple[Tuple[float, float], float]:
    """
    Calculate where and when object lands.
    
    Args:
        start_pos: (x, y, z) starting position in meters
        start_vel: (vx, vy, vz) starting velocity in m/s
        catch_height: height of catch plane in meters
        gravity: gravitational acceleration in m/s^2
    
    Returns:
        ((landing_x, landing_y), flight_time)
    """
    x0, y0, z0 = start_pos
    vx, vy, vz = start_vel
    
    # Solve: catch_height = z0 + vz*t - 0.5*g*t^2
    # Rearrange: 0.5*g*t^2 - vz*t + (catch_height - z0) = 0
    # Use quadratic formula: t = (vz + sqrt(vz^2 - 2*g*(catch_height-z0))) / g
    
    a = 0.5 * gravity
    b = -vz
    c = catch_height - z0
    
    discriminant = b*b - 4*a*c
    
    if discriminant < 0:
        # Object never reaches catch height (thrown downward too fast or starts below)
        raise ValueError("Object never reaches catch plane")
    
    # We want the positive root (future time)
    t1 = (-b + np.sqrt(discriminant)) / (2*a)
    t2 = (-b - np.sqrt(discriminant)) / (2*a)
    
    # Take the larger positive time (object goes up then comes down)
    flight_time = max(t1, t2)
    
    if flight_time <= 0:
        raise ValueError("Object already past catch plane")
    
    # Calculate landing position
    landing_x = x0 + vx * flight_time
    landing_y = y0 + vy * flight_time
    
    return (landing_x, landing_y), flight_time


def is_point_in_fov(
    point: Tuple[float, float, float],
    camera_pos: Tuple[float, float, float] = config.CAMERA_POSITION,
    fov_degrees: float = config.CAMERA_FOV_DEGREES,
    max_range: float = config.CAMERA_MAX_RANGE_M
) -> bool:
    """
    Check if a 3D point is visible to the upward-facing camera.
    
    Camera is at camera_pos, pointing straight up (+z direction).
    FOV is a cone with apex at camera, opening upward.
    """
    px, py, pz = point
    cx, cy, cz = camera_pos
    
    # Vector from camera to point
    dx = px - cx
    dy = py - cy
    dz = pz - cz
    
    # Point must be above camera
    if dz <= 0:
        return False
    
    # Check range
    distance = np.sqrt(dx*dx + dy*dy + dz*dz)
    if distance > max_range:
        return False
    
    # Check angle from vertical
    # Angle = arctan(horizontal_distance / vertical_distance)
    horizontal_dist = np.sqrt(dx*dx + dy*dy)
    angle_from_vertical = np.degrees(np.arctan2(horizontal_dist, dz))
    
    # FOV is diagonal, so half-angle is FOV/2
    max_angle = fov_degrees / 2
    
    return angle_from_vertical <= max_angle


def add_noise(
    value: float, 
    noise_std: float = config.CAMERA_DEPTH_NOISE_M
) -> float:
    """Add Gaussian noise to a measurement."""
    return value + np.random.normal(0, noise_std)


def generate_throw(
    start_position: Optional[Tuple[float, float, float]] = None,
    start_velocity: Optional[Tuple[float, float, float]] = None,
    add_measurement_noise: bool = True,
    dropout_probability: float = 0.05
) -> Throw:
    """
    Generate a complete throw simulation.
    
    Args:
        start_position: (x, y, z) or None for random
        start_velocity: (vx, vy, vz) or None for random
        add_measurement_noise: add realistic sensor noise
        dropout_probability: chance of missing a frame (0.0 to 1.0)
    
    Returns:
        Throw object with ground truth and observations
    """
    # Generate random start if not provided
    if start_position is None:
        # Random position within camera FOV at typical throw height
        start_position = (
            np.random.uniform(-1.5, 1.5),  # x: -1.5m to 1.5m
            np.random.uniform(-1.5, 1.5),  # y: -1.5m to 1.5m
            np.random.uniform(2.0, 3.5)    # z: 2m to 3.5m height
        )
    
    if start_velocity is None:
        # Random velocity - mostly downward with some horizontal
        start_velocity = (
            np.random.uniform(-2.0, 2.0),   # vx: -2 to 2 m/s
            np.random.uniform(-2.0, 2.0),   # vy: -2 to 2 m/s
            np.random.uniform(-1.0, 3.0)    # vz: -1 to 3 m/s (can go up first)
        )
    
    # Calculate ground truth landing
    actual_landing, actual_flight_time = calculate_landing(
        start_position, start_velocity
    )
    
    # Generate observed points at camera frame rate
    dt = 1.0 / config.CAMERA_FPS
    observed_points = []
    
    t = 0.0
    while t <= actual_flight_time:
        # Calculate true position at time t
        x = start_position[0] + start_velocity[0] * t
        y = start_position[1] + start_velocity[1] * t
        z = start_position[2] + start_velocity[2] * t - 0.5 * config.GRAVITY_M_S2 * t * t
        
        # Check if in FOV
        in_fov = is_point_in_fov((x, y, z))
        
        # Simulate dropout (missed frame)
        if np.random.random() < dropout_probability:
            t += dt
            continue
        
        # Add noise if enabled
        if add_measurement_noise and in_fov:
            x = add_noise(x)
            y = add_noise(y)
            z = add_noise(z)
        
        point = TrajectoryPoint(
            time_sec=t,
            x_m=x,
            y_m=y,
            z_m=z,
            in_fov=in_fov
        )
        observed_points.append(point)
        
        t += dt
    
    return Throw(
        start_position=start_position,
        start_velocity=start_velocity,
        actual_landing=actual_landing,
        actual_flight_time=actual_flight_time,
        observed_points=observed_points
    )


def get_visible_points(throw: Throw) -> List[TrajectoryPoint]:
    """Get only the points the camera can actually see."""
    return [p for p in throw.observed_points if p.in_fov]
