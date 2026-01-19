"""
Configuration for trash catcher simulation.
All units are meters and seconds unless noted.
"""

# Camera settings (matches ArduCam ToF specs)
CAMERA_FOV_DEGREES = 70  # diagonal field of view
CAMERA_MAX_RANGE_M = 4.0  # max depth detection
CAMERA_FPS = 30  # frames per second
CAMERA_RESOLUTION = (240, 180)  # width, height in pixels
CAMERA_DEPTH_NOISE_M = 0.02  # +/- 2cm accuracy

# Camera position (camera faces UP from this position)
CAMERA_POSITION = (0.0, 0.0, 0.0)  # x, y, z in meters

# Catch plane (where the robot catches objects)
CATCH_PLANE_HEIGHT_M = 0.3  # 30cm above ground

# Physics
GRAVITY_M_S2 = 9.81

# Prediction settings
MIN_FRAMES_FOR_PREDICTION = 5  # need at least this many points
MAX_FRAMES_FOR_PREDICTION = 15  # don't use more than this (old data)

# Simulation defaults
DEFAULT_THROW_HEIGHT_M = 2.5  # typical release height
DEFAULT_THROW_VELOCITY_M_S = 5.0  # typical throw speed
