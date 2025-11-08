import asyncio
import os
from datetime import datetime
from typing import List, Optional, Callable
from PIL import Image
from hardware import Turntable, DepthSensor, Camera
from api_Clients import GeminiBlenderClient, BlenderClient
from config_loader import get_config


class Scanner:
    
    def __init__(self):
        self.config = get_config()
        self.turntable = Turntable()
        self.depth_sensor = DepthSensor()
        self.camera = Camera()
        self.gemini = None
        self.blender = None
        self.delay = self.config.get('app', 'scan_delay_seconds', default=0.3)
        self.steps = self.config.get('hardware', 'turntable', 'steps_per_scan', default=8)
        self.quality = self.config.get('app', 'image_quality', default=85)
        self.scans_dir = 'scans'
        os.makedirs(self.scans_dir, exist_ok=True)
        self.scan_id = None
        self.last_dir = None
    
    def _init_clients(self):
        if self.gemini is None:
            try:
                self.gemini = GeminiBlenderClient()
            except Exception as e:
                raise Exception(f"Gemini init failed: {e}")
        if self.blender is None:
            try:
                self.blender = BlenderClient()
            except Exception as e:
                raise Exception(f"Blender init failed: {e}")
    
    def _load_scan(self, scan_id: Optional[str] = None) -> Optional[tuple[List[Image.Image], float]]:
        if scan_id is None:
            if not os.path.exists(self.scans_dir):
                return None
            dirs = [d for d in os.listdir(self.scans_dir) 
                   if os.path.isdir(os.path.join(self.scans_dir, d))]
            if not dirs:
                return None
            scan_id = sorted(dirs)[-1]
        
        scan_dir = os.path.join(self.scans_dir, scan_id)
        if not os.path.exists(scan_dir):
            return None
        
        dist_file = os.path.join(scan_dir, 'distance.txt')
        dist = 15.0
        if os.path.exists(dist_file):
            try:
                with open(dist_file, 'r') as f:
                    dist = float(f.read().strip())
            except:
                pass
        
        imgs = []
        for i in range(self.steps):
            img_path = os.path.join(scan_dir, f'angle_{i:03d}.jpg')
            if os.path.exists(img_path):
                try:
                    imgs.append(Image.open(img_path))
                except:
                    pass
        
        if len(imgs) == self.steps:
            self.last_dir = scan_dir
            return imgs, dist
        return None
    
    async def scan_object(
        self,
        on_progress: Optional[Callable[[str, int], None]] = None,
        cancel: Optional[asyncio.Event] = None
    ) -> tuple[List[Image.Image], float]:
        imgs = []
        
        if cancel and cancel.is_set():
            raise asyncio.CancelledError("Cancelled")
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.scan_id = ts
        scan_dir = os.path.join(self.scans_dir, ts)
        os.makedirs(scan_dir, exist_ok=True)
        self.last_dir = scan_dir
        
        if on_progress:
            on_progress("Measuring distance...", 5)
        
        dist = self.depth_sensor.measure_distance()
        
        with open(os.path.join(scan_dir, 'distance.txt'), 'w') as f:
            f.write(f"{dist}\n")
        
        if on_progress:
            on_progress("Resetting turntable...", 10)
        self.turntable.reset_position()
        
        for step in range(self.steps):
            if cancel and cancel.is_set():
                raise asyncio.CancelledError("Cancelled")
            
            if on_progress:
                p = 10 + int((step / self.steps) * 40)
                on_progress(f"Capturing {step + 1}/{self.steps}...", p)
            
            if step > 0:
                self.turntable.rotate_step()
                await asyncio.sleep(self.delay)
            
            img = self.camera.capture_image()
            if img:
                imgs.append(img)
                img_path = os.path.join(scan_dir, f'angle_{step:03d}.jpg')
                img.save(img_path, 'JPEG', quality=self.quality, optimize=True)
            
            await asyncio.sleep(0.05)
        
        if on_progress:
            on_progress("Scan complete!", 50)
        
        return imgs, dist
    
    def _optimize_images(self, imgs: List[Image.Image]) -> List[Image.Image]:
        result = []
        max_size = self.config.get('app', 'gemini_image_max_size', default=1024)
        
        for img in imgs:
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.BILINEAR)
            result.append(img)
        
        return result
    
    async def generate_code(
        self,
        imgs: List[Image.Image],
        dist: float,
        mod: Optional[str] = None,
        on_progress: Optional[Callable[[str, int], None]] = None,
        cancel: Optional[asyncio.Event] = None
    ) -> str:
        if cancel and cancel.is_set():
            raise asyncio.CancelledError("Cancelled")
        
        if on_progress:
            on_progress("Optimizing images...", 55)
        
        opt_imgs = self._optimize_images(imgs)
        
        max_imgs = self.config.get('app', 'gemini_max_images', default=8)
        if len(opt_imgs) > max_imgs:
            step = len(opt_imgs) / max_imgs
            opt_imgs = [opt_imgs[int(i * step)] for i in range(max_imgs)]
        
        if on_progress:
            on_progress("Generating code...", 60)
        
        self._init_clients()
        
        if cancel and cancel.is_set():
            raise asyncio.CancelledError("Cancelled")
        
        loop = asyncio.get_event_loop()
        code = await loop.run_in_executor(
            None,
            lambda: self.gemini.generate_blender_code(opt_imgs, dist, mod)
        )
        
        if cancel and cancel.is_set():
            raise asyncio.CancelledError("Cancelled")
        
        if on_progress:
            on_progress("Code generated!", 70)
        
        return code
    
    async def generate_model(
        self,
        imgs: List[Image.Image],
        dist: float,
        mod: Optional[str] = None,
        on_progress: Optional[Callable[[str, int], None]] = None,
        use_prev: bool = False,
        cancel: Optional[asyncio.Event] = None
    ) -> Optional[str]:
        self._init_clients()
        
        if use_prev:
            if on_progress:
                on_progress("Loading previous scan...", 50)
            data = self._load_scan()
            if data:
                imgs, dist = data
            else:
                raise Exception("No previous scan found")
        
        if not imgs:
            raise Exception("No images available")
        
        if cancel and cancel.is_set():
            raise asyncio.CancelledError("Cancelled")
        
        code = await self.generate_code(imgs, dist, mod, on_progress, cancel)
        
        if cancel and cancel.is_set():
            raise asyncio.CancelledError("Cancelled")
        
        if on_progress:
            on_progress("Executing Blender...", 75)
        
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(
            None,
            lambda: self.blender.generate_3d_model(
                code,
                progress_callback=lambda s, p: (
                    on_progress(s, 75 + int(p * 0.25)) if on_progress else None
                )
            )
        )
        
        if cancel and cancel.is_set():
            raise asyncio.CancelledError("Cancelled")
        
        if self.last_dir and path:
            with open(os.path.join(self.last_dir, 'model_path.txt'), 'w') as f:
                f.write(f"{path}\n")
            if mod:
                with open(os.path.join(self.last_dir, 'modification.txt'), 'w') as f:
                    f.write(f"{mod}\n")
        
        return path
    
    async def full_scan(
        self,
        on_progress: Optional[Callable[[str, int], None]] = None,
        cancel: Optional[asyncio.Event] = None
    ) -> Optional[str]:
        try:
            if cancel and cancel.is_set():
                return None
            
            imgs, dist = await self.scan_object(on_progress, cancel)
            
            if not imgs:
                raise Exception("No images captured")
            
            if cancel and cancel.is_set():
                return None
            
            path = await self.generate_model(imgs, dist, None, on_progress, False, cancel)
            
            if on_progress:
                on_progress("Complete!", 100)
            
            return path
        
        except asyncio.CancelledError:
            if on_progress:
                on_progress("Cancelled", 0)
            return None
        except Exception as e:
            if on_progress:
                on_progress(f"Error: {str(e)}", -1)
            raise
    
    def cleanup(self):
        self.camera.close()
        if hasattr(self.turntable, 'cleanup'):
            self.turntable.cleanup()
        if hasattr(self.depth_sensor, 'cleanup'):
            self.depth_sensor.cleanup()
