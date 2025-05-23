#!/usr/bin/env python
"""
Unified TIL Blog deployment script
One command to update database, build site, and deploy
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def run_command(cmd, description):
    """Run a command and log the result"""
    log(f"Starting: {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        log(f"✅ Completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Failed: {description}")
        log(f"Error: {e.stderr}")
        return False

def main():
    """Main deployment workflow"""
    log("🚀 Starting TIL blog deployment")
    
    # Step 1: Update database from content files
    log("📄 Step 1: Updating database from content files")
    if not run_command("python rebuild_database.py", "Database update"):
        return 1
    
    # Step 2: Generate static site
    log("🏗️  Step 2: Generating static site")
    if not run_command("python til_static_builder.py", "Static site generation"):
        return 1
    
    # Step 3: Deploy to GitHub Pages
    log("🌐 Step 3: Deploying to GitHub Pages")
    if not run_command("git subtree push --prefix=_site origin gh-pages", "GitHub Pages deployment"):
        return 1
    
    log("🎉 Deployment complete!")
    log("Your site should be live at: https://johngage.github.io/TILBlog/")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())