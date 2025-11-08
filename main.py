import tkinter as tk
import sys
from gui.main_window import MainWindow
from config_loader import get_config
from platform_detector import get_platform_info


def main():
    info = get_platform_info()
    print("=" * 50)
    print("The Lighthouse - Interactive AI 3D Scanner")
    print("=" * 50)
    print(f"Platform: {'Raspberry Pi' if info['is_pi'] else 'Development (Mock Hardware)'}")
    print(f"System: {info['system']}")
    print(f"Python: {info['python_version']}")
    print("=" * 50)
    
    cfg = get_config()
    key = cfg.get('ai', 'gemini', 'api_key', default='')
    
    if not key:
        print("\n⚠ WARNING: Gemini API key not configured!")
        print("   Set GEMINI_API_KEY environment variable or update config.yaml\n")
    else:
        print("✓ Gemini API key configured")
    
    print("✓ Blender required for 3D model generation")
    print("  Download from: https://www.blender.org/download/\n")
    
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
