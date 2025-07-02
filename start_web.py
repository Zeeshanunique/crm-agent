#!/usr/bin/env python3
"""
Simple startup script for the Ralph CRM Web Interface
"""

import subprocess
import sys
import os

def main():
    """Launch the Streamlit web interface."""
    print("🚀 Starting Ralph CRM Web Interface...")
    print("📱 The interface will open in your browser at http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Change to frontend directory
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    
    try:
        # Launch streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "web_chat.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ], cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down Ralph CRM Web Interface...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting the web interface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 