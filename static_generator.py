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

def fix_html_paths(html_content):
    """Fix paths in HTML content for static site"""
    # Replace url_for('static', filename='...') style paths
    html_content = re.sub(
        r'href="\s*\{\{\s*url_for\([\'\"]static[\'\"]\s*,\s*filename\s*=\s*[\'\"]([^\'\"]+)[\'\"]\)\s*\}\}\s*"',
        r'href="/static/\1"',
        html_content
    )
    
    # Also catch src attributes for scripts and images
    html_content = re.sub(
        r'src="\s*\{\{\s*url_for\([\'\"]static[\'\"]\s*,\s*filename\s*=\s*[\'\"]([^\'\"]+)[\'\"]\)\s*\}\}\s*"',
        r'src="/static/\1"',
        html_content
    )
    
    # Replace url_for for routes
    html_content = re.sub(
        r'href="\s*\{\{\s*url_for\([\'\"]([\w_]+)[\'\"](?:\s*,\s*([^\}\}]+))?\)\s*\}\}\s*"',
        lambda m: fix_url_for_match(m),
        html_content
    )
    
    # Fix any absolute references that should be relative
    if "href=\"//" in html_content and not "href=\"//cdnjs" in html_content:
        html_content = html_content.replace("href=\"//", "href=\"/")
    
    return html_content

def fix_url_for_match(match):
    """Handle url_for regex matches and convert to proper static URLs"""
    endpoint = match.group(1)
    args = match.group(2)
    
    # Parse the args if present
    arg_dict = {}
    if args:
        args = args.strip()
        parts = args.split(',')
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                    value = value[1:-1]
                arg_dict[key] = value
    
    # Generate appropriate URLs for different endpoints
    if endpoint == 'index':
        return 'href="/"'
    elif endpoint == 'entry':
        slug = arg_dict.get('slug', '')
        return f'href="/til/{slug}"'
    elif endpoint == 'topic':
        topic = arg_dict.get('topic', '')
        return f'href="/topic/{topic}"'
    elif endpoint == 'search':
        return 'href="/search"'
    elif endpoint == 'stats':
        return 'href="/stats"'
    else:
        return f'href="/{endpoint}"'

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

def render_template_direct(app_module, template_name, **context):
    """Render a template directly with Jinja, bypassing Flask's url_for"""
    try:
        # Get Flask app
        flask_app = app_module.app
        
        # Using Jinja2 directly
        jinja_env = flask_app.jinja_env
        template = jinja_env.get_template(template_name)
        html = template.render(**context)
        
        # Fix URLs after rendering
        html = fix_html_paths(html)
        
        return html
    except Exception as e:
        log(f"Error rendering {template_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

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
            html = render_template_direct(
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
            html = render_template_direct(
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
            
            # Render home page directly with Jinja
            home_html = render_template_direct(
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
                generate_entry_pages(app_module, BUILD_DIR, conn)
                
                # Generate topic pages
                generate_topic_pages(app_module, BUILD_DIR, conn)
                
                # Generate search page
                search_html = render_template_direct(
                    app_module,
                    'search.html',
                    entries=[],
                    topic_cloud=topic_cloud,
                    query="",
                    page=1,
                    has_next=False,
                    has_prev=False,
                    count=0
                )
                
                if search_html:
                    ensure_dir(BUILD_DIR / "search")
                    with open(BUILD_DIR / "search" / "index.html", "w", encoding="utf-8") as f:
                        f.write(search_html)
                    log("Generated search page")
                
                # Generate stats page
                topic_stats = conn.execute(
                    """
                    SELECT t.name as topic, COUNT(*) as count 
                    FROM topics t
                    JOIN entry_topics et ON t.id = et.topic_id
                    GROUP BY t.name 
                    ORDER BY count DESC
                    """
                ).fetchall()
                
                date_range = conn.execute(
                    """
                    SELECT MIN(COALESCE(created_fm, created_fs)) as first_entry, 
                           MAX(COALESCE(created_fm, created_fs)) as last_entry
                    FROM entries
                    """,
                    one=True
                ).fetchall()
                
                stats_html = render_template_direct(
                    app_module,
                    'stats.html',
                    topic_cloud=topic_cloud,
                    topic_stats=topic_stats,
                    total_entries=count,
                    date_range=date_range
                )
                
                if stats_html:
                    ensure_dir(BUILD_DIR / "stats")
                    with open(BUILD_DIR / "stats" / "index.html", "w", encoding="utf-8") as f:
                        f.write(stats_html)
                    log("Generated stats page")
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
            log("Warning: styles.css not found in static directory")
            # Look for it elsewhere and copy it if found
            potential_paths = [
                Path("static/css/styles.css"),
                Path("static/style.css"),
                Path("static/main.css"),
                Path("css/styles.css")
            ]
            
            for css_path in potential_paths:
                if css_path.exists():
                    log(f"Found CSS at alternative location: {css_path}")
                    shutil.copy(css_path, static_target / "styles.css")
                    log(f"Copied {css_path} to {static_target / 'styles.css'}")
                    break
    else:
        log("No static directory found, creating one")
        static_target = BUILD_DIR / "static"
        ensure_dir(static_target)
        
        # Create a basic CSS file if none exists
        with open(static_target / "styles.css", "w") as f:
            f.write("""/* Basic TIL Blog Styles */
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    color: #333;
}
h1 { font-size: 1.8rem; color: #2c3e50; }
h2 { font-size: 1.5rem; color: #3498db; }
a { color: #3498db; text-decoration: none; }
a:hover { text-decoration: underline; }
.entry { margin-bottom: 2rem; border-bottom: 1px solid #eee; padding-bottom: 1rem; }
.topics { font-size: 0.8rem; color: #7f8c8d; }
.date { font-size: 0.8rem; color: #95a5a6; }
.topic-cloud { margin-top: 2rem; }
.topic-cloud a { margin-right: 1rem; margin-bottom: 0.5rem; display: inline-block; }
""")
        log("Created basic styles.css file")
    
    # Create .nojekyll file to prevent GitHub Pages from using Jekyll
    with open(BUILD_DIR / ".nojekyll", "w") as f:
        f.write("")
    
    log("Created .nojekyll file")
    log("Static site generation complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())