#!/usr/bin/env python3
"""
TILNET Unified Deployment Script

Intelligently detects available features and runs appropriate workflow:
- Always: Core TIL deployment (database → static site → git deploy)
- If available: Claude conversation processing
- If available: TILNET status reporting

No magic, no complex CI/CD - just smart, simple commands!
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

# Configuration
GITHUB_PAGES_BASE_URL = '/TILBlog'

def log(message):
    """Print a timestamped, colorful log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def run_command(cmd, description, capture_output=True):
    """Run a shell command and log the result"""
    log(f"Starting: {description}")
    log(f"Command: {cmd}")
    
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

def check_environment():
    """Make sure we're in the right place with the right tools"""
    if not Path('.git').exists():
        log("❌ Not in a git repository! Please run from your tilnet directory.")
        return False
    
    required_files = ['rebuild_database.py', 'til_static_builder.py', 'content']
    for file in required_files:
        if not Path(file).exists():
            log(f"❌ Missing required file/directory: {file}")
            return False
    
    return True

def check_claude_integration():
    """Check if Claude integration is available and has new data"""
    claude_export_path = Path("claude_exports/latest/conversations.json")
    claude_integration_script = Path("claude_tilnet_integration.py")
    
    return {
        'available': claude_integration_script.exists(),
        'has_new_exports': claude_export_path.exists(),
        'script_path': claude_integration_script,
        'export_path': claude_export_path
    }

def process_claude_conversations():
    """Process Claude conversations if available"""
    claude_info = check_claude_integration()
    
    if not claude_info['available']:
        log("📂 No Claude integration script found - skipping")
        return True
    
    if not claude_info['has_new_exports']:
        log("📂 No new Claude conversation exports found - skipping")
        return True
    
    log("🤖 Processing Claude conversations...")
    return run_command("python claude_tilnet_integration.py", "Claude conversation processing")

def show_tilnet_status():
    """Show TILNET system status if available"""
    try:
        log("📊 TILNET System Status:")
        
        # Check conversations database
        if Path("conversations.db").exists():
            result = subprocess.run([
                "sqlite-utils", "query", "conversations.db",
                "SELECT COUNT(*) as conversations FROM conversations"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                log(f"  💬 Total conversations: {data[0]['conversations']}")
        
        # Check high-value conversations
        if Path("high_value_conversations.json").exists():
            with open("high_value_conversations.json") as f:
                high_value = json.load(f)
                log(f"  💎 High-value conversations: {len(high_value)}")
        
        # Check meta-conversation
        if Path("tilnet_meta_conversation.json").exists():
            meta_size = Path("tilnet_meta_conversation.json").stat().st_size
            log(f"  🔄 Meta-conversation: {meta_size:,} bytes (recursive knowledge active)")
        
        # Check if Datasette is available
        if Path("tilnet-datasette-metadata.json").exists():
            log("  🌐 Datasette available at: http://localhost:8080")
            
    except Exception as e:
        log(f"  ❌ Error checking TILNET status: {e}")

def check_for_changes():
    """Check if there are any changes to deploy"""
    try:
        result = subprocess.run(["git", "status", "_site/", "--porcelain"], 
                              capture_output=True, text=True, check=True)
        return len(result.stdout.strip()) > 0
    except subprocess.CalledProcessError:
        return True  # If _site doesn't exist yet, we have changes

def main():
    """Main deployment workflow - auto-detects features!"""
    log("🚀 Starting TILNET Unified Deployment")
    log("=" * 50)
    
    # Environment check
    if not check_environment():
        return 1
    
    # STEP 0: Claude Integration (if available)
    claude_info = check_claude_integration()
    if claude_info['available'] or claude_info['has_new_exports']:
        log("")
        log("🤖 STEP 0: Claude Integration")
        if not process_claude_conversations():
            log("💡 Claude processing failed, but continuing with core deployment")
    
    # STEP 1: Build database
    log("")
    log("📄 STEP 1: Building database from markdown files")
    log("This reads all .md files in content/ and creates til.db")
    
    if not run_command("python rebuild_database.py", "Database build"):
        log("💡 Tip: Check that your markdown files have valid frontmatter")
        return 1
    
    # STEP 2: Generate static site
    log("")
    log("🏗️  STEP 2: Generating static website")
    log("This creates HTML files in _site/ directory")
    
    if not run_command(
        f"python til_static_builder.py --base-url '{GITHUB_PAGES_BASE_URL}'", 
        "Static site generation"
    ):
        return 1
    
    # STEP 3: Check for changes
    log("")
    log("🔍 STEP 3: Checking for changes")
    
    if not check_for_changes():
        log("✨ No changes detected - your site is already up to date!")
        show_tilnet_status()  # Show status even if no changes
        return 0
    
    # STEP 4: Commit changes
    log("")
    log("📦 STEP 4: Saving changes to git")
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Update TIL site - {timestamp}"
    
    if not run_command("git add _site/", "Stage changes"):
        return 1
    
    if not run_command(f'git commit -m "{commit_message}"', "Create commit"):
        log("💡 Tip: If this fails, you might not have any new changes")
        return 1
    
    # STEP 5: Deploy to GitHub Pages
    log("")
    log("🌐 STEP 5: Deploying to GitHub Pages")
    
    if not run_command(
        "git subtree push --prefix=_site origin gh-pages", 
        "Push to GitHub Pages", 
        capture_output=False
    ):
        log("💡 If this failed, try: git push origin main (to save your work)")
        return 1
    
    # SUCCESS!
    log("")
    log("🎉 Deployment complete!")
    log("=" * 50)
    show_tilnet_status()
    log("")
    log(f"📍 Your site will be live at:")
    log(f"   https://YOUR-GITHUB-USERNAME.github.io{GITHUB_PAGES_BASE_URL}/")
    log("")
    log("⏱️  Note: GitHub Pages may take 1-2 minutes to update")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
    