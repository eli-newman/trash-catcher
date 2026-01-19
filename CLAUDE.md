# Trash Catcher MVP - Claude Code Guide

## Project Overview

**Physics-based trajectory prediction system for autonomous trash-catching robot.**

Simulation software that validates we can predict where falling objects land using ToF camera data. Software proves the concept before hardware integration.

**Current Status:** ✅ Simulation validated, ready for hardware deployment
**Success Metric:** ✅ 89.6% accuracy within 10cm (exceeds 80% target)

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CURRENT (Software)                   │
├─────────────────────────────────────────────────────────┤
│  simulator.py  → Generates synthetic ToF camera data    │
│  predictor.py  → Predicts landing (physics-based)       │
│  visualizer.py → 3D visualization & debugging           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   NEXT PHASE (Hardware)                  │
├─────────────────────────────────────────────────────────┤
│  camera.py     → ArduCam ToF 4M data acquisition        │
│  servo.py      → Pan/tilt servo control system          │
│  controller.py → Real-time trajectory tracking loop     │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
TrajectoryPoint (observation) → predictor.py → Prediction
       ↓                                           ↓
   (t, x, y, z, in_fov)              (landing_x, landing_y, time, confidence)
                                                   ↓
                                           [SERVO CONTROL]
                                         Move catch mechanism
                                        to predicted position
```

## Key Files & Modules

### Core Modules (`src/`)

| File | Purpose | Lines | Complexity |
|------|---------|-------|------------|
| `simulator.py` | Generates realistic throw trajectories | ~220 | Medium |
| `predictor.py` | Physics-based landing prediction | ~180 | Medium |
| `visualizer.py` | 3D matplotlib visualization | ~100 | Low |

### Configuration

| File | Purpose | When to Modify |
|------|---------|----------------|
| `config.py` | All tunable parameters | Camera specs, physics constants, catch height |

### Scripts (`scripts/`)

| Script | Purpose | Use Case |
|--------|---------|----------|
| `run_single_throw.py` | Demo single trajectory | Quick validation |
| `run_benchmark.py` | Accuracy testing (N throws) | Performance measurement |
| `run_visualization.py` | Animated trajectory plots | Debugging |
| `interactive_simulator.py` | **Real-time parameter tuning** | Experimentation, demos |
| `demo_fov_entry.py` | FOV entry scenario | Edge case testing |
| `visualize_fov_entry.py` | FOV entry visualization | Understanding visibility |
| `animate_fov_entry.py` | Create GIF animation | Documentation, sharing |

### Tests (`tests/`)

| File | Tests | Status |
|------|-------|--------|
| `test_simulator.py` | Trajectory generation, FOV detection | ✅ 9/9 pass |
| `test_predictor.py` | Landing prediction, curve fitting | ✅ 8/8 pass |

**Total:** 17 tests, all passing

## Coordinate System

```
      +Z (up)
       ↑
       │
       │    Camera looking UP
       │    at origin (0,0,0)
       │           ▲
       │          /│\
       └──────────────→ +X
      /          Camera
     /
   +Y

- Origin: Camera position (0, 0, 0)
- +Z: Vertical (up)
- X, Y: Horizontal plane
- Catch plane: z = 0.3m (30cm above ground)
- FOV: 70° cone pointing upward
```

## Quick Start

```bash
# 1. Setup environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Run tests (always do this first!)
python3 -m pytest tests/ -v

# 3. Try interactive simulator (RECOMMENDED)
python3 scripts/interactive_simulator.py

# 4. Check accuracy
python3 scripts/run_benchmark.py 100

# 5. Single throw demo
python3 scripts/run_single_throw.py
```

## Interactive Simulator (Best for Learning)

**Launch:** `python3 scripts/interactive_simulator.py`

**Features:**
- 6 real-time parameter sliders
- Live 3D + top-down visualization
- Instant prediction updates
- FOV visibility visualization
- Preset scenarios

**Sliders:**
- Start X, Y, Z (position)
- Speed (0.5-6 m/s)
- Horizontal angle (-180° to 180°)
- Vertical angle (-30° to 90°)

**Presets:**
- Center Drop: Simple test case
- Side Arc: Curved trajectory
- Fast Toss: High-speed throw
- **FOV Entry:** Object enters view mid-flight

## Configuration Parameters (`config.py`)

### Camera Settings
```python
CAMERA_FOV_DEGREES = 70      # Field of view
CAMERA_MAX_RANGE_M = 4.0     # Max detection distance
CAMERA_FPS = 30              # Frame rate
CAMERA_DEPTH_NOISE_M = 0.02  # ±2cm accuracy
```

### Physics
```python
GRAVITY_M_S2 = 9.81
CATCH_PLANE_HEIGHT_M = 0.3   # Where robot catches
```

### Prediction
```python
MIN_FRAMES_FOR_PREDICTION = 5   # Minimum data points
MAX_FRAMES_FOR_PREDICTION = 15  # Don't use old data
```

## Testing & Validation

### Run All Tests
```bash
python3 -m pytest tests/ -v
```

### Run Specific Test
```bash
python3 -m pytest tests/test_predictor.py::test_object_entering_fov_mid_flight -v -s
```

### Benchmark Accuracy
```bash
python3 scripts/run_benchmark.py 100  # 100 random throws
```

**Expected Results:**
- Mean error: ~5cm
- Median error: ~3cm
- Success rate (< 10cm): >89%

## Key Test Cases

### 1. Standard Throws (Inside FOV)
- Starting position inside camera view
- Full trajectory visibility
- **Accuracy:** <5cm typical

### 2. FOV Entry (Edge Case) ✨ NEW
- Object starts **outside** FOV
- Enters camera view mid-flight
- Only 55-60% trajectory visible
- **Accuracy:** Still <2cm!
- **Test:** `test_object_entering_fov_mid_flight()`

### 3. Noisy Data
- Realistic sensor noise (±2cm)
- Occasional dropped frames
- **Accuracy:** <30cm tolerance

## Common Development Tasks

### 1. Adjust Camera Parameters
```python
# Edit config.py
CAMERA_FOV_DEGREES = 80  # Change FOV
CAMERA_FPS = 60          # Higher frame rate
```
Then: Run benchmark to see impact

### 2. Test New Throw Scenario
```python
# In scripts/run_single_throw.py or use interactive simulator
throw = generate_throw(
    start_position=(x, y, z),
    start_velocity=(vx, vy, vz),
    add_measurement_noise=True
)
```

### 3. Improve Predictor Accuracy
1. Modify `src/predictor.py::predict_landing()`
2. Run: `pytest tests/test_predictor.py -v`
3. Run: `python3 scripts/run_benchmark.py 100`
4. Compare before/after accuracy

### 4. Add New Visualization
1. Edit `src/visualizer.py`
2. Add function using matplotlib
3. Call from scripts

## Hardware Integration Roadmap

### Phase 1: Camera Integration (NEXT)
**Goal:** Replace simulator with real ToF camera

**Files to Create:**
- `src/camera.py` - ArduCam ToF 4M driver
  - Initialize camera
  - Read depth frames (30 FPS)
  - Convert to TrajectoryPoint format
  - Handle connection errors

**Interface:**
```python
# src/camera.py
def read_camera_frame() -> TrajectoryPoint:
    """Read single frame from ToF camera."""
    pass

def track_object() -> List[TrajectoryPoint]:
    """Track object until landing."""
    pass
```

### Phase 2: Servo Control (AFTER CAMERA)
**Goal:** Move catch mechanism to predicted landing position

**Files to Create:**
- `src/servo.py` - Pan/tilt servo controller
  - Convert (x, y) → servo angles
  - Smooth movement with acceleration limits
  - Emergency stop
  - Position feedback

- `src/controller.py` - Real-time control loop
  - Track object with camera
  - Update prediction continuously
  - Command servos to intercept
  - Handle timing constraints

**Interface:**
```python
# src/servo.py
def move_to_position(x_m: float, y_m: float, time_to_arrival: float):
    """Move catch mechanism to intercept position."""
    pass

def calculate_servo_angles(x_m: float, y_m: float) -> Tuple[float, float]:
    """Convert XY coordinates to pan/tilt angles."""
    pass

# src/controller.py
def tracking_loop():
    """Main real-time control loop."""
    while True:
        # 1. Read camera frame
        # 2. Update trajectory prediction
        # 3. Command servos if confident
        # 4. Repeat at 30 Hz
        pass
```

### Phase 3: Integration Testing
- Test with real trash throws
- Tune timing parameters
- Adjust servo speeds
- Validate success rate

## Code Style & Standards

### Type Hints (Required)
```python
def predict_landing(points: List[TrajectoryPoint]) -> Optional[Prediction]:
    """Always include type hints."""
    pass
```

### Docstrings (Required)
```python
def calculate_landing(start_pos, start_vel, catch_height):
    """
    Calculate where and when object lands.

    Args:
        start_pos: (x, y, z) starting position in meters
        start_vel: (vx, vy, vz) starting velocity in m/s
        catch_height: height of catch plane in meters

    Returns:
        ((landing_x, landing_y), flight_time)
    """
```

### Comments for Complex Logic
```python
# Solve quadratic: 0.5*g*t^2 - vz*t + (catch_height - z0) = 0
# Use quadratic formula, take larger positive root
discriminant = b*b - 4*a*c
```

### Configuration Over Hardcoding
```python
# ❌ Bad
fov = 70
fps = 30

# ✅ Good
import config
fov = config.CAMERA_FOV_DEGREES
fps = config.CAMERA_FPS
```

## Project Rules

### DO
✅ Run tests before committing
✅ Use dataclasses for structured data
✅ Keep functions modular and testable
✅ Document complex physics/math
✅ Validate accuracy with benchmarks

### DON'T
❌ Add ML until physics baseline proven (baseline proven ✅)
❌ Change TrajectoryPoint/Prediction interfaces without updating consumers
❌ Hardcode values that belong in config.py
❌ Commit without passing tests
❌ Optimize prematurely

## Deployment Checklist (Hardware)

### Before Deploying to Robot Computer:
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Benchmark accuracy >80%: `python3 scripts/run_benchmark.py 100`
- [ ] Config values match hardware specs
- [ ] Camera driver installed (ArduCam)
- [ ] Servo library installed
- [ ] Python 3.8+ on robot computer
- [ ] Requirements installed: `pip install -r requirements.txt`

### Files to Transfer:
```
trash-catcher/
├── config.py           # Tuned parameters
├── requirements.txt
├── src/
│   ├── predictor.py   # Core prediction logic
│   ├── camera.py      # NEW: Camera driver
│   └── servo.py       # NEW: Servo control
└── tests/             # For validation on robot
```

### Performance Targets:
- Prediction latency: <33ms (30 FPS)
- Servo response time: <100ms
- End-to-end latency: <200ms
- Success rate: >70% (real-world, with noise)

## Troubleshooting

### Tests Failing
```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test
pytest tests/test_predictor.py::test_name -v
```

### Accuracy Drop
```bash
# Check benchmark
python3 scripts/run_benchmark.py 100

# Visualize failures
python3 scripts/run_visualization.py
```

### Import Errors
```bash
# Ensure you're in project root
cd /path/to/trash-catcher

# Scripts need parent directory in path (handled automatically)
python3 scripts/run_single_throw.py
```

## Performance Metrics

**Current Simulation Results (100 throws):**
- Success rate (< 10cm): **89.6%** ✅
- Mean error: **5.0cm**
- Median error: **3.1cm**
- Best: **0.3cm**
- Worst: **28.0cm**

**Edge Case (FOV Entry):**
- Trajectory visibility: **56-61%**
- Prediction error: **0-2cm** ✅
- Demonstrates robustness to partial data

## Resources

### Key Equations
- Projectile motion: `z(t) = z₀ + v_z·t - ½g·t²`
- Horizontal motion: `x(t) = x₀ + v_x·t` (no air resistance)
- FOV check: `angle_from_vertical < FOV/2`

### Dependencies
- numpy: Numerical computing
- matplotlib: Visualization
- pytest: Testing framework
- pillow: GIF animation export

### Future Enhancements
- [ ] ML predictor for comparison
- [ ] Air resistance model
- [ ] Multiple object tracking
- [ ] Success rate optimization
- [ ] Web dashboard for live monitoring

---

**Version:** 1.0 (Simulation validated)
**Next Phase:** Hardware integration
**Contact:** Ready for robot computer deployment
