#!/usr/bin/env python
"""
Unified TIL Blog deployment script
One command to update database, build site, commit changes, and deploy
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Add near the top of til_deploy.py
os.environ['TIL_BASE_URL'] = '/TILBlog'

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def run_command(cmd, description, capture_output=True):
    """Run a command and log the result"""
    log(f"Starting: {description}")
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, shell=True, check=True)
        log(f"✅ Completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Failed: {description}")
        if capture_output and e.stderr:
            log(f"Error: {e.stderr}")
        return False

def check_for_site_changes():
    """Check if there are changes in _site directory"""
    try:
        result = subprocess.run(["git", "status", "_site/", "--porcelain"], 
                              capture_output=True, text=True, check=True)
        return len(result.stdout.strip()) > 0
    except subprocess.CalledProcessError:
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
    if not run_command("python til_static_builder.py --base-url '/TILBlog'", "Static site generation"):
        return 1
    
    # Step 3: Check if there are changes to commit
    log("🔍 Step 3: Checking for site changes")
    if not check_for_site_changes():
        log("📭 No changes detected in _site directory")
        log("✨ Your site is already up to date!")
        return 0
    
    # Step 4: Commit the site changes
    log("📦 Step 4: Committing site changes")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Update TIL site - {timestamp}"
    
    if not run_command("git add _site/", "Stage site changes"):
        return 1
    
    if not run_command(f'git commit -m "{commit_msg}"', "Commit site changes"):
        return 1
    
    # Step 5: Deploy to GitHub Pages
    log("🌐 Step 5: Deploying to GitHub Pages")
    if not run_command("git subtree push --prefix=_site origin gh-pages", 
                      "GitHub Pages deployment", capture_output=False):
        return 1
    
    log("🎉 Deployment complete!")
    log("Your site should be live at: https://johngage.github.io/TILBlog/")
    log("💡 Tip: GitHub Pages may take 1-2 minutes to update")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())