import time
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from PIL import Image
from typing import Optional
from config_loader import get_config


class Turntable:
    
    def __init__(self):
        self.config = get_config()
        self.burst_duration = self.config.get('hardware', 'turntable', 'burst_duration_ms', default=500) / 1000.0
        
        self.motor_pin = 12
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.motor_pin, GPIO.OUT)
        self.motor_pwm = GPIO.PWM(self.motor_pin, 1000)
        self.motor_pwm.start(0)
        
        self.is_rotating = False
        self.current_position = 0.0
    
    def rotate_step(self) -> bool:
        if self.is_rotating:
            return False
        
        self.is_rotating = True
        try:
            self.motor_pwm.ChangeDutyCycle(50)
            time.sleep(self.burst_duration)
            self.motor_pwm.ChangeDutyCycle(0)
            
            self.current_position = (self.current_position + 45) % 360
            return True
        finally:
            self.is_rotating = False
    
    def reset_position(self):
        steps_to_reset = int(self.current_position / 45)
        for _ in range(steps_to_reset):
            self.rotate_step()
        self.current_position = 0.0
    
    def get_position(self) -> float:
        return self.current_position
    
    def cleanup(self):
        self.motor_pwm.stop()
        GPIO.cleanup(self.motor_pin)


class DepthSensor:
    
    def __init__(self):
        self.config = get_config()
        self.trigger_pin = self.config.get('hardware', 'depth_sensor', 'trigger_pin', default=18)
        self.echo_pin = self.config.get('hardware', 'depth_sensor', 'echo_pin', default=24)
        self.timeout_us = self.config.get('hardware', 'depth_sensor', 'timeout_us', default=30000)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        GPIO.output(self.trigger_pin, False)
        time.sleep(0.1)
    
    def measure_distance(self) -> float:
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, False)
        
        start_time = time.time()
        timeout = self.timeout_us / 1000000.0
        
        while GPIO.input(self.echo_pin) == 0:
            if time.time() - start_time > timeout:
                return -1.0
            start_time = time.time()
        
        pulse_start = time.time()
        
        while GPIO.input(self.echo_pin) == 1:
            if time.time() - pulse_start > timeout:
                return -1.0
            pulse_end = time.time()
        
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2
        
        return round(distance, 2)
    
    def cleanup(self):
        GPIO.cleanup([self.trigger_pin, self.echo_pin])


class Camera:
    
    def __init__(self):
        self.config = get_config()
        self.width = self.config.get('hardware', 'camera', 'resolution_width', default=1920)
        self.height = self.config.get('hardware', 'camera', 'resolution_height', default=1080)
        self.rotation = self.config.get('hardware', 'camera', 'rotation', default=0)
        
        self.camera = Picamera2()
        
        camera_config = self.camera.create_still_configuration(
            main={"size": (self.width, self.height)}
        )
        self.camera.configure(camera_config)
        self.camera.start()
        
        time.sleep(2)
    
    def capture_image(self) -> Optional[Image.Image]:
        try:
            array = self.camera.capture_array()
            
            img = Image.fromarray(array)
            
            if self.rotation != 0:
                img = img.rotate(self.rotation, expand=True)
            
            return img
        except Exception as e:
            print(f"Error capturing image: {e}")
            return None
    
    def close(self):
        if hasattr(self, 'camera'):
            self.camera.stop()
            self.camera.close()
    
    def __del__(self):
        self.close()
