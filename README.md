# Trash Catcher MVP - Simulation

Simulation software to test trajectory prediction for a trash-catching robot.

## What This Does

Simulates an upward-facing ToF camera tracking falling objects and predicting where they'll land.

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Run single simulation
python scripts/run_single_throw.py

# Run accuracy benchmark
python scripts/run_benchmark.py 100

# See prediction improve over time
python scripts/run_visualization.py
```

## Project Structure

```
trash-catcher/
├── CLAUDE.md           # Guide for Claude Code
├── config.py           # All tunable parameters
├── src/
│   ├── simulator.py    # Generates fake throw data
│   ├── predictor.py    # Predicts landing position
│   └── visualizer.py   # 3D visualization
├── tests/              # Unit tests
├── scripts/            # Runnable demos
└── skills/             # Claude Code skills
```

## Key Parameters (config.py)

- `CAMERA_FOV_DEGREES`: Camera field of view (default: 70°)
- `CAMERA_FPS`: Frames per second (default: 30)
- `CAMERA_MAX_RANGE_M`: Max detection distance (default: 4m)
- `CATCH_PLANE_HEIGHT_M`: Height of catch mechanism (default: 0.3m)
- `MIN_FRAMES_FOR_PREDICTION`: Minimum data points needed (default: 5)

## Success Criteria

Target: >80% of predictions within 10cm of actual landing.

Run `python scripts/run_benchmark.py 100` to check current accuracy.

## Next Steps

1. Connect real ArduCam ToF camera
2. Replace simulator with real camera input
3. Add servo control for catch mechanism
