---
name: trajectory-sim
description: Trajectory simulation and landing prediction for trash-catching robot. Use when working on simulator.py, predictor.py, or any physics/prediction code. Covers parabolic motion, camera FOV modeling, coordinate transforms, and prediction accuracy benchmarking.
---

# Trajectory Simulation Skill

## Physics Model

Objects follow projectile motion:
```
x(t) = x0 + vx * t
y(t) = y0 + vy * t  
z(t) = z0 + vz * t - 0.5 * g * t²
```

Landing time found by solving `z(t) = catch_height` using quadratic formula.

## Camera Model

ToF camera at origin pointing +z (up). FOV is a cone:
```python
# Point visible if:
# 1. Above camera (dz > 0)
# 2. Within range (distance < max_range)
# 3. Within cone (angle_from_vertical < fov/2)

horizontal_dist = sqrt(dx² + dy²)
angle = atan2(horizontal_dist, dz)
in_fov = angle < (fov_degrees / 2)
```

## Prediction Algorithm

1. Collect N visible points from camera
2. Fit parabola to z-coordinates: `z = a*t² + b*t + c`
3. Fit lines to x, y coordinates: `x = mx*t + bx`
4. Solve quadratic for landing time
5. Evaluate x(t), y(t) at landing time

Use `np.linalg.lstsq` for fitting - handles noise well.

## Key Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `CAMERA_FOV_DEGREES` | 70 | Diagonal FOV |
| `CAMERA_FPS` | 30 | Frames per second |
| `CAMERA_MAX_RANGE_M` | 4.0 | Max detection distance |
| `CAMERA_DEPTH_NOISE_M` | 0.02 | ±2cm measurement noise |
| `MIN_FRAMES_FOR_PREDICTION` | 5 | Minimum points needed |
| `CATCH_PLANE_HEIGHT_M` | 0.3 | Height of catch mechanism |

## Testing Predictions

Always test with:
1. Perfect data (no noise) - should be <1cm error
2. Noisy data - should be <10cm error for 80%+ throws
3. Edge cases: steep angles, fast throws, late FOV entry

```bash
# Quick accuracy check
python scripts/run_benchmark.py 100
```

## Common Bugs

**Negative landing time:** Object already past catch plane. Check discriminant and filter for future times only.

**NaN in prediction:** Division by zero when trajectory is nearly vertical. Add `abs(a) < 1e-10` check.

**High error on angled throws:** Usually FOV issue - object enters late, fewer frames to fit. Increase `MIN_FRAMES` or accept lower confidence.

**Inconsistent results:** Forgot to set random seed. Use `np.random.seed(N)` for reproducibility.

## Extending the Predictor

To add ML predictor later:
1. Same interface: `predict_landing(List[TrajectoryPoint]) -> Prediction`
2. Train on synthetic data first
3. Export training pairs: `(observed_points, actual_landing)`
4. Start with MLP, skip LSTM (trajectories are short)
