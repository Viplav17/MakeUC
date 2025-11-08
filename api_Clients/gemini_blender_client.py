import google.generativeai as genai
import re
from typing import List, Optional
from PIL import Image
from config_loader import get_config


class GeminiBlenderClient:
    
    def __init__(self):
        config = get_config()
        api_key = config.get('ai', 'gemini', 'api_key', default='')
        model_name = config.get('ai', 'gemini', 'model', default='gemini-2.5-pro')
        
        if not api_key:
            raise ValueError("Gemini API key not configured")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
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
    
    def generate_blender_code(
        self,
        imgs: List[Image.Image],
        dist: float,
        mod: Optional[str] = None
    ) -> str:
        if not imgs:
            raise ValueError("No images provided")
        
        modification_instruction = f"\n\nMODIFICATION REQUEST:\n{mod}\nApply this modification to the model." if mod else ""
        
        system_prompt = f"""You are an expert 3D modeler using Blender Python API (bpy) version 4.0 or higher. Analyze these {len(imgs)} images and generate Python code that recreates this object procedurally.

CONTEXT:
- Object is {dist}cm from camera
- Scale: {dist}cm = {dist/100:.3f} Blender units (1 unit = 1 meter)
- {len(imgs)} views from 360° rotation
- Object is centered on turntable

CRITICAL REQUIREMENTS (MUST FOLLOW):
1. DELETE THE DEFAULT CUBE FIRST: bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
2. Use ONLY standard Blender primitives (cylinders for mugs/cups, spheres for balls/apples, cubes for boxes, etc.)
3. Combine primitives to match the object shape
4. Apply materials with colors matching the images
5. Use accurate scale based on {dist}cm distance
6. Code must be Blender 4.0+ compatible
7. Code must be standalone and executable
8. DO NOT include export commands - export is handled automatically by the system

{modification_instruction}

OUTPUT FORMAT:
- Return ONLY Python code
- NO markdown backticks
- NO explanations
- NO comments
- Pure executable bpy code
- Code must start immediately with import statements

Generate the code:"""
        
        try:
            image_list = list(imgs)
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 30,
                "max_output_tokens": 4096,
            }
            
            response = self.model.generate_content(
                [system_prompt] + image_list,
                generation_config=generation_config
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini")
            
            sanitized_code = self._sanitize_code(response.text)
            
            if not sanitized_code:
                raise ValueError("No code extracted from response")
            
            return sanitized_code
        
        except Exception as e:
            raise Exception(f"Gemini error: {str(e)}")
    
    def analyze_object(self, imgs: List[Image.Image], dist: float) -> str:
        generated_code = self.generate_blender_code(imgs, dist)
        return f"Code generated ({len(generated_code)} chars)"
