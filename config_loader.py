import os
import yaml
from typing import Dict, Any


class Config:
    
    def __init__(self, path: str = 'config.yaml'):
        self.path = path
        self._config = self._load()
        self._apply_env()
    
    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file {self.path} not found. Using defaults.")
            return self._defaults()
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return self._defaults()
    
    def _defaults(self) -> Dict[str, Any]:
        return {
            'hardware': {
                'turntable': {
                    'burst_duration_ms': 500,
                    'steps_per_scan': 8
                },
                'depth_sensor': {
                    'trigger_pin': 18,
                    'echo_pin': 24,
                    'timeout_us': 30000
                },
                'camera': {
                    'resolution_width': 1920,
                    'resolution_height': 1080,
                    'rotation': 0
                }
            },
            'ai': {
                'gemini': {
                    'api_key': '',
                    'model': 'gemini-2.5-pro'
                },
                'reconstruction': {
                    'method': 'blender_bpy',
                    'output_format': 'glb',
                    'blender_path': 'blender'
                }
            },
            'app': {
                'scan_delay_seconds': 0.5,
                'mock_delay_seconds': 0.5,
                'voice_enabled': False
            }
        }
    
    def _apply_env(self):
        if 'GEMINI_API_KEY' in os.environ:
            self._config['ai']['gemini']['api_key'] = os.environ['GEMINI_API_KEY']
    
    def get(self, *keys, default=None):
        val = self._config
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
                if val is None:
                    return default
            else:
                return default
        return val
    
    def set(self, *keys, value):
        cfg = self._config
        for key in keys[:-1]:
            if key not in cfg:
                cfg[key] = {}
            cfg = cfg[key]
        cfg[keys[-1]] = value


_config = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
