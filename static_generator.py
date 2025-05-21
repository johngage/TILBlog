#!/usr/bin/env python
"""
Static content generator for TIL Blog
Works without starting a Flask server
We really hope this works
"""
import os
import sys
import time
import re
import shutil
import importlib.util
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
    # FIX: Change the module name to something other than "app_module"
    # because we're importing the actual file, not a module named app_module
    spec = importlib.util.spec_from_file_location("app_script", "app.py")
    app_script = importlib.util.module_from_spec(spec)
    
    # Prepare a dummy sys.argv to prevent the app from running in main mode
    original_argv = sys.argv
    sys.argv = [sys.argv[0], 'build']
    
    try:
        # Execute the module
        spec.loader.exec_module(app_script)
        return app_script
    except Exception as e:
        log(f"Error loading app.py: {e}")
        return None
    finally:
        # Restore original argv
        sys.argv = original_argv

def render_template_directly(app_module, template_name, **context):
    """Render a template directly using Jinja2 without Flask running"""
    log(f"Rendering template: {template_name}")
    
    try:
        # Get the Jinja environment from Flask
        if hasattr(app_module, 'app') and hasattr(app_module.app, 'jinja_env'):
            jinja_env = app_module.app.jinja_env
            template = jinja_env.get_template(template_name)
            return template.render(**context)
        else:
            log("No Flask app or Jinja environment found")
            return None
    except Exception as e:
        log(f"Error rendering template: {e}")
        return None

def get_sample_data_from_app(app_module):
    """Extract sample data from the app for rendering templates"""
    sample_data = {}
    
    # Try to get database connection and extract data
    if hasattr(app_module, 'get_db'):
        try:
            log("Getting database connection...")
            conn = app_module.get_db()
            
            # Get recent entries
            log("Fetching entries from database...")
            entries = conn.execute(
                """
                SELECT id, title, created, topic
                FROM entries
                ORDER BY created DESC
                LIMIT 10
                """
            ).fetchall()
            
            # Convert row objects to dictionaries
            sample_data['entries'] = [dict(entry) for entry in entries]
            
            # Get topics
            topics = conn.execute(
                """
                SELECT DISTINCT topic
                FROM entries
                """
            ).fetchall()
            sample_data['topics'] = [dict(topic) for topic in topics]
            
            log(f"Got {len(sample_data['entries'])} entries and {len(sample_data['topics'])} topics")
            
        except Exception as e:
            log(f"Error getting data from database: {e}")
            # Provide fallback sample data
            sample_data = {
                'entries': [
                    {'id': 'sample-1', 'title': 'Sample TIL 1', 'created': '2023-01-01', 'topic': 'python'},
                    {'id': 'sample-2', 'title': 'Sample TIL 2', 'created': '2023-01-02', 'topic': 'flask'},
                ],
                'topics': [
                    {'topic': 'python'},
                    {'topic': 'flask'},
                ]
            }
    else:
        log("No get_db function found in app.py, using fallback data")
        # Provide fallback sample data
        sample_data = {
            'entries': [
                {'id': 'sample-1', 'title': 'Sample TIL 1', 'created': '2023-01-01', 'topic': 'python'},
                {'id': 'sample-2', 'title': 'Sample TIL 2', 'created': '2023-01-02', 'topic': 'flask'},
            ],
            'topics': [
                {'topic': 'python'},
                {'topic': 'flask'},
            ]
        }
    
    return sample_data

def main():
    """Main build process that works without starting Flask"""
    log("Starting TIL blog static generation (Flask adapter mode)")
    
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
        
        # Get sample data for rendering templates
        sample_data = get_sample_data_from_app(app_module)
        
        # Render home page template
        home_html = render_template_directly(app_module, 'index.html', 
                                             entries=sample_data['entries'],
                                             topics=sample_data['topics'])
        
        if home_html:
            # Save home page
            with open(BUILD_DIR / "index.html", "w") as f:
                f.write(home_html)
            log("Generated index.html")
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
    <h2>Sample Entries:</h2>
    <ul>
""")
                # Add sample entries
                for entry in sample_data['entries']:
                    f.write(f"        <li>{entry['title']} ({entry['topic']})</li>\n")
                
                f.write("""    </ul>
</body>
</html>""")
        
        # Create individual entry pages
        entries_dir = BUILD_DIR / "til"
        ensure_dir(entries_dir)
        
        for entry in sample_data['entries']:
            entry_path = entries_dir / f"{entry['id']}.html"
            with open(entry_path, "w") as f:
                f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{entry['title']} | TIL Blog</title>
</head>
<body>
    <h1>{entry['title']}</h1>
    <p>Topic: {entry['topic']}</p>
    <p>Created: {entry['created']}</p>
    <div class="content">
        <p>This is a placeholder for the content of TIL entry "{entry['id']}".</p>
    </div>
    <p><a href="/">Back to Home</a></p>
</body>
</html>""")
            log(f"Generated entry page: {entry_path}")
        
        # Create topic pages
        topics_dir = BUILD_DIR / "topic"
        ensure_dir(topics_dir)
        
        for topic in sample_data['topics']:
            topic_name = topic['topic']
            topic_path = topics_dir / f"{topic_name}.html"
            
            # Filter entries for this topic
            topic_entries = [e for e in sample_data['entries'] if e['topic'] == topic_name]
            
            with open(topic_path, "w") as f:
                f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Topic: {topic_name} | TIL Blog</title>
</head>
<body>
    <h1>Topic: {topic_name}</h1>
    <ul>
""")
                # Add entries for this topic
                for entry in topic_entries:
                    f.write(f'        <li><a href="/til/{entry["id"]}.html">{entry["title"]}</a></li>\n')
                
                f.write("""    </ul>
    <p><a href="/">Back to Home</a></p>
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
    
    return 0

if __name__ == "__main__":
    sys.exit(main())