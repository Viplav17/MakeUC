"""
Hardware Abstraction Layer

Provides unified interface for hardware components with automatic
platform detection and mock fallback for development.
"""
from platform_detector import is_raspberry_pi

# Import appropriate implementations based on platform
if is_raspberry_pi():
    from .real_hardware import Turntable, DepthSensor, Camera
else:
    from .mock_hardware import Turntable, DepthSensor, Camera

__all__ = ['Turntable', 'DepthSensor', 'Camera']

