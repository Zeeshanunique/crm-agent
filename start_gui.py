#!/usr/bin/env python3
"""
Startup script for Ralph CRM Assistant GUI
"""

import subprocess
import sys
import os

def main():
    # Change to the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Path to the Streamlit app
    app_path = os.path.join("frontend", "chat_gui.py")
    
    print("🚀 Starting Ralph CRM Assistant GUI...")
    print("📱 The app will open in your default web browser")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", app_path,
            "--server.headless", "false",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Ralph GUI stopped. Goodbye!")
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 