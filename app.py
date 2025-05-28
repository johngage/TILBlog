#!/usr/bin/env python3
"""
TIL Blog Application - Fixed Structure
"""

import os
import sys
import pathlib
import re
import sqlite3
import time
import yaml
from datetime import datetime
from markdown import markdown
from flask import Flask, g, render_template, request, redirect, url_for, abort, Response
from feedgen.feed import FeedGenerator
from urllib.parse import urljoin
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import frontmatter

# Configuration
DATABASE = "til.db"
PER_PAGE = 20

# Setup paths
root = pathlib.Path(__file__).parent.resolve()

# Check if we're running in build mode
is_build_mode = len(sys.argv) > 1 and sys.argv[1] == 'build'

# Flask application
app = Flask(__name__)
app.config.from_object(__name__)

# ===== HELPER FUNCTIONS =====

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

def get_topic_cloud():
    """Get topics with their counts for the topic cloud"""
    return query_db(
        """
        SELECT t.name as topic, COUNT(*) as count
        FROM entry_topics et
        JOIN topics t ON et.topic_id = t.id
        GROUP BY t.name
        ORDER BY t.name ASC
        """
    )

def convert_wikilinks(content):
    """Convert [[Wiki Links]] to HTML links"""
    import os
    # Get base URL from environment (empty for local Flask, /TILBlog for static)
    base_url = os.environ.get('TIL_BASE_URL', '')
    
    def replace_link(match):
        link_text = match.group(1)
        # Convert to slug (lowercase, hyphens for spaces)
        slug = link_text.lower().replace(' ', '-').replace('_', '-')
        # Remove special characters
        slug = re.sub(r'[^\w\-]', '', slug)
        return f'<a href="{base_url}/note/{slug}/" class="wiki-link">{link_text}</a>'
    
    # Pattern for [[Link Text]]
    pattern = r'\[\[([^\]]+)\]\]'
    return re.sub(pattern, replace_link, content)

# File watcher for auto-rebuild
class MarkdownHandler(FileSystemEventHandler):
    def __init__(self, rebuild_callback):
        self.rebuild_callback = rebuild_callback
        self.last_rebuild = 0
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Only rebuild for markdown files
        if not event.src_path.endswith('.md'):
            return
            
        # Prevent rapid successive rebuilds
        now = time.time()
        if now - self.last_rebuild < 2:  # Wait 2 seconds between rebuilds
            return
            
        print(f"Detected change in {event.src_path}, rebuilding database...")
        self.rebuild_callback()
        self.last_rebuild = now

def start_file_watcher():
    """Start watching for markdown file changes"""
    def rebuild_db():
        try:
            build_database(root)
        except Exception as e:
            print(f"Error rebuilding database: {e}")
    
    event_handler = MarkdownHandler(rebuild_db)
    observer = Observer()
    observer.schedule(event_handler, str(root), recursive=True)
    observer.start()
    print("File watcher started - will auto-rebuild on markdown changes")
    return observer

def build_database(root_dir):
    """Build the SQLite database from Markdown files with front matter"""
    print(f"Building database from {root_dir}")
    db_path = root_dir / DATABASE
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Create tables
    conn.execute("DROP TABLE IF EXISTS entries")
    conn.execute("DROP TABLE IF EXISTS topics")
    conn.execute("DROP TABLE IF EXISTS entry_topics")
    conn.execute("DROP TABLE IF EXISTS entry_fts")
    
    # Main entries table
    conn.execute("""
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY,
            slug TEXT UNIQUE,
            title TEXT,
            content TEXT,
            html TEXT,
            created_fs TEXT,
            modified_fs TEXT,
            created_fm TEXT,
            topics_raw TEXT
        )
    """)
    
    # Topics table
    conn.execute("""
        CREATE TABLE topics (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )
    """)
    
    # Many-to-many relationship
    conn.execute("""
        CREATE TABLE entry_topics (
            entry_id INTEGER,
            topic_id INTEGER,
            FOREIGN KEY (entry_id) REFERENCES entries (id),
            FOREIGN KEY (topic_id) REFERENCES topics (id)
        )
    """)
    
    # Full-text search
    conn.execute("""
        CREATE VIRTUAL TABLE entry_fts USING fts5(
            title,
            content,
            topics,
            content=entries,
            content_rowid=id
        )
    """)
    
    print("Created database tables")
    
    content_dir = root_dir / "content"
    if not content_dir.exists():
        print("ERROR: No content directory found!")
        conn.close()
        return
    
    all_files = list(content_dir.glob("**/*.md"))
    print(f"Found {len(all_files)} markdown files in content directory")
    
    # Log which files are being processed
    for filepath in all_files:
        print(f"  Will process: {filepath.relative_to(root_dir)}")
    
    if not all_files:
        print("No markdown files found in content directory!")
        conn.close()
        return
    
    # Process markdown files
    for filepath in all_files:
        try:
            # Parse front matter
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Extract metadata
            front_matter = post.metadata
            content = post.content
            
            # Get title (from front matter or first heading or filename)
            title = front_matter.get('title')
            if not title:
                # Try to extract from first # heading
                lines = content.strip().splitlines()
                for line in lines:
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                if not title:
                    # Use filename as fallback
                    title = filepath.stem.replace('-', ' ').replace('_', ' ').title()
            
            # Generate slug
            slug = front_matter.get('slug')
            if not slug:
                slug = title.lower()
                slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
                slug = re.sub(r'[\s_]+', '-', slug)   # Replace spaces/underscores with hyphens
                slug = slug.strip('-')                # Remove leading/trailing hyphens
            
            print(f"Processing: {filepath.name} -> {slug}")
            
            # Get topics
            topics = front_matter.get('topics', [])
            if isinstance(topics, str):
                topics = [topics]  # Handle single topic as string
            
            # Get dates - fix the bug where both dates were the same
            # Get dates - fix the bug where both dates were the same
            file_stat = filepath.stat()
            # Use creation time for created_fs (on macOS, use st_birthtime if available)
            try:
                created_fs = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stat.st_birthtime))
            except AttributeError:
                # Fallback for non-macOS systems
                created_fs = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stat.st_ctime))

# Use modification time for modified_fs
            modified_fs = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_stat.st_mtime))
            # Check for explicit modified date in front matter
            modified_fm = front_matter.get('modified') or front_matter.get('updated')
            if modified_fm:
               if isinstance(modified_fm, datetime):
                 modified_fs = modified_fm.strftime("%Y-%m-%d %H:%M:%S")
               else:
                 modified_fs = str(modified_fm)
            
            # Front matter date (if provided)
            created_fm = front_matter.get('created') or front_matter.get('date')
            if created_fm:
                if isinstance(created_fm, datetime):
                    created_fm = created_fm.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    created_fm = str(created_fm)
            
            # Convert wiki links before rendering markdown
            content_with_links = convert_wikilinks(content)
            
            # Render HTML
            html = markdown(
                content_with_links,
                extensions=[
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.tables',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.smarty',
                    'markdown.extensions.toc',
                    'markdown.extensions.attr_list',
                    'markdown.extensions.def_list'
                ],
                extension_configs={
                    'markdown.extensions.codehilite': {
                        'use_pygments': True,
                        'css_class': 'highlight'
                    }
                }
            )
            
            # Insert entry
            entry_result = conn.execute(
                """
                INSERT INTO entries (slug, title, content, html, created_fs, modified_fs, created_fm, topics_raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [slug, title, content, html, created_fs, modified_fs, created_fm, ','.join(topics)]
            )
            entry_id = entry_result.lastrowid
            
            # Insert topics and relationships
            for topic in topics:
                topic = topic.strip()
                if topic:
                    # Insert or get topic
                    topic_result = conn.execute(
                        "INSERT OR IGNORE INTO topics (name) VALUES (?)",
                        [topic]
                    )
                    
                    # Get topic ID
                    topic_row = conn.execute(
                        "SELECT id FROM topics WHERE name = ?",
                        [topic]
                    ).fetchone()
                    
                    if topic_row:
                        # Link entry to topic
                        conn.execute(
                            "INSERT INTO entry_topics (entry_id, topic_id) VALUES (?, ?)",
                            [entry_id, topic_row[0]]
                        )
            
            print(f"Inserted: {title} with topics: {topics}")
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            continue
    
    # Populate full-text search
    conn.execute("""
        INSERT INTO entry_fts (rowid, title, content, topics)
        SELECT id, title, content, topics_raw FROM entries
    """)
    
    # Verify contents
    count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    topic_count = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
    
    print(f"Database build completed: {count} entries, {topic_count} topics")
    
    conn.commit()
    conn.close()

def get_all_til_urls():
    """Return all URLs for TIL entries - used for static site generation"""
    # Connect to database
    conn = get_db()
    
    # Get all entries
    entries = conn.execute(
        """
        SELECT 
            id, 
            title,
            slug,
            created_fs,
            created_fm
        FROM entries
        ORDER BY COALESCE(created_fm, created_fs) DESC
        """
    ).fetchall()
    
    # Generate URLs for all entries
    urls = []
    
    # Home page
    urls.append("/")
    
    # Individual entry pages
    for entry in entries:
        urls.append(f"/note/{entry['slug']}")
    
    # Topic pages
    topics = conn.execute("SELECT DISTINCT name FROM topics").fetchall()
    for topic in topics:
        urls.append(f"/topic/{topic['name']}")
    
    # Add any other routes you want to include
    urls.append("/stats")
    urls.append("/feed.atom")
    
    return urls

# ===== FLASK ROUTES =====

@app.route("/")
def index():
    """Home page - show recent entries"""
    page = request.args.get("page", 1, type=int)
    order = request.args.get("order", "desc")
    offset = (page - 1) * PER_PAGE
    
    # Get total count
    count = query_db("SELECT COUNT(*) as count FROM entries", one=True)["count"]
    
    # Determine sort order - use front matter date if available, otherwise file date
    order_clause = "DESC" if order == "desc" else "ASC"
    sort_field = "COALESCE(created_fm, created_fs)"
    
    # Get entries for this page - INCLUDING content, html, topics_raw
    entries = query_db(
    f"""
    SELECT id, slug, title, content, html, topics_raw, 
           {sort_field} as created, modified_fs, created_fs, created_fm
    FROM entries
    ORDER BY {sort_field} {order_clause}
    LIMIT ? OFFSET ?
    """,
    [PER_PAGE, offset]
)
    
    # Process entries to add previews
    processed_entries = []
    for entry in entries:
        entry_dict = dict(entry)  # Convert Row to dict
        
        # Generate preview
        if entry['content'] and entry['content'].strip():
            # Use markdown content
            preview_text = entry['content'].strip()
        elif entry['html']:
            # Strip HTML tags and use that
            preview_text = re.sub(r'<[^>]+>', '', entry['html'])
            preview_text = preview_text.strip()
        else:
            preview_text = ""
        
    # Clean up and truncate
    if preview_text:
        preview_text = ' '.join(preview_text.split())  # Clean whitespace
        if len(preview_text) > 200:  # CHANGED FROM 100 TO 200
          # Try to break at word boundary
          truncated = preview_text[:200]  # CHANGED FROM 100 TO 200
          last_space = truncated.rfind(' ')
          if last_space > 140:  # CHANGED FROM 70 TO 140 (70% of 200)
            preview_text = preview_text[:last_space] + "..."
        else:
            preview_text = truncated + "..."    
        
        entry_dict['preview'] = preview_text

        # Add logic to determine if entry was modified
        created_date = entry['created_fm'] or entry['created_fs']
        modified_date = entry['modified_fs']
        entry_dict['was_modified'] = (modified_date and 
                            modified_date[:10] != created_date[:10])

        processed_entries.append(entry_dict) 
    
    # Get all topics with counts
    topic_cloud = get_topic_cloud()
    
    has_next = offset + PER_PAGE < count
    has_prev = page > 1
    
    return render_template(
        "index.html",
        entries=processed_entries,
        topic_cloud=topic_cloud,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        count=count,
        current_order=order
    )



@app.route("/topic/<topic>")
def topic(topic):
    """Show entries for a specific topic"""
    # Check if topic exists
    topic_exists = query_db("SELECT 1 FROM topics WHERE name = ? LIMIT 1", [topic], one=True)
    if not topic_exists:
        abort(404)
    
    page = request.args.get("page", 1, type=int)
    order = request.args.get("order", "desc")
    offset = (page - 1) * PER_PAGE
    
    # Get total count for this topic
    count = query_db(
        """
        SELECT COUNT(*) as count 
        FROM entries e
        JOIN entry_topics et ON e.id = et.entry_id
        JOIN topics t ON et.topic_id = t.id
        WHERE t.name = ?
        """, 
        [topic], 
        one=True
    )["count"]
    
    # Determine sort order
    order_clause = "DESC" if order == "desc" else "ASC"
    sort_field = "COALESCE(e.created_fm, e.created_fs)"
    
    # Get entries for this page
    entries = query_db(
    f"""
    SELECT e.id, e.slug, e.title, e.content, e.html, e.topics_raw, 
           {sort_field} as created, e.modified_fs, e.created_fs, e.created_fm
    FROM entries e
    JOIN entry_topics et ON e.id = et.entry_id
    JOIN topics t ON et.topic_id = t.id
    WHERE t.name = ?
    ORDER BY {sort_field} {order_clause}
    LIMIT ? OFFSET ?
    """,
    [topic, PER_PAGE, offset]
)
    
    # Process entries to add previews (same logic as index)
    processed_entries = []
    for entry in entries:
        entry_dict = dict(entry)
        
        # Generate preview
        if entry['content'] and entry['content'].strip():
            preview_text = entry['content'].strip()
        elif entry['html']:
            preview_text = re.sub(r'<[^>]+>', '', entry['html'])
            preview_text = preview_text.strip()
        else:
            preview_text = ""
        
        # Clean up and truncate
        if preview_text:
          preview_text = ' '.join(preview_text.split())  # Clean whitespace
          if len(preview_text) > 200:  # CHANGED FROM 100 TO 200
            # Try to break at word boundary
            truncated = preview_text[:200]  # CHANGED FROM 100 TO 200
            last_space = truncated.rfind(' ')
            if last_space > 140:  # CHANGED FROM 70 TO 140 (70% of 200)
              preview_text = preview_text[:last_space] + "..."
            else:
              preview_text = truncated + "..."

        entry_dict['preview'] = preview_text

        # Add logic to determine if entry was modified
        created_date = entry['created_fm'] or entry['created_fs']
        modified_date = entry['modified_fs']
        entry_dict['was_modified'] = (modified_date and 
                            modified_date[:10] != created_date[:10])

        processed_entries.append(entry_dict)
    
    # Get all topics for navigation
    topic_cloud = get_topic_cloud()
    
    has_next = offset + PER_PAGE < count
    has_prev = page > 1
    
    return render_template(
        "topic.html",
        entries=processed_entries,
        topic_cloud=topic_cloud,
        current_topic=topic,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        count=count,
        current_order=order
    )

@app.route("/note/<slug>")
def entry(slug):
    """Show a single entry by slug"""
    entry = query_db(
        """
        SELECT e.id, e.slug, e.title, e.html, 
               COALESCE(e.created_fm, e.created_fs) as created,
               e.topics_raw
        FROM entries e
        WHERE e.slug = ?
        """,
        [slug],
        one=True
    )
    
    if entry is None:
        abort(404)
    
    # Get topics for this entry
    entry_topics = query_db(
        """
        SELECT t.name
        FROM topics t
        JOIN entry_topics et ON t.id = et.topic_id
        WHERE et.entry_id = ?
        ORDER BY t.name
        """,
        [entry['id']]
    )
    
    # Get all topics for navigation
    topic_cloud = get_topic_cloud()
    
    # Get related entries (entries that share topics)
    related = query_db(
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
    )
    
    return render_template(
        "entry.html",
        entry=entry,
        entry_topics=entry_topics,
        topic_cloud=topic_cloud,
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
        FROM entry_fts
        WHERE entry_fts MATCH ?
        """,
        [q],
        one=True
    )["count"]
    
    # Get entries for this page
    entries = query_db(
        """
        SELECT e.id, e.slug, e.title, 
               COALESCE(e.created_fm, e.created_fs) as created,
               snippet(entry_fts, -1, '<mark>', '</mark>', '...', 30) as snippet
        FROM entry_fts
        JOIN entries e ON entry_fts.rowid = e.id
        WHERE entry_fts MATCH ?
        ORDER BY rank
        LIMIT ? OFFSET ?
        """,
        [q, PER_PAGE, offset]
    )
    
    # Get all topics for navigation
    topic_cloud = get_topic_cloud()
    
    has_next = offset + PER_PAGE < count
    has_prev = page > 1
    
    return render_template(
        "search.html",
        entries=entries,
        topic_cloud=topic_cloud,
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
        SELECT id, slug, title, html, 
               COALESCE(created_fm, created_fs) as created
        FROM entries
        ORDER BY COALESCE(created_fm, created_fs) DESC
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
            url_for('entry', slug=entry['slug'])
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
        SELECT t.name as topic, COUNT(*) as count 
        FROM topics t
        JOIN entry_topics et ON t.id = et.topic_id
        GROUP BY t.name 
        ORDER BY count DESC
        """
    )
    
    # Get total counts
    total_entries = query_db("SELECT COUNT(*) as count FROM entries", one=True)["count"]
    
    # Get date range
    date_range = query_db(
        """
        SELECT MIN(COALESCE(created_fm, created_fs)) as first_entry, 
               MAX(COALESCE(created_fm, created_fs)) as last_entry
        FROM entries
        """,
        one=True
    )
    
    # Get all topics for navigation
    topic_cloud = get_topic_cloud()
    
    return render_template(
        "stats.html",
        topic_cloud=topic_cloud,
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
    topic_cloud = get_topic_cloud()
    return render_template('404.html', topic_cloud=topic_cloud), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    topic_cloud = get_topic_cloud()
    return render_template('500.html', topic_cloud=topic_cloud), 500

# ===== MAIN EXECUTION =====

if __name__ == "__main__":
    # This code ONLY runs when executed directly (not on Netlify)
    if len(sys.argv) > 1 and sys.argv[1] == 'freeze':
        from flask_frozen import Freezer
        freezer = Freezer(app)
        freezer.freeze()
        sys.exit(0)
    
    # Start file watcher in a separate thread (for local dev only)
    if not is_build_mode:
        observer = start_file_watcher()
    
    try:
        # If database doesn't exist, build it
        if not os.path.exists(root / DATABASE):
            print("Database not found. Building database...")
            build_database(root)
        
        # Run the app with file watcher (local dev only)
        if not is_build_mode:
            app.run(debug=True, use_reloader=False)  # Disable reloader to avoid conflicts with file watcher
        else:
            print("Running in build mode - static site generator will handle URLs")
    except KeyboardInterrupt:
        if not is_build_mode:
            print("Stopping file watcher...")
            observer.stop()
            observer.join()
else:
    # When imported by Netlify, just ensure database exists
    if not os.path.exists(root / DATABASE):
        print("Database not found. Building database...")
        build_database(root)