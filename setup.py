import subprocess
import sys
import os

# Windows consoles default to cp1252, which can't encode the emoji printed below
sys.stdout.reconfigure(encoding="utf-8")

def setup():
    print("🚀 Initializing CliPRx Environment...")
    
    # Install dependencies from requirements.txt
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_file):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        print("✅ Requirements installed successfully.")
    
    # Run test script
    test_file = os.path.join(os.path.dirname(__file__), "test.py")
    if os.path.exists(test_file):
        print("\n▶ Running Pipeline Test Runner...\n")
        subprocess.check_call([sys.executable, test_file])

if __name__ == "__main__":
    setup()