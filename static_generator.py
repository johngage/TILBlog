#!/usr/bin/env python3
"""Static site generator wrapper for GitHub workflow"""
import subprocess
import sys

def main():
    """Run the actual static site builder"""
    try:
        result = subprocess.run([sys.executable, "til_static_builder.py"], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode
    except Exception as e:
        print(f"Error running til_static_builder.py: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
