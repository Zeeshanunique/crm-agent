#!/usr/bin/env python3
"""
Start the Ralph CRM Clean GUI Interface

This version provides:
- Clean error handling and separation
- Proper data table formatting
- No formatting artifacts
- Professional appearance
"""

import subprocess
import sys
import os

def main():
    """Start the clean Streamlit interface"""
    print("🚀 Starting Ralph CRM Clean Interface...")
    print("📊 Features: Clean tables, error separation, professional UI")
    print("🌐 Opening in browser at: http://localhost:8501")
    print("\n💡 To stop: Press Ctrl+C")
    print("-" * 50)
    
    try:
        # Change to the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Run the clean GUI
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "frontend/chat_gui_clean.py",
            "--server.address", "localhost",
            "--server.port", "8501"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down Ralph CRM Clean Interface...")
        print("✅ Goodbye!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting interface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 