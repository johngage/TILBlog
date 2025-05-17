import os
import pathlib
import re
import sqlite3
import time
from datetime import datetime
from markdown import markdown
from flask import Flask, g, render_template, request, redirect, url_for, abort, Response
from feedgen.feed import FeedGenerator
from urllib.parse import urljoin

# Configuration
DATABASE = "til.db"
PER_PAGE = 20

# Setup paths
root = pathlib.Path(__file__).parent.resolve()

# Flask application
app = Flask(__name__)
app.config.from_object(__name__)

def get_db():
    """Connect to the database and return a connection object"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(str(root / DATABASE))
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection when request ends"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Execute a query and return the results"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def build_database(root_dir):
    """Build the SQLite database from Markdown files"""
    print(f"Building database from {root_dir}")
    db_path = root_dir / DATABASE
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Create tables
    conn.execute("DROP TABLE IF EXISTS til")
    conn.execute("""
        CREATE TABLE til (
            id INTEGER PRIMARY KEY,
            topic TEXT,
            slug TEXT,
            title TEXT,
            html TEXT,
            created TEXT,
            updated TEXT
        )
    """)
    print("Created til table")
    
    # Create search table
    conn.execute("DROP TABLE IF EXISTS til_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE til_fts USING fts5(
            title,
            html,
            content=til,
            content_rowid=id
        )
    """)
    print("Created til_fts table")
    
    # List all markdown files in content directory first, then fallback to root
    content_dir = root_dir / "content"
    if content_dir.exists():
        all_files = list(content_dir.glob("*/*.md"))
        print(f"Found {len(all_files)} markdown files in content directory")
    else:
        # Fallback to looking in root directory
        all_files = list(root_dir.glob("*/*.md"))
        print(f"Found {len(all_files)} markdown files in root directory")
    
    if not all_files:
        print("No markdown files found! Checking directories:")
        if content_dir.exists():
            print(f"Checking content directory: {content_dir}")
            for d in content_dir.iterdir():
                if d.is_dir():
                    print(f"Directory: {d}")
                    files = list(d.glob("*.md"))
                    for f in files:
                        print(f"  - {f}")
        else:
            print(f"Checking root directory: {root_dir}")
            for d in root_dir.iterdir():
                if d.is_dir():
                    print(f"Directory: {d}")
                    files = list(d.glob("*.md"))
                    for f in files:
                        print(f"  - {f}")
    
    # Process markdown files
    for filepath in all_files:
        # Calculate relative path from content directory or root directory
        if content_dir.exists() and filepath.is_relative_to(content_dir):
            rel_path = filepath.relative_to(content_dir)
        else:
            rel_path = filepath.relative_to(root_dir)
        
        topic = rel_path.parts[0]
        slug = filepath.stem
        
        print(f"Processing: {rel_path} (topic={topic}, slug={slug})")
        
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        # Extract title from first line (remove leading # if present)
        lines = content.strip().splitlines()
        if lines and lines[0].startswith("# "):
            title = lines[0].lstrip("# ").strip()
        else:
            title = slug.replace("-", " ").replace("_", " ").title()
        
        print(f"Title: {title}")
        
        # Render HTML with proper extensions
        html = markdown(
            content,
            extensions=[
                'markdown.extensions.fenced_code',  # For code blocks
                'markdown.extensions.tables',       # For tables
                'markdown.extensions.codehilite',   # For syntax highlighting
                'markdown.extensions.smarty',       # For smart quotes
                'markdown.extensions.nl2br',        # For line breaks
                'markdown.extensions.toc',          # For table of contents
                'markdown.extensions.attr_list',    # For attribute lists
                'markdown.extensions.def_list'      # For definition lists
            ],
            extension_configs={
                'markdown.extensions.codehilite': {
                    'use_pygments': True,
                    'css_class': 'highlight'
                }
            }
        )
        
        print(f"Rendered HTML for {rel_path} - length: {len(html)} chars")
        
        # Get modification time
        created = updated = time.strftime(
            "%Y-%m-%d %H:%M:%S", 
            time.localtime(filepath.stat().st_mtime)
        )
        
        # Insert into database
        conn.execute(
            """
            INSERT INTO til (topic, slug, title, html, created, updated)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [topic, slug, title, html, created, updated],
        )
        print(f"Inserted into database: topic={topic}, slug={slug}")
    
    # Verify contents
    count = conn.execute("SELECT COUNT(*) FROM til").fetchone()[0]
    print(f"Total entries in database: {count}")
    
    # Populate search index
    if count > 0:
        conn.execute("""
            INSERT INTO til_fts (rowid, title, html)
            SELECT id, title, html FROM til
        """)
        print("Populated search index")
    
    conn.commit()
    conn.close()
    print("Database build completed")

# Flask routes

@app.route("/")
def index():
    """Home page - show recent entries"""
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * PER_PAGE
    
    # Get total count
    count = query_db("SELECT COUNT(*) as count FROM til", one=True)["count"]
    
    # Get entries for this page
    entries = query_db(
        """
        SELECT id, topic, slug, title, created
        FROM til
        ORDER BY created DESC
        LIMIT ? OFFSET ?
        """,
        [PER_PAGE, offset]
    )
    
    # Get all topics for navigation
    topics = query_db("SELECT DISTINCT topic FROM til ORDER BY topic")
    topics = [t["topic"] for t in topics]
    
    has_next = offset + PER_PAGE < count
    has_prev = page > 1
    
    return render_template(
        "index.html",
        entries=entries,
        topics=topics,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        count=count
    )

@app.route("/topic/<topic>")
def topic(topic):
    """Show entries for a specific topic"""
    # Check if topic exists
    topic_exists = query_db("SELECT 1 FROM til WHERE topic = ? LIMIT 1", [topic], one=True)
    if not topic_exists:
        abort(404)
    
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * PER_PAGE
    
    # Get total count for this topic
    count = query_db(
        "SELECT COUNT(*) as count FROM til WHERE topic = ?", 
        [topic], 
        one=True
    )["count"]
    
    # Get entries for this page
    entries = query_db(
        """
        SELECT id, topic, slug, title, created
        FROM til
        WHERE topic = ?
        ORDER BY created DESC
        LIMIT ? OFFSET ?
        """,
        [topic, PER_PAGE, offset]
    )
    
    # Get all topics for navigation
    topics = query_db("SELECT DISTINCT topic FROM til ORDER BY topic")
    topics = [t["topic"] for t in topics]
    
    has_next = offset + PER_PAGE < count
    has_prev = page > 1
    
    return render_template(
        "topic.html",
        entries=entries,
        topics=topics,
        current_topic=topic,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        count=count
    )

@app.route("/<topic>/<slug>")
def entry(topic, slug):
    """Show a single entry"""
    entry = query_db(
        """
        SELECT id, topic, slug, title, html, created, updated
        FROM til
        WHERE topic = ? AND slug = ?
        """,
        [topic, slug],
        one=True
    )
    
    if entry is None:
        abort(404)
    
    # Get all topics for navigation
    topics = query_db("SELECT DISTINCT topic FROM til ORDER BY topic")
    topics = [t["topic"] for t in topics]
    
    # Get related entries (same topic, exclude current)
    related = query_db(
        """
        SELECT id, topic, slug, title
        FROM til
        WHERE topic = ? AND slug != ?
        ORDER BY created DESC
        LIMIT 5
        """,
        [topic, slug]
    )
    
    return render_template(
        "entry.html",
        entry=entry,
        topics=topics,
        related=related
    )

@app.route("/search")
def search():
    """Search entries"""
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("index"))
    
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * PER_PAGE
    
    # Get total count for this search
    count = query_db(
        """
        SELECT COUNT(*) as count
        FROM til_fts
        JOIN til ON til_fts.rowid = til.id
        WHERE til_fts MATCH ?
        """,
        [q],
        one=True
    )["count"]
    
    # Get entries for this page
    entries = query_db(
        """
        SELECT til.id, til.topic, til.slug, til.title, til.created,
               snippet(til_fts, -1, '<mark>', '</mark>', '...', 30) as snippet
        FROM til_fts
        JOIN til ON til_fts.rowid = til.id
        WHERE til_fts MATCH ?
        ORDER BY rank
        LIMIT ? OFFSET ?
        """,
        [q, PER_PAGE, offset]
    )
    
    # Get all topics for navigation
    topics = query_db("SELECT DISTINCT topic FROM til ORDER BY topic")
    topics = [t["topic"] for t in topics]
    
    has_next = offset + PER_PAGE < count
    has_prev = page > 1
    
    return render_template(
        "search.html",
        entries=entries,
        topics=topics,
        query=q,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        count=count
    )

@app.route('/feed.atom')
def feed():
    """Generate Atom feed of recent entries"""
    # Get the 20 most recent entries
    entries = query_db(
        """
        SELECT id, topic, slug, title, html, created
        FROM til
        ORDER BY created DESC
        LIMIT 20
        """
    )
    
    fg = FeedGenerator()
    fg.id(request.url_root)
    fg.title('Today I Learned')
    fg.author({'name': 'Your Name', 'email': 'your.email@example.com'})
    fg.link(href=request.url_root, rel='alternate')
    fg.link(href=request.url, rel='self')
    fg.description('A collection of things I learn every day')
    fg.language('en')
    
    for entry in entries:
        # Create full URL for entry
        entry_url = urljoin(
            request.url_root,
            url_for('entry', topic=entry['topic'], slug=entry['slug'])
        )
        
        # Convert created date to datetime object
        created = datetime.strptime(entry['created'], "%Y-%m-%d %H:%M:%S")
        
        # Add entry to feed
        fe = fg.add_entry()
        fe.id(entry_url)
        fe.title(entry['title'])
        fe.link(href=entry_url)
        fe.published(created)
        fe.updated(created)
        fe.content(entry['html'], type='html')
        fe.author(name='Your Name', email='your.email@example.com')
    
    response = app.response_class(
        fg.atom_str(pretty=True),
        mimetype='application/atom+xml'
    )
    return response

@app.route('/stats')
def stats():
    """Show statistics about the blog"""
    # Get topic counts
    topic_stats = query_db(
        """
        SELECT topic, COUNT(*) as count 
        FROM til 
        GROUP BY topic 
        ORDER BY count DESC
        """
    )
    
    # Get total counts
    total_entries = query_db("SELECT COUNT(*) as count FROM til", one=True)["count"]
    
    # Get date range
    date_range = query_db(
        """
        SELECT MIN(created) as first_entry, MAX(created) as last_entry
        FROM til
        """,
        one=True
    )
    
    # Get all topics for navigation
    topics = query_db("SELECT DISTINCT topic FROM til ORDER BY topic")
    topics = [t["topic"] for t in topics]
    
    return render_template(
        "stats.html",
        topics=topics,
        topic_stats=topic_stats,
        total_entries=total_entries,
        date_range=date_range
    )

# Command to rebuild the database
@app.cli.command("build")
def build_command():
    """Build the database."""
    build_database(root)
    print("Database has been built.")

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    # Get all topics for navigation
    topics = query_db("SELECT DISTINCT topic FROM til ORDER BY topic")
    topics = [t["topic"] for t in topics]
    return render_template('404.html', topics=topics), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    # Get all topics for navigation
    topics = query_db("SELECT DISTINCT topic FROM til ORDER BY topic")
    topics = [t["topic"] for t in topics]
    return render_template('500.html', topics=topics), 500

if __name__ == "__main__":
    # If run directly, build database first then run app
    if not os.path.exists(root / DATABASE):
        print("Database not found. Building database...")
        build_database(root)
    app.run(debug=True)