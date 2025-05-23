#!/usr/bin/env python
"""
Local HTML generator for TIL Blog
Run this locally to generate a static site and commit to GitHub
"""
import os
import sys
import time
import shutil
from pathlib import Path
import sqlite3
import traceback

# Configuration
BUILD_DIR = Path("build")
STATIC_DIR = Path("static") if Path("static").exists() else None
DATABASE_PATH = "til.db"  # Change this to your actual database file

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def ensure_dir(path):
    """Create directory if it doesn't exist"""
    if not path.exists():
        path.mkdir(parents=True)
        log(f"Created directory: {path}")

def get_data_from_database():
    """Get entries and topics from the database"""
    try:
        log(f"Connecting to database: {DATABASE_PATH}")
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        
        # Get entries
        log("Fetching entries from database...")
        entries = conn.execute("""
            SELECT 
                id, 
                title,
                created,
                updated,
                topic,
                path
            FROM entries
            ORDER BY created DESC
        """).fetchall()
        
        # Convert to list of dictionaries
        entries_list = []
        for entry in entries:
            entry_dict = dict(entry)
            
            # Try to get the content from the file
            try:
                if 'path' in entry_dict and entry_dict['path']:
                    with open(entry_dict['path'], 'r') as f:
                        entry_dict['content'] = f.read()
                else:
                    entry_dict['content'] = "Content not available"
            except Exception as e:
                log(f"Error reading content file: {e}")
                entry_dict['content'] = "Error reading content"
                
            entries_list.append(entry_dict)
            
        log(f"Found {len(entries_list)} entries")
        
        # Get topics
        log("Fetching topics from database...")
        topics = conn.execute("""
            SELECT DISTINCT topic
            FROM entries
            WHERE topic IS NOT NULL
        """).fetchall()
        
        topics_list = [{'topic': topic['topic']} for topic in topics if topic['topic']]
        log(f"Found {len(topics_list)} topics")
        
        conn.close()
        
        return {
            'entries': entries_list,
            'topics': topics_list
        }
        
    except Exception as e:
        log(f"Error accessing database: {e}")
        log(traceback.format_exc())
        
        # Return fallback data
        return {
            'entries': [
                {
                    'id': 'sample-1',
                    'title': 'Sample TIL Entry 1',
                    'created': time.strftime('%Y-%m-%d'),
                    'topic': 'python',
                    'content': 'This is a sample TIL entry about Python.'
                },
                {
                    'id': 'sample-2',
                    'title': 'Sample TIL Entry 2',
                    'created': time.strftime('%Y-%m-%d'),
                    'topic': 'flask',
                    'content': 'This is a sample TIL entry about Flask.'
                }
            ],
            'topics': [
                {'topic': 'python'},
                {'topic': 'flask'}
            ]
        }

def generate_static_site(data):
    """Generate static HTML files for the TIL blog"""
    # Clean build directory
    if BUILD_DIR.exists():
        log(f"Removing existing build directory: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)
    
    ensure_dir(BUILD_DIR)
    log(f"Created fresh build directory: {BUILD_DIR}")
    
    # Generate index.html (home page)
    with open(BUILD_DIR / "index.html", "w") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Today I Learned</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
        }}
        header {{
            background-color: #3498db;
            color: white;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        h1 {{
            margin: 0;
        }}
        .topics {{
            background-color: #f8f9fa;
            padding: 0.5rem;
            margin-bottom: 1rem;
        }}
        .topics ul {{
            list-style: none;
            display: flex;
            flex-wrap: wrap;
            padding: 0;
            margin: 0;
        }}
        .topics li {{
            margin-right: 1rem;
            margin-bottom: 0.5rem;
        }}
        .entry-list {{
            list-style: none;
            padding: 0;
        }}
        .entry-list li {{
            margin-bottom: 0.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #eee;
        }}
        .entry-list .title {{
            font-weight: 500;
        }}
        .entry-list .topic {{
            color: #666;
            font-size: 0.9rem;
        }}
        .entry-list time {{
            color: #666;
            font-size: 0.9rem;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        footer {{
            margin-top: 2rem;
            color: #666;
            font-size: 0.9rem;
            text-align: center;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Today I Learned</h1>
    </header>
    
    <div class="topics">
        <ul>
""")
        # Add topics
        for topic in data['topics']:
            f.write(f'            <li><a href="topic/{topic["topic"]}.html">{topic["topic"]}</a></li>\n')
            
        f.write("""        </ul>
    </div>
    
    <main>
        <ul class="entry-list">
""")
        # Add entries
        for entry in data['entries']:
            topic = entry.get('topic', 'general')
            created = entry.get('created', time.strftime('%Y-%m-%d'))
            f.write(f'            <li>\n')
            f.write(f'                <a href="til/{entry["id"]}.html">\n')
            f.write(f'                    <span class="title">{entry["title"]}</span>\n')
            f.write(f'                    <span class="topic">{topic}</span>\n')
            f.write(f'                    <time datetime="{created}">{created}</time>\n')
            f.write(f'                </a>\n')
            f.write(f'            </li>\n')
            
        f.write("""        </ul>
    </main>
    
    <footer>
        <p>Generated on """ + time.strftime('%Y-%m-%d %H:%M:%S') + """</p>
    </footer>
</body>
</html>""")
    
    log("Generated index.html")
    
    # Create individual entry pages
    entries_dir = BUILD_DIR / "til"
    ensure_dir(entries_dir)
    
    for entry in data['entries']:
        entry_path = entries_dir / f"{entry['id']}.html"
        topic = entry.get('topic', 'general')
        created = entry.get('created', time.strftime('%Y-%m-%d'))
        content = entry.get('content', 'No content available for this entry.')
        
        with open(entry_path, "w") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{entry['title']} | Today I Learned</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
        }}
        header {{
            margin-bottom: 2rem;
        }}
        h1 {{
            margin-bottom: 0.5rem;
        }}
        .meta {{
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        .topic {{
            background-color: #f8f9fa;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }}
        .content {{
            margin-bottom: 2rem;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        footer {{
            margin-top: 2rem;
            color: #666;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{entry['title']}</h1>
        <div class="meta">
            <span class="topic">{topic}</span>
            <time datetime="{created}">{created}</time>
        </div>
    </header>
    
    <div class="content">
        {content}
    </div>
    
    <footer>
        <p><a href="/">← Back to Home</a></p>
    </footer>
</body>
</html>""")
        log(f"Generated entry page: {entry_path}")
    
    # Create topic pages
    topics_dir = BUILD_DIR / "topic"
    ensure_dir(topics_dir)
    
    for topic_dict in data['topics']:
        topic_name = topic_dict['topic']
        topic_path = topics_dir / f"{topic_name}.html"
        
        # Filter entries for this topic
        topic_entries = [e for e in data['entries'] if e.get('topic') == topic_name]
        
        with open(topic_path, "w") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Topic: {topic_name} | Today I Learned</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
        }}
        header {{
            background-color: #3498db;
            color: white;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        h1 {{
            margin: 0;
        }}
        .entry-list {{
            list-style: none;
            padding: 0;
        }}
        .entry-list li {{
            margin-bottom: 0.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #eee;
        }}
        .entry-list .title {{
            font-weight: 500;
        }}
        .entry-list time {{
            color: #666;
            font-size: 0.9rem;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        footer {{
            margin-top: 2rem;
            color: #666;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Topic: {topic_name}</h1>
    </header>
    
    <main>
        <ul class="entry-list">
""")
            # Add entries for this topic
            for entry in topic_entries:
                created = entry.get('created', time.strftime('%Y-%m-%d'))
                f.write(f'            <li>\n')
                f.write(f'                <a href="../til/{entry["id"]}.html">\n')
                f.write(f'                    <span class="title">{entry["title"]}</span>\n')
                f.write(f'                    <time datetime="{created}">{created}</time>\n')
                f.write(f'                </a>\n')
                f.write(f'            </li>\n')
            
            if not topic_entries:
                f.write('            <li>No entries found for this topic</li>\n')
                
            f.write("""        </ul>
    </main>
    
    <footer>
        <p><a href="../index.html">← Back to Home</a></p>
    </footer>
</body>
</html>""")
        log(f"Generated topic page: {topic_path}")
    
    # Copy static files if they exist
    if STATIC_DIR and STATIC_DIR.exists():
        static_target = BUILD_DIR / STATIC_DIR.name
        if static_target.exists():
            shutil.rmtree(static_target)
        
        shutil.copytree(STATIC_DIR, static_target)
        log(f"Copied static files to {static_target}")
    else:
        log("No static directory found, skipping static files")
    
    # Create .nojekyll file to prevent GitHub Pages from using Jekyll
    with open(BUILD_DIR / ".nojekyll", "w") as f:
        f.write("")
    
    log("Created .nojekyll file")
    log("Static site generation complete!")

def main():
    log("Starting TIL blog local HTML generation")
    
    # Get data from database
    data = get_data_from_database()
    
    # Generate static site
    generate_static_site(data)
    
    # Print instructions
    print("\n" + "="*60)
    print("LOCAL BUILD COMPLETED SUCCESSFULLY")
    print("="*60)
    print("\nTo deploy to GitHub Pages:")
    print("\n1. Commit the 'build' directory to your repository:")
    print("   git add build")
    print("   git commit -m \"Update static site\"")
    print("   git push origin main")
    print("\n2. Configure GitHub Pages in your repository settings:")
    print("   - Go to Settings > Pages")
    print("   - Source: Deploy from a branch")
    print("   - Branch: main")
    print("   - Folder: /build")
    print("   - Save")
    print("\nYour site will be available at: https://YOUR_USERNAME.github.io/TILBlog/")
    print("="*60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())