#!/usr/bin/env python
"""
Debug script to examine the TIL database contents
"""
import sqlite3
import os
import sys
import time
from pathlib import Path

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()

def main():
    """Main debug function to examine database"""
    log("TIL Database Debug Tool")
    log("=======================")
    
    # Configuration
    DATABASE = "til.db"
    root = Path(__file__).parent.resolve()
    
    # Check if database exists
    db_path = root / DATABASE
    if not os.path.exists(db_path):
        log(f"Error: Database file {db_path} not found!")
        return 1
    
    # Print database file size
    db_size = os.path.getsize(db_path)
    log(f"Database size: {db_size} bytes")
    
    # Connect to database
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        log("Successfully connected to database")
    except Exception as e:
        log(f"Error connecting to database: {e}")
        return 1
    
    # List tables
    log("\nDatabase Tables:")
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    if not tables:
        log("No tables found in database!")
    else:
        for table in tables:
            log(f"- {table['name']}")
    
    # Check entries table
    if any(table['name'] == 'entries' for table in tables):
        log("\nEntries in 'entries' table:")
        entries = conn.execute(
            """
            SELECT id, slug, title, 
                   COALESCE(created_fm, created_fs) as created,
                   topics_raw
            FROM entries 
            ORDER BY COALESCE(created_fm, created_fs) DESC 
            LIMIT 10;
            """
        ).fetchall()
        log(f"Found {len(entries)} entries (showing first 10)")
        
        for entry in entries:
            log(f"- {entry['id']}: {entry['title']} (Created: {entry['created']})")
            log(f"  Slug: {entry['slug']}")
            log(f"  Topics: {entry['topics_raw']}")
            
        # Count total entries
        total_count = conn.execute("SELECT COUNT(*) as count FROM entries;").fetchone()
        log(f"\nTotal entries in database: {total_count['count']}")
    
    # Check topics table
    if any(table['name'] == 'topics' for table in tables):
        log("\nTopics in 'topics' table:")
        topics = conn.execute(
            """
            SELECT t.id, t.name, COUNT(et.entry_id) as count
            FROM topics t
            LEFT JOIN entry_topics et ON t.id = et.topic_id
            GROUP BY t.id, t.name
            ORDER BY count DESC;
            """
        ).fetchall()
        log(f"Found {len(topics)} topics")
        
        for topic in topics:
            log(f"- {topic['name']}: {topic['count']} entries")
    
    # Check content directory
    content_dir = root / "content"
    log(f"\nContent Directory ({content_dir}):")
    if os.path.exists(content_dir) and os.path.isdir(content_dir):
        content_files = []
        for root_path, dirs, files in os.walk(content_dir):
            for file in files:
                if file.endswith(".md"):
                    content_files.append(os.path.join(root_path, file))
        
        log(f"Found {len(content_files)} markdown files in content directory")
        for file in content_files[:5]:  # Show first 5 files
            log(f"- {file}")
        if len(content_files) > 5:
            log(f"  ... and {len(content_files) - 5} more files")
    else:
        log(f"Content directory {content_dir} not found or is not a directory!")
    
    # Check templates directory
    templates_dir = root / "templates"
    log(f"\nTemplates Directory ({templates_dir}):")
    if os.path.exists(templates_dir) and os.path.isdir(templates_dir):
        template_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
        log(f"Found {len(template_files)} template files")
        for file in template_files:
            log(f"- {file}")
    else:
        log(f"Templates directory {templates_dir} not found or is not a directory!")
    
    # Check static directory
    static_dir = root / "static"
    log(f"\nStatic Directory ({static_dir}):")
    if os.path.exists(static_dir) and os.path.isdir(static_dir):
        css_files = [f for f in os.listdir(static_dir) if f.endswith('.css')]
        js_files = [f for f in os.listdir(static_dir) if f.endswith('.js')]
        
        log(f"Found {len(css_files)} CSS files and {len(js_files)} JS files")
        
        if css_files:
            log("CSS files:")
            for file in css_files:
                log(f"- {file}")
        
        if js_files:
            log("JS files:")
            for file in js_files:
                log(f"- {file}")
    else:
        log(f"Static directory {static_dir} not found or is not a directory!")
    
    log("\nDatabase debugging complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())