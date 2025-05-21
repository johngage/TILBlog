#!/usr/bin/env python
"""
Robust static site generator for TIL Blog
With enhanced error handling and debugging
"""
import os
import sys
import time
import re
import shutil
import traceback
from pathlib import Path
import sqlite3

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()  # Ensure logs are immediately visible in GitHub Actions

def ensure_dir(path):
    """Create directory if it doesn't exist"""
    if not path.exists():
        path.mkdir(parents=True)
        log(f"Created directory: {path}")

def read_app_code():
    """Read the app.py code and log its contents for debugging"""
    try:
        with open('app.py', 'r') as f:
            app_code = f.read()
        
        log(f"Successfully read app.py ({len(app_code)} bytes)")
        
        # Log the first few lines to help with debugging
        first_lines = app_code.split('\n')[:20]
        log("First 20 lines of app.py:")
        for i, line in enumerate(first_lines):
            log(f"{i+1:02d}: {line}")
            
        return app_code
    except Exception as e:
        log(f"Error reading app.py: {e}")
        return None

def extract_database_path_from_code(app_code):
    """Try to extract the database path from app.py code"""
    if not app_code:
        return None
    
    # Common patterns for SQLite database paths
    patterns = [
        r"DATABASE\s*=\s*['\"](.+?)['\"]",
        r"database\s*=\s*['\"](.+?)['\"]",
        r"db_path\s*=\s*['\"](.+?)['\"]",
        r"sqlite:///(.+?)[\"\']"
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, app_code, re.IGNORECASE)
        if matches:
            db_path = matches.group(1)
            log(f"Found database path in code: {db_path}")
            return db_path
            
    log("Could not find database path in app.py")
    return None

def connect_to_database(db_path=None):
    """Try to connect to the SQLite database"""
    log("Attempting to connect to database...")
    
    # List of possible database paths to try
    paths_to_try = []
    
    if db_path:
        paths_to_try.append(db_path)
    
    # Add common default paths
    paths_to_try.extend([
        'til.db',
        'app.db',
        'database.db',
        'blog.db',
        'tilblog.db'
    ])
    
    # Check for any .db files in the current directory
    for file in os.listdir('.'):
        if file.endswith('.db') and file not in paths_to_try:
            paths_to_try.append(file)
    
    # Try each path
    for path in paths_to_try:
        log(f"Trying database path: {path}")
        try:
            conn = sqlite3.connect(path)
            
            # Test query to ensure it's a valid database
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            log(f"Connected to database at {path}")
            log(f"Found tables: {[t[0] for t in tables]}")
            
            return conn, path
        except sqlite3.Error as e:
            log(f"Failed to connect to {path}: {e}")
            continue
    
    log("Could not connect to any database")
    return None, None

def get_sample_data_from_db(conn):
    """Try to extract entries and topics from the database"""
    if not conn:
        log("No database connection, using fallback data")
        return get_fallback_data()
    
    try:
        # Try to determine the table structure
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        
        log(f"Available tables: {table_names}")
        
        # Find the entries table
        entries_table = None
        for table in table_names:
            if table.lower() in ['entries', 'posts', 'tils', 'notes', 'articles']:
                entries_table = table
                break
        
        if not entries_table:
            log("Could not identify entries table, trying first table")
            if table_names:
                entries_table = table_names[0]
            else:
                log("No tables found in database")
                return get_fallback_data()
        
        # Get table columns
        columns_info = conn.execute(f"PRAGMA table_info({entries_table})").fetchall()
        column_names = [c[1] for c in columns_info]
        
        log(f"Columns in {entries_table}: {column_names}")
        
        # Try to identify key columns
        id_col = next((c for c in column_names if c.lower() in ['id', 'entry_id', 'post_id']), None)
        title_col = next((c for c in column_names if c.lower() in ['title', 'name', 'subject']), None)
        content_col = next((c for c in column_names if c.lower() in ['content', 'body', 'text']), None)
        topic_col = next((c for c in column_names if c.lower() in ['topic', 'category', 'tag']), None)
        date_col = next((c for c in column_names if c.lower() in ['created', 'date', 'timestamp', 'published']), None)
        
        if not id_col or not title_col:
            log("Could not identify required columns")
            return get_fallback_data()
        
        # Build query dynamically based on available columns
        select_cols = [id_col, title_col]
        if date_col:
            select_cols.append(date_col)
        if topic_col:
            select_cols.append(topic_col)
        if content_col:
            select_cols.append(content_col)
            
        # Get entries
        query = f"SELECT {', '.join(select_cols)} FROM {entries_table} ORDER BY {date_col or id_col} DESC LIMIT 10"
        log(f"Executing query: {query}")
        
        entries_raw = conn.execute(query).fetchall()
        log(f"Found {len(entries_raw)} entries")
        
        # Convert to dictionaries with standardized keys
        entries = []
        for entry in entries_raw:
            entry_dict = {}
            for i, col in enumerate(select_cols):
                if col == id_col:
                    entry_dict['id'] = str(entry[i])
                elif col == title_col:
                    entry_dict['title'] = entry[i]
                elif col == date_col:
                    entry_dict['created'] = entry[i]
                elif col == topic_col:
                    entry_dict['topic'] = entry[i] or 'general'
                elif col == content_col:
                    entry_dict['content'] = entry[i]
            entries.append(entry_dict)
        
        # Get topics
        topics = []
        if topic_col:
            topic_query = f"SELECT DISTINCT {topic_col} FROM {entries_table} WHERE {topic_col} IS NOT NULL"
            topics_raw = conn.execute(topic_query).fetchall()
            topics = [{'topic': t[0]} for t in topics_raw if t[0]]
        
        if not topics:
            # Add at least one topic
            topics = [{'topic': 'general'}]
        
        log(f"Found {len(topics)} topics")
        
        return {
            'entries': entries,
            'topics': topics
        }
            
    except Exception as e:
        log(f"Error extracting data from database: {e}")
        log(traceback.format_exc())
        return get_fallback_data()

def get_fallback_data():
    """Return fallback sample data when database access fails"""
    log("Using fallback sample data")
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
            },
            {
                'id': 'sample-3',
                'title': 'Sample TIL Entry 3',
                'created': time.strftime('%Y-%m-%d'),
                'topic': 'github',
                'content': 'This is a sample TIL entry about GitHub.'
            }
        ],
        'topics': [
            {'topic': 'python'},
            {'topic': 'flask'},
            {'topic': 'github'}
        ]
    }

def generate_static_site(build_dir, data):
    """Generate static HTML files for the TIL blog"""
    # Generate index.html (home page)
    with open(build_dir / "index.html", "w") as f:
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
            padding: 0;
            margin: 0;
        }}
        .topics li {{
            margin-right: 1rem;
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
            f.write(f'            <li><a href="/topic/{topic["topic"]}.html">{topic["topic"]}</a></li>\n')
            
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
            f.write(f'                <a href="/til/{entry["id"]}.html">\n')
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
    entries_dir = build_dir / "til"
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
    topics_dir = build_dir / "topic"
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
                f.write(f'                <a href="/til/{entry["id"]}.html">\n')
                f.write(f'                    <span class="title">{entry["title"]}</span>\n')
                f.write(f'                    <time datetime="{created}">{created}</time>\n')
                f.write(f'                </a>\n')
                f.write(f'            </li>\n')
            
            if not topic_entries:
                f.write('            <li>No entries found for this topic</li>\n')
                
            f.write("""        </ul>
    </main>
    
    <footer>
        <p><a href="/">← Back to Home</a></p>
    </footer>
</body>
</html>""")
        log(f"Generated topic page: {topic_path}")

def main():
    """Main build process with robust error handling"""
    log("Starting TIL blog static generation with robust error handling")
    
    # Configuration
    BUILD_DIR = Path("build")
    STATIC_DIR = Path("static") if Path("static").exists() else None
    
    # Clean build directory
    if BUILD_DIR.exists():
        log(f"Removing existing build directory: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)
    
    ensure_dir(BUILD_DIR)
    log(f"Created fresh build directory: {BUILD_DIR}")
    
    # Environment info
    log(f"Python version: {sys.version}")
    log(f"Working directory: {os.getcwd()}")
    
    # Check if we're running in GitHub Actions
    is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    log(f"Running in GitHub Actions: {is_github_actions}")
    
    # List current directory contents
    log("Current directory contents:")
    for item in os.listdir('.'):
        log(f"  - {item}")
    
    # Try to get data from the app
    try:
        # Read app.py code
        app_code = read_app_code()
        
        # Extract database path if possible
        db_path = extract_database_path_from_code(app_code)
        
        # Connect to database
        conn, db_file = connect_to_database(db_path)
        
        # Get data from database
        data = get_sample_data_from_db(conn)
        
        # Generate static site
        generate_static_site(BUILD_DIR, data)
        
        # Close database connection if open
        if conn:
            conn.close()
            log(f"Closed database connection to {db_file}")
    except Exception as e:
        log(f"Error during site generation: {e}")
        log(traceback.format_exc())
        
        # Create a simple fallback page
        with open(BUILD_DIR / "index.html", "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIL Blog - Error Recovery Page</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        h1 { color: #3498db; }
        .note { background: #f8f9fa; padding: 1rem; border-left: 4px solid #3498db; }
        pre { background: #f8f9fa; padding: 1rem; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>TIL Blog - Error Recovery Page</h1>
    
    <div class="note">
        <p>An error occurred during site generation, but we've created this recovery page.</p>
    </div>
    
    <h2>Next Steps:</h2>
    <ol>
        <li>Check the GitHub Actions logs for detailed error information</li>
        <li>Make sure your app.py file is compatible with the static generator</li>
        <li>Verify that your database is accessible</li>
    </ol>

    <footer>
        <p>Generated on: """ + time.strftime('%Y-%m-%d %H:%M:%S') + """</p>
    </footer>
</body>
</html>""")
        log("Created fallback index.html due to error")
    
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
    
    return 0

if __name__ == "__main__":
    sys.exit(main())