import tkinter as tk
import sys
from gui.main_window import MainWindow
from config_loader import get_config
from platform_detector import get_platform_info


def main():
    info = get_platform_info()
    print("*" * 60)
    print(" VoxelScan 3D - AI-Powered Modeler")
    print("*" * 60)
    print(f"Running Environment: {'Embedded (Raspberry Pi)' if info['is_pi'] else 'Desktop (Mock Hardware)'}")
    print(f"OS: {info['system']}")
    print(f"Python Version: {info['python_version']}")
    print("*" * 60)
    
    cfg = get_config()
    key = cfg.get('ai', 'gemini', 'api_key', default='')
    
    if not key:
        print("\n*** ACTION REQUIRED ***")
        print("  Gemini API key is missing. Please set GEMINI_API_KEY or edit config.yaml.\n")
    else:
        print("[OK] Gemini API key loaded successfully.")
    
    print("[INFO] Blender installation is necessary for mesh creation.")
    print("  Grab it here: https://www.blender.org/download/\n")
    
    root = tk.Tk()
    app = MainWindow(root)
    
    def on_closing():
        app.cleanup()
        root.destroy()
        sys.exit(0)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_closing()


if __name__ == '__main__':
    main()
