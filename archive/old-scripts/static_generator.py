#!/usr/bin/env python
"""
Static content generator for TIL Blog
Works without starting a Flask server
Uses app.py functionality to access database and templates
"""
import os
import sys
import time
import re
import shutil
import importlib.util
import sqlite3
from pathlib import Path
import json

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()

def ensure_dir(path):
    """Create directory if it doesn't exist"""
    if not path.exists():
        path.mkdir(parents=True)
        log(f"Created directory: {path}")

def load_app_module():
    """Load app.py as a module without executing main code"""
    log("Loading app.py as a module...")
    
    # Import app.py as a module
    try:
        # First, add the current directory to sys.path to ensure app can be imported
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Set an environment variable to indicate we're in build mode
        os.environ['FLASK_STATIC_BUILD'] = 'True'
        
        # Now try to import app directly
        import app
        
        # Check if app has the Flask app object
        if not hasattr(app, 'app'):
            log("Error: app.py does not have a 'app' attribute (Flask app instance)")
            return None
            
        # Check if database exists
        if not os.path.exists(app.root / app.DATABASE):
            log(f"Database not found at {app.root / app.DATABASE}, building it...")
            app.build_database(app.root)
            
        log("Successfully imported app.py")
        return app
    except Exception as e:
        log(f"Error importing app.py: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_db_connection(app_module):
    """Get database connection directly without using Flask's g object"""
    try:
        db_path = app_module.root / app_module.DATABASE
        log(f"Opening direct connection to database: {db_path}")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        log(f"Error connecting to database: {e}")
        return None

def modify_template_for_static(template_content):
    """Modify a template to use static URLs for CSS and JS"""
    # Replace url_for('static', filename='...') with direct static paths
    template_content = template_content.replace(
        "{{ url_for('static', filename='styles.css') }}", 
        "/static/styles.css"
    )
    
    # Replace other static files if needed
    template_content = template_content.replace(
        "{{ url_for('static', filename='script.js') }}", 
        "/static/script.js"
    )
    
    return template_content

def main():
    """Main build process that works without starting Flask"""
    log("Starting TIL blog static generation")
    
    # Configuration
    BUILD_DIR = Path("build")
    STATIC_DIR = Path("static") if Path("static").exists() else None
    TEMPLATES_DIR = Path("templates") if Path("templates").exists() else None
    
    # Clean build directory
    if BUILD_DIR.exists():
        log(f"Removing existing build directory: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)
    
    ensure_dir(BUILD_DIR)
    log(f"Created fresh build directory: {BUILD_DIR}")
    
    # Check if we're running in GitHub Actions
    is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    log(f"Running in GitHub Actions: {is_github_actions}")
    
    # Load the app module
    app_module = load_app_module()
    
    if app_module is None:
        log("Failed to load app module, creating simple test page instead")
        # Create simple index.html
        with open(BUILD_DIR / "index.html", "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>TIL Blog - Build Test</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <h1>TIL Blog - Build Test</h1>
    <p>Failed to load app module. This is a fallback page.</p>
</body>
</html>""")
    else:
        log("Successfully loaded app module")
        
        # Create a simple template with direct static paths
        with open(BUILD_DIR / "index.html", "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>TIL Blog</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <h1>TIL Blog</h1>
        <p>This site is currently running in static mode.</p>
        <p>Your content has been successfully deployed to GitHub Pages!</p>
        
        <h2>Recent Entries</h2>
        <ul>
""")
            
            # Open direct database connection
            conn = get_db_connection(app_module)
            
            if conn:
                # Get recent entries
                try:
                    entries = conn.execute(
                        """
                        SELECT id, slug, title, 
                               COALESCE(created_fm, created_fs) as created
                        FROM entries
                        ORDER BY COALESCE(created_fm, created_fs) DESC
                        LIMIT 20
                        """
                    ).fetchall()
                    
                    for entry in entries:
                        f.write(f'            <li><a href="/til/{entry["slug"]}">{entry["title"]}</a> <span class="date">{entry["created"]}</span></li>\n')
                    
                    log(f"Added {len(entries)} entries to index.html")
                except Exception as e:
                    log(f"Error getting entries: {e}")
                    f.write('            <li>Error retrieving entries</li>\n')
            else:
                f.write('            <li>Database connection failed</li>\n')
                
            # Close the HTML
            f.write("""        </ul>
        
        <h2>Topics</h2>
        <div class="topic-cloud">
""")
            
            # Add topics if database connection is available
            if conn:
                try:
                    topics = conn.execute(
                        """
                        SELECT t.name as topic, COUNT(*) as count
                        FROM topics t
                        JOIN entry_topics et ON t.id = et.topic_id
                        GROUP BY t.name
                        ORDER BY t.name ASC
                        """
                    ).fetchall()
                    
                    for topic in topics:
                        f.write(f'            <a href="/topic/{topic["topic"]}">{topic["topic"]} ({topic["count"]})</a>\n')
                    
                    log(f"Added {len(topics)} topics to index.html")
                except Exception as e:
                    log(f"Error getting topics: {e}")
                    f.write('            <p>Error retrieving topics</p>\n')
            
            # Finish the HTML
            f.write("""        </div>
    </div>
    
    <footer>
        <p>TIL Blog - Generated on """ + time.strftime('%Y-%m-%d') + """</p>
    </footer>
</body>
</html>""")
            
            log("Generated custom index.html with direct static references")
    
    # Generate a custom CSS file if not copying from static directory
    if STATIC_DIR and STATIC_DIR.exists():
        static_target = BUILD_DIR / "static"
        if static_target.exists():
            shutil.rmtree(static_target)
        
        shutil.copytree(STATIC_DIR, static_target)
        log(f"Copied static files to {static_target}")
        
        # Check if styles.css exists
        styles_css = static_target / "styles.css"
        if styles_css.exists():
            log(f"Found styles.css ({os.path.getsize(styles_css)} bytes)")
        else:
            # Create styles.css if it doesn't exist
            log("styles.css not found in static directory, creating default CSS")
            with open(static_target / "styles.css", "w") as f:
                f.write("""
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    color: #333;
}

h1 {
    font-size: 2rem;
    margin-bottom: 1rem;
    color: #3498db;
}

h2 {
    font-size: 1.5rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: #2c3e50;
}

a {
    color: #3498db;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

ul {
    padding-left: 1.5rem;
}

li {
    margin-bottom: 0.5rem;
}

.date {
    color: #7f8c8d;
    font-size: 0.9rem;
}

.topic-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1rem;
}

.topic-cloud a {
    background-color: #f1f1f1;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.9rem;
}

footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid #eee;
    color: #95a5a6;
    font-size: 0.9rem;
}
""")
            log("Created default styles.css")
    else:
        log("No static directory found, creating one")
        static_target = BUILD_DIR / "static"
        ensure_dir(static_target)
        
        # Create a basic CSS file
        with open(static_target / "styles.css", "w") as f:
            f.write("""
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    color: #333;
}

h1 {
    font-size: 2rem;
    margin-bottom: 1rem;
    color: #3498db;
}

h2 {
    font-size: 1.5rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: #2c3e50;
}

a {
    color: #3498db;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

ul {
    padding-left: 1.5rem;
}

li {
    margin-bottom: 0.5rem;
}

.date {
    color: #7f8c8d;
    font-size: 0.9rem;
}

.topic-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1rem;
}

.topic-cloud a {
    background-color: #f1f1f1;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.9rem;
}

footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid #eee;
    color: #95a5a6;
    font-size: 0.9rem;
}
""")
        log("Created static directory with default styles.css")
    
    # Create .nojekyll file to prevent GitHub Pages from using Jekyll
    with open(BUILD_DIR / ".nojekyll", "w") as f:
        f.write("")
    
    log("Created .nojekyll file")
    log("Static site generation complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())