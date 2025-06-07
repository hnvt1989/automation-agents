#!/usr/bin/env python3
"""
Run tests for the Editor functionality
"""
import subprocess
import sys

def main():
    """Run the editor tests"""
    print("Running Editor functionality tests...")
    print("-" * 50)
    
    # Run pytest with verbose output
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/integration/test_editor_functionality.py",
        "-v",
        "--tb=short"
    ])
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())