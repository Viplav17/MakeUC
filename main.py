import tkinter as tk
import sys
from gui.main_window import MainWindow
from config_loader import get_config


def main():
    print("*" * 60)
    print(" The Lighthouse - AI-Powered 3D Scanner")
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
