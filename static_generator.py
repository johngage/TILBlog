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
            
        # Configure Flask app for static site generation
        log("Configuring Flask app for static site generation")
        app.app.config['SERVER_NAME'] = 'localhost:5000'  # Dummy server name
        app.app.config['APPLICATION_ROOT'] = '/'
        app.app.config['PREFERRED_URL_SCHEME'] = 'http'
        
        # Important: we need to fix url_for to generate relative URLs
        from flask import url_for as flask_url_for
        
        def static_url_for(*args, **kwargs):
            """Generate static-friendly URLs (relative paths) for static site"""
            # For static files, use a relative path
            if args and args[0] == 'static':
                return f"/static/{kwargs.get('filename', '')}"
            # For other URLs, try to make them relative
            try:
                url = flask_url_for(*args, **kwargs)
                # Remove http://localhost:5000 prefix from URLs
                url = url.replace('http://localhost:5000', '')
                return url
            except Exception as e:
                log(f"Error generating URL for {args}, {kwargs}: {e}")
                # Return a safe fallback
                return "/"
                
        # Replace url_for with our static version
        app.app.jinja_env.globals['url_for'] = static_url_for
            
        # Check if database exists
        if not os.path.exists(app.root / app.DATABASE):
            log(f"Database not found at {app.root / app.DATABASE}, building it...")
            app.build_database(app.root)
            
        log("Successfully imported and configured app.py")
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

def fix_links_in_html(html):
    """Fix links in HTML for static site deployment"""
    # Convert absolute links to URL-relative links
    html = re.sub(r'href="http://localhost:5000([^"]*)"', r'href="\1"', html)
    
    # Fix links to entry pages
    html = re.sub(r'href="/til/([^"]*)"', r'href="/til/\1/index.html"', html)
    
    # Fix links to topic pages
    html = re.sub(r'href="/topic/([^"]*)"', r'href="/topic/\1/index.html"', html)
    
    return html

def generate_entry_pages(app_module, build_dir, conn):
    """Generate individual entry pages"""
    log("Generating entry pages...")
    
    try:
        # Get all entries
        entries = conn.execute(
            """
            SELECT id, slug, title, html, 
                   COALESCE(created_fm, created_fs) as created,
                   topics_raw
            FROM entries
            ORDER BY COALESCE(created_fm, created_fs) DESC
            """
        ).fetchall()
        
        log(f"Found {len(entries)} entries in database")
        
        # Get all topics for sidebar
        topic_cloud = conn.execute(
            """
            SELECT t.name as topic, COUNT(*) as count
            FROM topics t
            JOIN entry_topics et ON t.id = et.topic_id
            GROUP BY t.name
            ORDER BY t.name ASC
            """
        ).fetchall()
        
        # Create directory for entries
        entries_dir = build_dir / "til"
        ensure_dir(entries_dir)
        
        # Create individual entry pages
        for entry in entries:
            # Get topics for this entry
            entry_topics = conn.execute(
                """
                SELECT t.name
                FROM topics t
                JOIN entry_topics et ON t.id = et.topic_id
                WHERE et.entry_id = ?
                ORDER BY t.name
                """,
                [entry['id']]
            ).fetchall()
            
            # Get related entries (entries that share topics)
            related = conn.execute(
                """
                SELECT DISTINCT e.id, e.slug, e.title
                FROM entries e
                JOIN entry_topics et ON e.id = et.entry_id
                JOIN entry_topics et2 ON et.topic_id = et2.topic_id
                WHERE et2.entry_id = ? AND e.id != ?
                ORDER BY e.title
                LIMIT 5
                """,
                [entry['id'], entry['id']]
            ).fetchall()
            
            # Render template
            with app_module.app.test_request_context():
                from flask import render_template
                try:
                    html = render_template(
                        'entry.html', 
                        entry=entry, 
                        entry_topics=entry_topics,
                        topic_cloud=topic_cloud,
                        related=related
                    )
                    
                    if html:
                        # Fix links in HTML
                        html = fix_links_in_html(html)
                        
                        # Create slug-based URL directory
                        entry_path = entries_dir / entry['slug']
                        ensure_dir(entry_path)
                        
                        # Write index.html in that directory
                        with open(entry_path / "index.html", "w", encoding="utf-8") as f:
                            f.write(html)
                        
                        log(f"Generated entry page: {entry['slug']}")
                    else:
                        log(f"Failed to render entry page for {entry['slug']}")
                except Exception as e:
                    log(f"Error rendering template for {entry['slug']}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return True
    except Exception as e:
        log(f"Error generating entry pages: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_topic_pages(app_module, build_dir, conn):
    """Generate topic index pages"""
    log("Generating topic pages...")
    
    try:
        # Get all topics
        topics = conn.execute(
            """
            SELECT DISTINCT t.name as topic
            FROM topics t
            JOIN entry_topics et ON t.id = et.topic_id
            ORDER BY t.name
            """
        ).fetchall()
        
        log(f"Found {len(topics)} topics")
        
        # Get all topics for sidebar
        topic_cloud = conn.execute(
            """
            SELECT t.name as topic, COUNT(*) as count
            FROM topics t
            JOIN entry_topics et ON t.id = et.topic_id
            GROUP BY t.name
            ORDER BY t.name ASC
            """
        ).fetchall()
        
        # Create directory for topics
        topics_dir = build_dir / "topic"
        ensure_dir(topics_dir)
        
        # Create topic pages
        for topic_row in topics:
            topic = topic_row['topic']
            
            # Get entries for this topic
            entries = conn.execute(
                """
                SELECT e.id, e.slug, e.title, 
                       COALESCE(e.created_fm, e.created_fs) as created
                FROM entries e
                JOIN entry_topics et ON e.id = et.entry_id
                JOIN topics t ON et.topic_id = t.id
                WHERE t.name = ?
                ORDER BY COALESCE(e.created_fm, e.created_fs) DESC
                """,
                [topic]
            ).fetchall()
            
            # Get count
            count = len(entries)
            
            # Render template
            with app_module.app.test_request_context():
                from flask import render_template
                try:
                    html = render_template(
                        'topic.html',
                        entries=entries,
                        topic_cloud=topic_cloud,
                        current_topic=topic,
                        page=1,
                        has_next=False,
                        has_prev=False,
                        count=count,
                        current_order="desc"
                    )
                    
                    if html:
                        # Fix links in HTML
                        html = fix_links_in_html(html)
                        
                        # Create topic directory
                        topic_path = topics_dir / topic
                        ensure_dir(topic_path)
                        
                        # Write index.html
                        with open(topic_path / "index.html", "w", encoding="utf-8") as f:
                            f.write(html)
                        
                        log(f"Generated topic page: {topic}")
                    else:
                        log(f"Failed to render topic page for {topic}")
                except Exception as e:
                    log(f"Error rendering template for topic {topic}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return True
    except Exception as e:
        log(f"Error generating topic pages: {e}")
        import traceback
        traceback.print_exc()
        return False

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
</head>
<body>
    <h1>TIL Blog - Build Test</h1>
    <p>Failed to load app module. This is a fallback page.</p>
</body>
</html>""")
    else:
        log("Successfully loaded app module")
        
        # Ensure database exists and has data
        if not os.path.exists(app_module.root / app_module.DATABASE):
            log("Database not found, building it from content directory...")
            app_module.build_database(app_module.root)
        
        # Open direct database connection without Flask's g
        conn = get_db_connection(app_module)
        
        if conn is None:
            log("Failed to connect to database, creating fallback page")
            with open(BUILD_DIR / "index.html", "w") as f:
                f.write("""<!DOCTYPE html>
<html>
<head>
    <title>TIL Blog - Database Error</title>
</head>
<body>
    <h1>TIL Blog - Database Error</h1>
    <p>Could not connect to the database. This is a fallback page.</p>
</body>
</html>""")
        else:
            # Get all entries for the home page
            entries = conn.execute(
                """
                SELECT id, slug, title, 
                       COALESCE(created_fm, created_fs) as created
                FROM entries
                ORDER BY COALESCE(created_fm, created_fs) DESC
                LIMIT ?
                """,
                [app_module.PER_PAGE]
            ).fetchall()
            
            log(f"Found {len(entries)} entries for home page")
            
            # Get topic cloud for sidebar
            topic_cloud = conn.execute(
                """
                SELECT t.name as topic, COUNT(*) as count
                FROM topics t
                JOIN entry_topics et ON t.id = et.topic_id
                GROUP BY t.name
                ORDER BY t.name ASC
                """
            ).fetchall()
            
            # Get total count of entries
            count = conn.execute("SELECT COUNT(*) as count FROM entries").fetchone()["count"]
            
            # Render home page using Flask's test_request_context()
            with app_module.app.test_request_context():
                from flask import render_template
                try:
                    home_html = render_template(
                        'index.html',
                        entries=entries,
                        topic_cloud=topic_cloud,
                        page=1,
                        has_next=(count > app_module.PER_PAGE),
                        has_prev=False,
                        count=count,
                        current_order="desc"
                    )
                    
                    if home_html:
                        # Fix links in HTML for static site
                        home_html = fix_links_in_html(home_html)
                        
                        # Save home page
                        with open(BUILD_DIR / "index.html", "w", encoding="utf-8") as f:
                            f.write(home_html)
                        log("Generated index.html")
                        
                        # Generate entry pages
                        generate_entry_pages(app_module, BUILD_DIR, conn)
                        
                        # Generate topic pages
                        generate_topic_pages(app_module, BUILD_DIR, conn)
                        
                        # Generate feed file
                        # TODO: Add feed generation
                        
                        # Generate sitemap
                        # TODO: Add sitemap generation
                    else:
                        log("Failed to render index.html, creating fallback page")
                        # Create simple index.html
                        with open(BUILD_DIR / "index.html", "w") as f:
                            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>TIL Blog</title>
</head>
<body>
    <h1>TIL Blog</h1>
    <p>Could not render the template. This is a fallback page.</p>
</body>
</html>""")
                except Exception as e:
                    log(f"Error rendering index template: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Create fallback page
                    with open(BUILD_DIR / "index.html", "w") as f:
                        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>TIL Blog - Rendering Error</title>
</head>
<body>
    <h1>TIL Blog - Rendering Error</h1>
    <p>Error rendering templates: {e}</p>
    <p>Found {len(entries)} entries in the database.</p>
</body>
</html>""")
    
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