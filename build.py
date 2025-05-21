#!/usr/bin/env python
"""
Static site generator for TIL Blog
Converts Flask app to static HTML files for deployment
"""
import os
import sys
import time
import re
import shutil
import requests
from pathlib import Path
from urllib.parse import urlparse
import subprocess

# Configuration
FLASK_APP_PATH = "app.py"  # Your main Flask app file
BASE_URL = "http://127.0.0.1:5000"  # Local Flask app URL
BUILD_DIR = Path("build")  # Output directory
STATIC_DIR = Path("static")  # Your static files folder
TIMEOUT = 5  # Seconds to wait for Flask to start

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def ensure_dir(path):
    """Create directory if it doesn't exist"""
    if not path.exists():
        path.mkdir(parents=True)
        log(f"Created directory: {path}")

def clean_build_dir():
    """Remove and recreate build directory"""
    if BUILD_DIR.exists():
        log(f"Removing existing build directory: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)
    
    ensure_dir(BUILD_DIR)
    log(f"Created fresh build directory: {BUILD_DIR}")

def save_page(url_path, content):
    """Save content to the appropriate path in the build directory"""
    # Handle root path
    if url_path == "/" or not url_path:
        target_path = BUILD_DIR / "index.html"
    else:
        # Remove leading slash
        clean_path = url_path.lstrip("/")
        
        # Determine if this is a file or directory path
        if clean_path.endswith("/"):
            # Directory path, add index.html
            target_path = BUILD_DIR / clean_path / "index.html"
            ensure_dir(BUILD_DIR / clean_path)
        elif "." not in clean_path.split("/")[-1]:
            # No file extension, treat as directory
            target_path = BUILD_DIR / clean_path / "index.html"
            ensure_dir(BUILD_DIR / clean_path)
        else:
            # File path
            target_path = BUILD_DIR / clean_path
            ensure_dir(target_path.parent)
    
    # Write content to file
    with open(target_path, "wb") as f:
        f.write(content)
    
    log(f"Saved: {target_path}")
    return target_path

def extract_links(html_content):
    """Extract internal links from HTML content"""
    # Convert bytes to string if needed
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8')
    
    # Find all href links, excluding anchors, external links, and special protocols
    links = []
    href_pattern = r'href=["\'](\/[^"\'#]+)["\']'
    matches = re.finditer(href_pattern, html_content)
    
    for match in matches:
        link = match.group(1)
        # Skip already processed links
        if link not in links:
            links.append(link)
    
    return links

def copy_static_files():
    """Copy static directory to build directory"""
    if STATIC_DIR.exists():
        static_target = BUILD_DIR / STATIC_DIR.name
        if static_target.exists():
            shutil.rmtree(static_target)
        
        shutil.copytree(STATIC_DIR, static_target)
        log(f"Copied static files to {static_target}")

def main():
    """Main build process"""
    log("Starting TIL blog static site generation")
    
    # Clean build directory
    clean_build_dir()
    
    # Start Flask app in a subprocess
    log(f"Starting Flask app: {FLASK_APP_PATH}")
    flask_process = subprocess.Popen(
        [sys.executable, FLASK_APP_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Wait for Flask to start
        log(f"Waiting {TIMEOUT}s for Flask to start...")
        time.sleep(TIMEOUT)
        
        # Process the home page
        log(f"Fetching home page: {BASE_URL}")
        try:
            response = requests.get(BASE_URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            log(f"Error fetching home page: {e}")
            log("Flask app may not have started properly. Check logs.")
            return 1
        
        # Save the home page
        home_path = save_page("/", response.content)
        
        # Extract links from home page
        links_to_process = extract_links(response.content)
        log(f"Found {len(links_to_process)} links on home page")
        
        # Keep track of processed links
        processed_links = {"/"}
        
        # Process all links (including new ones we find)
        while links_to_process:
            current_link = links_to_process.pop(0)
            
            # Skip if already processed
            if current_link in processed_links:
                continue
            
            log(f"Processing: {current_link}")
            processed_links.add(current_link)
            
            # Fetch the page
            try:
                page_url = f"{BASE_URL}{current_link}"
                response = requests.get(page_url, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                log(f"Error fetching {current_link}: {e}")
                continue
            
            # Save the page
            save_page(current_link, response.content)
            
            # Extract new links
            new_links = extract_links(response.content)
            for link in new_links:
                if link not in processed_links and link not in links_to_process:
                    links_to_process.append(link)
        
        # Copy static files
        copy_static_files()
        
        # Create .nojekyll file to prevent GitHub Pages from using Jekyll
        with open(BUILD_DIR / ".nojekyll", "w") as f:
            f.write("")
        
        log(f"Processed {len(processed_links)} pages in total")
        log("Static site generation complete!")
        
    finally:
        # Terminate Flask app
        log("Shutting down Flask app")
        flask_process.terminate()
        try:
            flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            flask_process.kill()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())