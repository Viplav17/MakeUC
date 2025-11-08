import os
import subprocess
import tempfile
import shutil
import time
import re
from typing import Optional
from config_loader import get_config


class BlenderClient:
    
    def __init__(self):
        cfg = get_config()
        self.format = cfg.get('ai', 'reconstruction', 'output_format', default='glb')
        self.blender_path = cfg.get('ai', 'reconstruction', 'blender_path', default='blender')
        self.config = cfg
        self.output_dir = 'models'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _sanitize_code(self, raw_code: str) -> str:
        code = raw_code.strip()
        
        code = re.sub(r'^```python\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'\s*```\s*$', '', code, flags=re.MULTILINE)
        
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith('```'):
                continue
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines).strip()
        
        while code.startswith('```'):
            code = code[3:].strip()
        while code.endswith('```'):
            code = code[:-3].strip()
        
        return code
    
    def generate_3d_model(self, code: str, progress_callback=None) -> Optional[str]:
        try:
            if progress_callback:
                progress_callback("Preparing script...", 10)
            
            sanitized_code = self._sanitize_code(code)
            
            script_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
            script_path = script_file.name
            
            try:
                full_script = self._wrap_code(sanitized_code, script_path)
                script_file.write(full_script)
                script_file.close()
                
                if progress_callback:
                    progress_callback("Executing Blender...", 30)
                
                output_path = self._run_script(script_path, progress_callback)
                return output_path
            
            finally:
                try:
                    os.unlink(script_path)
                except:
                    pass
        
        except Exception as e:
            raise Exception(f"Blender error: {str(e)}")
    
    def _wrap_code(self, user_code: str, script_path: str) -> str:
        ts = int(time.time())
        filename = f"model_{ts}.{self.format}"
        output_path = os.path.join(self.output_dir, filename)
        output_abs = os.path.abspath(output_path)
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        wrapper = f"""import bpy
import sys
import os

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

{user_code}

output_path = r"{output_abs}"

try:
    bpy.ops.object.select_all(action='SELECT')
    
    if "{self.format}" == "glb":
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            use_selection=True
        )
    elif "{self.format}" == "obj":
        bpy.ops.export_scene.obj(
            filepath=output_path,
            use_selection=True
        )
    elif "{self.format}" == "fbx":
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            use_selection=True
        )
    elif "{self.format}" == "ply":
        bpy.ops.wm.ply_export(filepath=output_path)
    else:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            use_selection=True
        )
    
    print(f"SUCCESS: Model exported to {{output_path}}")
    
except Exception as e:
    print(f"ERROR: Export failed: {{e}}")
    sys.exit(1)
"""
        return wrapper
    
    def _run_script(self, script_path: str, progress_callback=None) -> str:
        if progress_callback:
            progress_callback("Running Blender...", 50)
        
        blender_cmd = self._find_blender()
        
        cmd = [
            blender_cmd,
            '--background',
            '--python', script_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise Exception(f"Blender failed: {error_msg}")
            
            output_path = self._extract_path(result.stdout)
            
            if not output_path or not os.path.exists(output_path):
                raise Exception("Model file not created")
            
            if progress_callback:
                progress_callback("Model generated!", 100)
            
            return output_path
        
        except subprocess.TimeoutExpired:
            raise Exception("Blender timed out")
        except FileNotFoundError:
            raise Exception(f"Blender not found: {blender_cmd}")
    
    def _find_blender(self) -> str:
        configured = self.config.get('ai', 'reconstruction', 'blender_path', default='')
        if configured and os.path.exists(configured):
            return configured
        
        paths = [
            'blender',
            'blender.exe',
            '/usr/bin/blender',
            '/Applications/Blender.app/Contents/MacOS/blender',
            'C:\\Program Files\\Blender Foundation\\Blender\\blender.exe',
        ]
        
        for path in paths:
            if shutil.which(path):
                return path
        
        return 'blender'
    
    def _extract_path(self, stdout: str) -> Optional[str]:
        for line in stdout.split('\n'):
            if 'SUCCESS:' in line and 'Model exported to' in line:
                parts = line.split('Model exported to')
                if len(parts) > 1:
                    path = parts[1].strip()
                    if os.path.exists(path):
                        return path
        return None
