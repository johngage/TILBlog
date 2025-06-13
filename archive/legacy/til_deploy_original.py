#!/usr/bin/env python3
"""
TILNET One-Command Deployment Script

This script shows exactly how static site deployment works:
1. Build a database from markdown files
2. Generate a static website
3. Use git to deploy to GitHub Pages

No magic, no complex CI/CD - just simple commands you can understand!
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# For GitHub Pages deployment from a repository named 'tilnet',
# your site will be at: https://USERNAME.github.io/tilnet/
# Update this if your repository has a different name:
GITHUB_PAGES_BASE_URL = '/TILBlog'

def log(message):
    """Print a timestamped, colorful log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def run_command(cmd, description, capture_output=True):
    """Run a shell command and log the result"""
    log(f"Starting: {description}")
    log(f"Command: {cmd}")  # Show the actual command being run
    
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        else:
            # For git push, show output in real-time
            result = subprocess.run(cmd, shell=True, check=True)
        
        log(f"✅ Completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Failed: {description}")
        if capture_output and e.stderr:
            log(f"Error: {e.stderr}")
        return False

def check_environment():
    """Make sure we're in the right place with the right tools"""
    # Check if we're in a git repository
    if not Path('.git').exists():
        log("❌ Not in a git repository! Please run from your tilnet directory.")
        return False
    
    # Check if required files exist
    required_files = ['rebuild_database.py', 'til_static_builder.py', 'content']
    for file in required_files:
        if not Path(file).exists():
            log(f"❌ Missing required file/directory: {file}")
            return False
    
    return True

def check_for_changes():
    """Check if there are any changes to deploy"""
    try:
        # Check if _site directory has changes
        result = subprocess.run(["git", "status", "_site/", "--porcelain"], 
                              capture_output=True, text=True, check=True)
        return len(result.stdout.strip()) > 0
    except subprocess.CalledProcessError:
        # If _site doesn't exist yet, we definitely have changes to deploy
        return True

def main():
    """Main deployment workflow - simple and transparent!"""
    log("🚀 Starting TILNET deployment")
    log("=" * 50)
    
    # Make sure we're in the right place
    if not check_environment():
        return 1
    
    # Step 1: Build database from markdown files
    log("")
    log("📄 STEP 1: Building database from your markdown files")
    log("This reads all .md files in content/ and creates til.db")
    
    if not run_command("python rebuild_database.py", "Database build"):
        log("💡 Tip: Check that your markdown files have valid frontmatter")
        return 1
    
    # Step 2: Generate static site
    log("")
    log("🏗️  STEP 2: Generating static website")
    log("This creates HTML files in _site/ directory")
    
    if not run_command(
        f"python til_static_builder.py --base-url '{GITHUB_PAGES_BASE_URL}'", 
        "Static site generation"
    ):
        return 1
    
    # Step 3: Check if there are changes
    log("")
    log("🔍 STEP 3: Checking for changes")
    
    if not check_for_changes():
        log("✨ No changes detected - your site is already up to date!")
        return 0
    
    # Step 4: Commit changes
    log("")
    log("📦 STEP 4: Saving changes to git")
    log("This creates a commit with all your new content")
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Update TIL site - {timestamp}"
    
    # Add the generated site to git
    if not run_command("git add _site/", "Stage changes"):
        return 1
    
    # Create a commit
    if not run_command(f'git commit -m "{commit_message}"', "Create commit"):
        log("💡 Tip: If this fails, you might not have any new changes")
        return 1
    
    # Step 5: Deploy to GitHub Pages
    log("")
    log("🌐 STEP 5: Deploying to GitHub Pages")
    log("This pushes your _site/ directory to the gh-pages branch")
    log("GitHub will serve these files as your website")
    
    if not run_command(
        "git subtree push --prefix=_site origin gh-pages", 
        "Push to GitHub Pages", 
        capture_output=False  # Show progress for long operation
    ):
        log("")
        log("💡 If this failed, try:")
        log("   1. Make sure you're connected to internet")
        log("   2. Check your GitHub credentials")
        log("   3. Try: git push origin main (to save your work)")
        return 1
    
    # Success!
    log("")
    log("🎉 Deployment complete!")
    log("=" * 50)
    log("")
    log(f"📍 Your site will be live at:")
    log(f"   https://YOUR-GITHUB-USERNAME.github.io{GITHUB_PAGES_BASE_URL}/")
    log("")
    log("⏱️  Note: GitHub Pages may take 1-2 minutes to update")
    log("")
    log("💡 Next steps:")
    log("   1. Add more TIL entries to content/")
    log("   2. Run this script again!")
    log("")
    
    return 0

if __name__ == "__main__":
    # This makes the script executable
    exit_code = main()
    sys.exit(exit_code)