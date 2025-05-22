#!/usr/bin/env python
"""
Complete static content generator for TIL Blog
Creates all pages with correct GitHub Pages URLs
"""
import os
import sys
import time
import re
import shutil
import sqlite3
from pathlib import Path

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()

def ensure_dir(path):
    """Create directory if it doesn't exist"""
    if not path.exists():
        path.mkdir(parents=True)
        log(f"Created directory: {path}")

def main():
    """Main build process that creates all pages"""
    log("Starting complete TIL blog static generation")
    
    # Configuration - IMPORTANT: Change this to your repository name
    DATABASE = "til.db"
    BUILD_DIR = Path("_site")
    STATIC_DIR = Path("static")
    BASE_URL = "/TILBlog"  # Change this to your GitHub repository name
    
    # Clean build directory
    if BUILD_DIR.exists():
        log(f"Removing existing build directory: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)
    
    ensure_dir(BUILD_DIR)
    log(f"Created fresh build directory: {BUILD_DIR}")
    
    # Connect to the database
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        log(f"Connected to database: {DATABASE}")
    except Exception as e:
        log(f"Error connecting to database: {e}")
        return 1
    
    # Get all entries and topics
    entries = conn.execute(
        """
        SELECT id, slug, title, html, 
               COALESCE(created_fm, created_fs) as created,
               topics_raw
        FROM entries
        ORDER BY COALESCE(created_fm, created_fs) DESC
        """
    ).fetchall()
    
    topics = conn.execute(
        """
        SELECT t.name as topic, COUNT(*) as count
        FROM topics t
        JOIN entry_topics et ON t.id = et.topic_id
        GROUP BY t.name
        ORDER BY t.name ASC
        """
    ).fetchall()
    
    log(f"Found {len(entries)} entries and {len(topics)} topics")
    
    if len(entries) == 0:
        log("No entries found in database!")
        return 1
    
    # Generate home page
    generate_home_page(BUILD_DIR, entries, topics, BASE_URL)
    
    # Generate individual entry pages
    generate_entry_pages(BUILD_DIR, conn, entries, topics, BASE_URL)
    
    # Generate topic pages  
    generate_topic_pages(BUILD_DIR, conn, topics, BASE_URL)
    
    # Copy static files
    copy_static_files(BUILD_DIR, STATIC_DIR)
    
    # Create .nojekyll file for GitHub Pages
    with open(BUILD_DIR / ".nojekyll", "w") as f:
        f.write("")
    
    log("Complete static site generation finished!")
    log(f"Deploy the {BUILD_DIR} directory to your hosting provider.")
    return 0

def generate_home_page(build_dir, entries, topics, base_url):
    """Generate the home page with topic navigation"""
    log("Generating home page")
    
    # Create topics navigation
    topics_nav = ""
    for topic in topics:
        topics_nav += f'<a href="{base_url}/topic/{topic["topic"]}/">{topic["topic"]} ({topic["count"]})</a> '
    
    # Create entries list
    entries_html = ""
    for entry in entries[:20]:  # Show first 20 entries
        date_display = entry["created"].split()[0] if entry["created"] else "Unknown"
        entries_html += f"""
        <div class="entry-item">
            <h3><a href="{base_url}/til/{entry["slug"]}/">{entry["title"]}</a></h3>
            <div class="meta">
                <span class="date">{date_display}</span>
                {generate_topics_for_entry(entry, base_url)}
            </div>
        </div>
        """
    
    with open(build_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIL: Today I Learned</title>
    <link rel="stylesheet" href="{base_url}/static/styles.css">
</head>
<body>
    <header>
        <h1><a href="{base_url}/">TIL: Today I Learned</a></h1>
        <nav class="topics-nav">
            {topics_nav}
        </nav>
    </header>
    
    <main>
        <div class="entries">
            {entries_html}
        </div>
    </main>
    
    <footer>
        <p>Total entries: {len(entries)} | Topics: {len(topics)}</p>
    </footer>
</body>
</html>""")
    
    log("Generated home page")

def generate_entry_pages(build_dir, conn, entries, topics, base_url):
    """Generate individual entry pages"""
    log("Generating individual entry pages")
    
    # Create main til directory
    til_dir = build_dir / "til"
    ensure_dir(til_dir)
    
    # Topics navigation for all pages
    topics_nav = ""
    for topic in topics:
        topics_nav += f'<a href="{base_url}/topic/{topic["topic"]}/">{topic["topic"]}</a> '
    
    for entry in entries:
        # Create directory for this entry
        entry_dir = til_dir / entry["slug"]
        ensure_dir(entry_dir)
        
        # Get topics for this entry
        entry_topics = []
        if entry["topics_raw"]:
            entry_topics = [t.strip() for t in entry["topics_raw"].split(",")]
        
        # Generate topics links for this entry
        topics_html = ""
        if entry_topics:
            topics_links = [f'<a href="{base_url}/topic/{topic}/">{topic}</a>' for topic in entry_topics]
            topics_html = f'<div class="topics">Topics: {", ".join(topics_links)}</div>'
        
        # Create the entry page
        with open(entry_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{entry["title"]} - TIL</title>
    <link rel="stylesheet" href="{base_url}/static/styles.css">
</head>
<body>
    <header>
        <h1><a href="{base_url}/">TIL: Today I Learned</a></h1>
        <nav class="topics-nav">
            {topics_nav}
        </nav>
    </header>
    
    <main>
        <article class="entry">
            <h1>{entry["title"]}</h1>
            <div class="metadata">
                <span class="date">{entry["created"].split()[0] if entry["created"] else "Unknown"}</span>
                {topics_html}
            </div>
            <div class="content">
                {entry["html"]}
            </div>
        </article>
    </main>
    
    <footer>
        <p><a href="{base_url}/">← Back to all entries</a></p>
    </footer>
</body>
</html>""")
    
    log(f"Generated {len(entries)} entry pages")

def generate_topic_pages(build_dir, conn, topics, base_url):
    """Generate topic index pages"""
    log("Generating topic pages")
    
    # Create main topic directory
    topic_dir = build_dir / "topic"
    ensure_dir(topic_dir)
    
    # Topics navigation for all pages
    topics_nav = ""
    for topic in topics:
        topics_nav += f'<a href="{base_url}/topic/{topic["topic"]}/">{topic["topic"]}</a> '
    
    for topic in topics:
        topic_name = topic["topic"]
        
        # Create directory for this topic
        topic_page_dir = topic_dir / topic_name
        ensure_dir(topic_page_dir)
        
        # Get entries for this topic
        topic_entries = conn.execute(
            """
            SELECT e.id, e.slug, e.title, 
                   COALESCE(e.created_fm, e.created_fs) as created
            FROM entries e
            JOIN entry_topics et ON e.id = et.entry_id
            JOIN topics t ON et.topic_id = t.id
            WHERE t.name = ?
            ORDER BY COALESCE(e.created_fm, e.created_fs) DESC
            """,
            [topic_name]
        ).fetchall()
        
        # Generate entries list for this topic
        entries_html = ""
        for entry in topic_entries:
            date_display = entry["created"].split()[0] if entry["created"] else "Unknown"
            entries_html += f"""
            <div class="entry-item">
                <h3><a href="{base_url}/til/{entry["slug"]}/">{entry["title"]}</a></h3>
                <div class="meta">
                    <span class="date">{date_display}</span>
                </div>
            </div>
            """
        
        # Create the topic page
        with open(topic_page_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Topic: {topic_name} - TIL</title>
    <link rel="stylesheet" href="{base_url}/static/styles.css">
</head>
<body>
    <header>
        <h1><a href="{base_url}/">TIL: Today I Learned</a></h1>
        <nav class="topics-nav">
            {topics_nav}
        </nav>
    </header>
    
    <main>
        <h1>Topic: {topic_name}</h1>
        <p class="topic-count">{topic["count"]} entries in this topic</p>
        
        <div class="entries">
            {entries_html}
        </div>
    </main>
    
    <footer>
        <p><a href="{base_url}/">← Back to all entries</a></p>
    </footer>
</body>
</html>""")
    
    log(f"Generated {len(topics)} topic pages")

def generate_topics_for_entry(entry, base_url):
    """Generate topic links for an entry"""
    if not entry["topics_raw"]:
        return ""
    
    topics = [t.strip() for t in entry["topics_raw"].split(",")]
    topic_links = [f'<a href="{base_url}/topic/{topic}/" class="topic-link">{topic}</a>' for topic in topics]
    return f'<div class="topics">{", ".join(topic_links)}</div>'

def copy_static_files(build_dir, static_dir):
    """Copy static files to the build directory"""
    if static_dir.exists():
        static_target = build_dir / "static"
        if static_target.exists():
            shutil.rmtree(static_target)
        
        shutil.copytree(static_dir, static_target)
        log(f"Copied static files to {static_target}")
        
        # Check if styles.css exists
        styles_css = static_target / "styles.css"
        if styles_css.exists():
            log(f"Found styles.css ({os.path.getsize(styles_css)} bytes)")
        else:
            log("Warning: styles.css not found")
    else:
        log("No static directory found")

if __name__ == "__main__":
    sys.exit(main())