import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import asyncio
import threading
import time
import os
from typing import Optional
from scanner import Scanner
from config_loader import get_config


class MainWindow:
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("The Lighthouse - Interactive AI 3D Scanner")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a1a')
        
        self.scanner = Scanner()
        self.scan_task = None
        self.cancel_event = None
        self.current_model_url = None
        
        self._setup_ui()
        self._setup_async_loop()
    
    def _setup_ui(self):
        header = tk.Frame(self.root, bg='#1a1a1a', pady=20)
        header.pack(fill=tk.X)
        
        title = tk.Label(
            header,
            text="The Lighthouse",
            font=('Arial', 32, 'bold'),
            fg='#ffffff',
            bg='#1a1a1a'
        )
        title.pack()
        
        subtitle = tk.Label(
            header,
            text="Interactive AI 3D Scanner",
            font=('Arial', 14),
            fg='#aaaaaa',
            bg='#1a1a1a'
        )
        subtitle.pack()
        
        content = tk.Frame(self.root, bg='#1a1a1a')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        left = tk.Frame(content, bg='#2a2a2a', width=300)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)
        
        self.scan_button = tk.Button(
            left,
            text="SCAN",
            font=('Arial', 24, 'bold'),
            bg='#4CAF50',
            fg='white',
            activebackground='#45a049',
            activeforeground='white',
            relief=tk.FLAT,
            padx=40,
            pady=30,
            command=self._on_scan_clicked,
            cursor='hand2'
        )
        self.scan_button.pack(pady=30)
        
        progress_frame = tk.Frame(left, bg='#2a2a2a')
        progress_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.progress_label = tk.Label(
            progress_frame,
            text="Ready to scan",
            font=('Arial', 12),
            fg='#ffffff',
            bg='#2a2a2a',
            wraplength=250
        )
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=250
        )
        self.progress_bar.pack(pady=10)
        
        self.cancel_button = tk.Button(
            left,
            text="Cancel",
            font=('Arial', 12),
            bg='#f44336',
            fg='white',
            activebackground='#da190b',
            activeforeground='white',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self._on_cancel_clicked,
            cursor='hand2'
        )
        
        voice_frame = tk.LabelFrame(
            left,
            text="Voice Modification",
            font=('Arial', 12, 'bold'),
            fg='#ffffff',
            bg='#2a2a2a',
            padx=10,
            pady=10
        )
        voice_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.voice_entry = tk.Entry(
            voice_frame,
            font=('Arial', 11),
            bg='#3a3a3a',
            fg='#ffffff',
            insertbackground='#ffffff',
            relief=tk.FLAT,
            width=25
        )
        self.voice_entry.pack(pady=5)
        self.voice_entry.insert(0, "e.g., 'Turn it into gold'")
        
        self.modify_button = tk.Button(
            voice_frame,
            text="Modify 3D Model",
            font=('Arial', 11),
            bg='#2196F3',
            fg='white',
            activebackground='#0b7dda',
            activeforeground='white',
            relief=tk.FLAT,
            padx=15,
            pady=8,
            command=self._on_modify_clicked,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.modify_button.pack(pady=5)
        
        right = tk.Frame(content, bg='#2a2a2a')
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.display_label = tk.Label(
            right,
            text="Place object on turntable\nand click SCAN to begin",
            font=('Arial', 18),
            fg='#888888',
            bg='#2a2a2a',
            justify=tk.CENTER
        )
        self.display_label.pack(expand=True)
        
        self.status_text = scrolledtext.ScrolledText(
            right,
            font=('Arial', 10),
            bg='#1a1a1a',
            fg='#cccccc',
            wrap=tk.WORD,
            relief=tk.FLAT,
            height=10
        )
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.status_text.config(state=tk.DISABLED)
    
    def _setup_async_loop(self):
        loop_ref = {'loop': None}
        
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_ref['loop'] = loop
            loop.run_forever()
        
        self.async_thread = threading.Thread(target=run_loop, daemon=True)
        self.async_thread.start()
        
        while loop_ref['loop'] is None:
            time.sleep(0.01)
        
        self.async_loop = loop_ref['loop']
    
    def _run_async(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.async_loop)
        return future
    
    def _update_progress(self, msg: str, prog: int):
        self.root.after(0, lambda: self._update_progress_sync(msg, prog))
    
    def _update_progress_sync(self, msg: str, prog: int):
        self.progress_label.config(text=msg)
        if prog >= 0:
            self.progress_bar['value'] = prog
        else:
            self.progress_bar['value'] = 0
    
    def _on_scan_clicked(self):
        if self.scan_task and not self.scan_task.done():
            return
        
        self.scan_button.config(state=tk.DISABLED)
        self.cancel_button.pack(pady=10)
        self.progress_bar['value'] = 0
        self.current_model_url = None
        self.modify_button.config(state=tk.DISABLED)
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        self.cancel_event = asyncio.Event()
        self.scan_task = self._run_async(self._scan_workflow())
    
    def _on_cancel_clicked(self):
        if self.cancel_event:
            self.cancel_event.set()
        self._update_progress("Cancelling...", 0)
    
    def _on_modify_clicked(self):
        if not self.current_model_url:
            messagebox.showwarning("No Model", "Please scan an object first.")
            return
        
        mod = self.voice_entry.get().strip()
        if not mod or mod == "e.g., 'Turn it into gold'":
            messagebox.showwarning("No Modification", "Please enter a modification command.")
            return
        
        self.modify_button.config(state=tk.DISABLED)
        self._update_progress(f"Applying modification: {mod}...", 0)
        self.scan_task = self._run_async(self._modify_workflow(mod))
    
    async def _scan_workflow(self):
        try:
            imgs, dist = await self.scanner.scan_object(
                on_progress=self._update_progress,
                cancel=self.cancel_event
            )
            
            if not imgs:
                raise Exception("No images captured")
            
            path = await self.scanner.generate_model(
                imgs,
                dist,
                None,
                self._update_progress,
                False,
                self.cancel_event
            )
            
            if path:
                self.current_model_url = path
                self.root.after(0, lambda: self._scan_complete(path))
            else:
                self.root.after(0, lambda: self._scan_cancelled())
        
        except asyncio.CancelledError:
            self.root.after(0, lambda: self._scan_cancelled())
        except Exception as e:
            self.root.after(0, lambda: self._scan_error(str(e)))
    
    async def _modify_workflow(self, mod: str):
        try:
            self._update_progress(f"Generating modified model: {mod}...", 0)
            
            path = await self.scanner.generate_model(
                None,
                None,
                mod,
                self._update_progress,
                True,
                self.cancel_event
            )
            
            if path:
                self.current_model_url = path
                self.root.after(0, lambda: self._modify_complete(path))
            else:
                self.root.after(0, lambda: self._modify_error("Failed to generate modified model"))
        
        except asyncio.CancelledError:
            self.root.after(0, lambda: self._modify_error("Modification cancelled"))
        except Exception as e:
            self.root.after(0, lambda: self._modify_error(str(e)))
    
    def _scan_complete(self, path: str):
        self.scan_button.config(state=tk.NORMAL)
        self.cancel_button.pack_forget()
        self.modify_button.config(state=tk.NORMAL)
        self._update_progress_sync("Scan complete!", 100)
        
        filename = os.path.basename(path)
        self.display_label.config(
            text=f"3D Model Ready!\n\nFile: {filename}\n\nPath: {path}\n\n(3D viewer integration pending)"
        )
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"✓ Scan completed successfully\n")
        self.status_text.insert(tk.END, f"Model saved to: {path}\n")
        self.status_text.insert(tk.END, f"\nYou can open this file in any 3D viewer (Blender, MeshLab, etc.)\n")
        self.status_text.config(state=tk.DISABLED)
    
    def _scan_cancelled(self):
        self.scan_button.config(state=tk.NORMAL)
        self.cancel_button.pack_forget()
        self._update_progress_sync("Scan cancelled", 0)
        self.display_label.config(text="Scan cancelled.\nClick SCAN to try again.")
    
    def _scan_error(self, err: str):
        self.scan_button.config(state=tk.NORMAL)
        self.cancel_button.pack_forget()
        self._update_progress_sync(f"Error: {err}", -1)
        self.display_label.config(text=f"Error occurred:\n{err}")
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"✗ Error: {err}\n")
        self.status_text.config(state=tk.DISABLED)
        
        messagebox.showerror("Scan Error", f"An error occurred during scanning:\n\n{err}")
    
    def _modify_complete(self, path: str):
        self.modify_button.config(state=tk.NORMAL)
        self._update_progress_sync("Modification complete!", 100)
        filename = os.path.basename(path)
        self.display_label.config(
            text=f"Modified 3D Model Ready!\n\nFile: {filename}\n\nPath: {path}"
        )
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"✓ Modification completed\n")
        self.status_text.insert(tk.END, f"New Model: {path}\n")
        self.status_text.config(state=tk.DISABLED)
    
    def _modify_error(self, err: str):
        self.modify_button.config(state=tk.NORMAL)
        self._update_progress_sync(f"Error: {err}", -1)
        messagebox.showerror("Modification Error", f"An error occurred:\n\n{err}")
    
    def cleanup(self):
        if self.scanner:
            self.scanner.cleanup()
        if self.async_loop:
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)
