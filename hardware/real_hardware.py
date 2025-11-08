"""
Real Hardware Implementations for Raspberry Pi

These implementations use actual GPIO and camera hardware.
Only works on Raspberry Pi with proper hardware connected.
"""
import time
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from PIL import Image
from typing import Optional
from config_loader import get_config


class Turntable:
    """Real turntable controller using GPIO to control DC motor."""
    
    def __init__(self):
        """Initialize turntable with GPIO control."""
        self.config = get_config()
        self.burst_duration = self.config.get('hardware', 'turntable', 'burst_duration_ms', default=500) / 1000.0
        
        # GPIO pin for motor control (adjust based on your wiring)
        self.motor_pin = 12  # GPIO pin connected to motor driver
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.motor_pin, GPIO.OUT)
        self.motor_pwm = GPIO.PWM(self.motor_pin, 1000)  # 1kHz PWM
        self.motor_pwm.start(0)
        
        self.is_rotating = False
        self.current_position = 0.0
    
    def rotate_step(self) -> bool:
        """
        Rotate turntable by one step (~45 degrees).
        
        Returns:
            bool: True if rotation successful
        """
        if self.is_rotating:
            return False
        
        self.is_rotating = True
        try:
            # Start motor at 50% duty cycle
            self.motor_pwm.ChangeDutyCycle(50)
            time.sleep(self.burst_duration)
            # Stop motor
            self.motor_pwm.ChangeDutyCycle(0)
            
            self.current_position = (self.current_position + 45) % 360
            return True
        finally:
            self.is_rotating = False
    
    def reset_position(self):
        """Reset turntable to starting position."""
        # Rotate back to 0 (simplified - in production might need encoder)
        steps_to_reset = int(self.current_position / 45)
        for _ in range(steps_to_reset):
            self.rotate_step()
        self.current_position = 0.0
    
    def get_position(self) -> float:
        """Get current turntable position in degrees."""
        return self.current_position
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        self.motor_pwm.stop()
        GPIO.cleanup(self.motor_pin)


class DepthSensor:
    """Real HC-SR04 ultrasonic distance sensor."""
    
    def __init__(self):
        """Initialize depth sensor with GPIO pins."""
        self.config = get_config()
        self.trigger_pin = self.config.get('hardware', 'depth_sensor', 'trigger_pin', default=18)
        self.echo_pin = self.config.get('hardware', 'depth_sensor', 'echo_pin', default=24)
        self.timeout_us = self.config.get('hardware', 'depth_sensor', 'timeout_us', default=30000)
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        # Initialize trigger to low
        GPIO.output(self.trigger_pin, False)
        time.sleep(0.1)  # Stabilize sensor
    
    def measure_distance(self) -> float:
        """
        Measure distance to object in centimeters.
        
        Returns:
            float: Distance in cm
        """
        # Send trigger pulse
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)  # 10 microseconds
        GPIO.output(self.trigger_pin, False)
        
        # Wait for echo
        start_time = time.time()
        timeout = self.timeout_us / 1000000.0  # Convert to seconds
        
        while GPIO.input(self.echo_pin) == 0:
            if time.time() - start_time > timeout:
                return -1.0  # Timeout
            start_time = time.time()
        
        pulse_start = time.time()
        
        while GPIO.input(self.echo_pin) == 1:
            if time.time() - pulse_start > timeout:
                return -1.0  # Timeout
            pulse_end = time.time()
        
        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        # Speed of sound = 34300 cm/s
        # Distance = (pulse_duration * speed_of_sound) / 2 (round trip)
        distance = (pulse_duration * 34300) / 2
        
        return round(distance, 2)
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        GPIO.cleanup([self.trigger_pin, self.echo_pin])


class Camera:
    """Real Raspberry Pi camera using picamera2."""
    
    def __init__(self):
        """Initialize Pi camera."""
        self.config = get_config()
        self.width = self.config.get('hardware', 'camera', 'resolution_width', default=1920)
        self.height = self.config.get('hardware', 'camera', 'resolution_height', default=1080)
        self.rotation = self.config.get('hardware', 'camera', 'rotation', default=0)
        
        # Initialize camera
        self.camera = Picamera2()
        
        # Configure camera
        camera_config = self.camera.create_still_configuration(
            main={"size": (self.width, self.height)}
        )
        self.camera.configure(camera_config)
        self.camera.start()
        
        # Allow camera to stabilize
        time.sleep(2)
    
    def capture_image(self) -> Optional[Image.Image]:
        """
        Capture an image from the camera.
        
        Returns:
            PIL Image or None if capture fails
        """
        try:
            # Capture image
            array = self.camera.capture_array()
            
            # Convert to PIL Image
            img = Image.fromarray(array)
            
            # Apply rotation if needed
            if self.rotation != 0:
                img = img.rotate(self.rotation, expand=True)
            
            return img
        except Exception as e:
            print(f"Error capturing image: {e}")
            return None
    
    def close(self):
        """Close camera resources."""
        if hasattr(self, 'camera'):
            self.camera.stop()
            self.camera.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()

