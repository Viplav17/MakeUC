import google.generativeai as genai
from typing import List, Optional
from PIL import Image
from config_loader import get_config


class GeminiBlenderClient:
    
    def __init__(self):
        cfg = get_config()
        key = cfg.get('ai', 'gemini', 'api_key', default='')
        model = cfg.get('ai', 'gemini', 'model', default='gemini-2.5-pro')
        
        if not key:
            raise ValueError("Gemini API key not configured")
        
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel(model)
    
    def generate_blender_code(
        self,
        imgs: List[Image.Image],
        dist: float,
        mod: Optional[str] = None
    ) -> str:
        if not imgs:
            raise ValueError("No images provided")
        
        mod_text = f"\n\nMODIFICATION:\n{mod}\nApply this to the model." if mod else ""
        
        prompt = f"""You are an expert 3D modeler using Blender Python API (bpy). Analyze these {len(imgs)} images and generate Python code that recreates this object.

CONTEXT:
- Object is {dist}cm from camera
- Scale: {dist}cm = {dist/100:.3f} Blender units (1 unit ≈ 1 meter)
- {len(imgs)} views from 360° rotation
- Object is centered on turntable

TASK:
Generate executable Blender Python code (bpy) that:
1. Creates 3D geometry matching the object
2. Applies materials and colors
3. Uses accurate scale from {dist}cm distance
4. Includes visible features and textures
5. Creates production-ready model

REQUIREMENTS:
- Use ONLY bpy (no external libraries)
- Start with clean scene
- Use bpy.ops.mesh primitives or methods
- Apply materials with colors from images
- Use accurate scale
- Export-ready geometry
- Include comments for major steps

{mod_text}

IMPORTANT:
- Return ONLY Python code, no markdown
- Code must be complete and executable
- Focus on accuracy
- Use appropriate Blender units

Generate the code:"""
        
        try:
            img_parts = list(imgs)
            config = {
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 30,
                "max_output_tokens": 4096,
            }
            
            resp = self.model.generate_content(
                [prompt] + img_parts,
                generation_config=config
            )
            
            if not resp.text:
                raise ValueError("Empty response from Gemini")
            
            code = resp.text.strip()
            
            if code.startswith("```python"):
                code = code[9:]
            elif code.startswith("```"):
                code = code[3:]
            
            if code.endswith("```"):
                code = code[:-3]
            
            return code.strip()
        
        except Exception as e:
            raise Exception(f"Gemini error: {str(e)}")
    
    def analyze_object(self, imgs: List[Image.Image], dist: float) -> str:
        code = self.generate_blender_code(imgs, dist)
        return f"Code generated ({len(code)} chars)"
