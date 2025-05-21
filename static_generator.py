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

def generate_entry_pages(app_module, build_dir):
    """Generate individual entry pages"""
    log("Generating entry pages...")
    
    # Get database connection
    try:
        conn = app_module.get_db()
        log("Successfully connected to database")
        
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
            html = render_template_using_jinja(
                app_module, 
                'entry.html', 
                entry=entry, 
                entry_topics=entry_topics,
                topic_cloud=topic_cloud,
                related=related
            )
            
            if html:
                # Create slug-based URL directory
                entry_path = entries_dir / entry['slug']
                ensure_dir(entry_path)
                
                # Write index.html in that directory
                with open(entry_path / "index.html", "w", encoding="utf-8") as f:
                    f.write(html)
                
                log(f"Generated entry page: {entry['slug']}")
            else:
                log(f"Failed to render entry page for {entry['slug']}")
        
        return True
    except Exception as e:
        log(f"Error generating entry pages: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_topic_pages(app_module, build_dir):
    """Generate topic index pages"""
    log("Generating topic pages...")
    
    try:
        conn = app_module.get_db()
        
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
            html = render_template_using_jinja(
                app_module,
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
                # Create topic directory
                topic_path = topics_dir / topic
                ensure_dir(topic_path)
                
                # Write index.html
                with open(topic_path / "index.html", "w", encoding="utf-8") as f:
                    f.write(html)
                
                log(f"Generated topic page: {topic}")
            else:
                log(f"Failed to render topic page for {topic}")
        
        return True
    except Exception as e:
        log(f"Error generating topic pages: {e}")
        import traceback
        traceback.print_exc()
        return False

def render_template_using_jinja(app_module, template_name, **context):
    """Render a template directly using the Flask app"""
    log(f"Rendering template: {template_name}")
    
    try:
        # Get Flask app
        flask_app = app_module.app
        
        # Create a dummy request context
        with flask_app.test_request_context():
            # Try to use Flask's render_template function
            from flask import render_template
            return render_template(template_name, **context)
    except Exception as e:
        log(f"Error rendering template with Flask: {e}")
        
        # Fallback: Try to render directly with Jinja
        try:
            jinja_env = app_module.app.jinja_env
            template = jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e2:
            log(f"Error rendering with Jinja directly: {e2}")
            return None

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
        
        # Get database connection
        conn = app_module.get_db()
        
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
        
        # Render home page
        home_html = render_template_using_jinja(
            app_module,
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
            # Save home page
            with open(BUILD_DIR / "index.html", "w", encoding="utf-8") as f:
                f.write(home_html)
            log("Generated index.html")
            
            # Generate entry pages
            generate_entry_pages(app_module, BUILD_DIR)
            
            # Generate topic pages
            generate_topic_pages(app_module, BUILD_DIR)
            
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