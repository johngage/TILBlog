#!/usr/bin/env python
"""
Simple static site generator for TIL Blog
Based on existing database and templates
"""
import os
import sys
import time
import shutil
import sqlite3
from pathlib import Path
import subprocess
import markdown
import frontmatter

# Configuration
DATABASE = "til.db"
BUILD_DIR = Path("_site")
STATIC_DIR = Path("static")
BASE_URL = "/TILBlog/"  # Your repository name

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
    """Main build process"""
    log("Starting TIL blog static site generation")
    
    # Configuration
    DATABASE = "til.db"
    BUILD_DIR = Path("_site")  # Using _site as it's a common static site convention
    STATIC_DIR = Path("static")
    
    # Clean build directory
    if BUILD_DIR.exists():
        log(f"Removing existing build directory: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)
    
    ensure_dir(BUILD_DIR)
    log(f"Created fresh build directory: {BUILD_DIR}")
    
    # Copy static files
    if STATIC_DIR.exists():
        static_target = BUILD_DIR / "static"
        shutil.copytree(STATIC_DIR, static_target)
        log(f"Copied static files to {static_target}")
    
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
    
    # Get all topics with counts
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
    
    # Generate home page
    generate_home_page(BUILD_DIR, entries, topics)
    
    # Generate individual entry pages
    generate_entry_pages(BUILD_DIR, conn, entries, topics)
    
    # Generate topic pages
    generate_topic_pages(BUILD_DIR, conn, topics)
    
    # Generate Datasette export
    generate_datasette_export(BUILD_DIR, DATABASE)
    
    # Create .nojekyll file for GitHub Pages
    with open(BUILD_DIR / ".nojekyll", "w") as f:
        f.write("")
    
    log("Static site generation complete!")
    log(f"Deploy the {BUILD_DIR} directory to your hosting provider.")
    return 0

def generate_home_page(build_dir, entries, topics):
    """Generate the home page"""
    log("Generating home page")
    
    with open(build_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIL: Today I Learned</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <header>
        <h1>TIL: Today I Learned</h1>
        <nav class="topics-nav">
            {"".join(f'<a href="/topic/{t["topic"]}/">{t["topic"]} <span class="count">({t["count"]})</span></a>' for t in topics)}
        </nav>
    </header>
    
    <main>
        <div class="entries">
            {"".join(generate_entry_item(entry) for entry in entries[:20])}
        </div>
        
        <div class="pagination">
            <a href="/page/2/">More entries →</a>
        </div>
    </main>
    
    <footer>
        <p>TIL Blog - <a href="/data/">Browse the database</a></p>
    </footer>
</body>
</html>""")
    
    log("Home page generated")

def generate_entry_item(entry):
    """Generate HTML for a single entry in a list"""
    date_display = entry["created"].split()[0]  # Just the date part
    
    # Extract topics
    topics_list = []
    if entry["topics_raw"]:
        topics_list = entry["topics_raw"].split(",")
    
    topics_html = ""
    if topics_list:
        topics_html = f'<div class="topics">{" ".join(f"<a href=\"/topic/{topic.strip()}/\">{topic.strip()}</a>" for topic in topics_list)}</div>'
    
    return f"""
    <div class="entry">
        <h2><a href="/til/{entry["slug"]}/">{entry["title"]}</a></h2>
        <div class="metadata">
            <span class="date">{date_display}</span>
            {topics_html}
        </div>
    </div>
    """

def generate_entry_pages(build_dir, conn, entries, all_topics):
    """Generate individual entry pages"""
    log("Generating entry pages")
    
    for entry in entries:
        # Create directory for this entry
        entry_dir = build_dir / "til" / entry["slug"]
        ensure_dir(entry_dir)
        
        # Get topics for this entry
        entry_topics = []
        if entry["topics_raw"]:
            entry_topics = entry["topics_raw"].split(",")
        
        # Generate HTML
        with open(entry_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{entry["title"]} - TIL</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <header>
        <h1><a href="/">TIL: Today I Learned</a></h1>
        <nav class="topics-nav">
            {"".join(f'<a href="/topic/{t["topic"]}/">{t["topic"]}</a>' for t in all_topics)}
        </nav>
    </header>
    
    <main>
        <article class="entry full">
            <h1>{entry["title"]}</h1>
            <div class="metadata">
                <span class="date">{entry["created"].split()[0]}</span>
                <div class="topics">
                    {"".join(f'<a href="/topic/{topic.strip()}/">{topic.strip()}</a>' for topic in entry_topics)}
                </div>
            </div>
            <div class="content">
                {entry["html"]}
            </div>
        </article>
    </main>
    
    <footer>
        <p><a href="/">← Back to all entries</a></p>
        <p><a href="/data/">Browse the database</a></p>
    </footer>
</body>
</html>""")
    
    log(f"Generated {len(entries)} entry pages")

def generate_topic_pages(build_dir, conn, topics):
    """Generate topic pages"""
    log("Generating topic pages")
    
    for topic in topics:
        # Create directory for this topic
        topic_dir = build_dir / "topic" / topic["topic"]
        ensure_dir(topic_dir)
        
        # Get entries for this topic
        topic_entries = conn.execute(
            """
            SELECT e.id, e.slug, e.title, 
                   COALESCE(e.created_fm, e.created_fs) as created,
                   e.topics_raw
            FROM entries e
            JOIN entry_topics et ON e.id = et.entry_id
            JOIN topics t ON et.topic_id = t.id
            WHERE t.name = ?
            ORDER BY COALESCE(e.created_fm, e.created_fs) DESC
            """,
            [topic["topic"]]
        ).fetchall()
        
        # Generate HTML
        with open(topic_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Topic: {topic["topic"]} - TIL</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <header>
        <h1><a href="/">TIL: Today I Learned</a></h1>
        <nav class="topics-nav">
            {"".join(f'<a href="/topic/{t["topic"]}/" class="{"active" if t["topic"] == topic["topic"] else ""}">{t["topic"]}</a>' for t in topics)}
        </nav>
    </header>
    
    <main>
        <h1>Topic: {topic["topic"]}</h1>
        <p class="count">{topic["count"]} entries</p>
        
        <div class="entries">
            {"".join(generate_entry_item(entry) for entry in topic_entries)}
        </div>
    </main>
    
    <footer>
        <p><a href="/">← Back to all entries</a></p>
        <p><a href="/data/">Browse the database</a></p>
    </footer>
</body>
</html>""")
    
    log(f"Generated {len(topics)} topic pages")

def generate_datasette_export(build_dir, database):
    """Generate a Datasette export for the database"""
    log("Setting up Datasette export")
    
    # Create data directory
    data_dir = build_dir / "data"
    ensure_dir(data_dir)
    
    # Check if datasette is installed
    datasette_installed = False
    try:
        subprocess.run(["datasette", "--version"], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE, 
                       check=True)
        datasette_installed = True
    except (subprocess.SubprocessError, FileNotFoundError):
        log("Datasette not found. Install with: pip install datasette")
    
    if datasette_installed:
        try:
            # Create a static export of the database
            log("Generating Datasette export")
            subprocess.run([
                "datasette", "export", database,
                "--format", "html",
                "--plugin", "datasette-render-html",
                "--plugin", "datasette-json-html",
                "--outfile", str(data_dir / "index.html")
            ], check=True)
            log("Datasette export complete")
        except subprocess.SubprocessError as e:
            log(f"Error generating Datasette export: {e}")
            
            # Create a simple placeholder page
            with open(data_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIL Database - Datasette</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <header>
        <h1><a href="/">TIL: Today I Learned</a></h1>
    </header>
    
    <main>
        <h1>Database Browser</h1>
        <p>To browse the database, install Datasette locally:</p>
        <pre>pip install datasette
datasette {database}</pre>
    </main>
    
    <footer>
        <p><a href="/">← Back to all entries</a></p>
    </footer>
</body>
</html>""")
            log("Created Datasette placeholder page")
    else:
        # Create a simple page about Datasette
        with open(data_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIL Database - Install Datasette</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <header>
        <h1><a href="/">TIL: Today I Learned</a></h1>
    </header>
    
    <main>
        <h1>Database Browser</h1>
        <p>To browse the database, install Datasette:</p>
        <pre>pip install datasette
datasette {database}</pre>
        <p>Learn more at <a href="https://datasette.io/">datasette.io</a></p>
    </main>
    
    <footer>
        <p><a href="/">← Back to all entries</a></p>
    </footer>
</body>
</html>""")
        log("Created Datasette info page")

if __name__ == "__main__":
    sys.exit(main())