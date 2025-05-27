#!/usr/bin/env python3
"""
TIL Blog Static Site Generator
Matches the Flask app.py exactly - same database queries, processing, and contexts
"""

import os
import sys
import time
import re
import shutil
import sqlite3
import argparse
from pathlib import Path
from urllib.parse import urlencode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
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


class MockRequest:
    """Enhanced mock Flask request object matching Flask app patterns"""
    def __init__(self, endpoint='index', args=None, path='/', method='GET'):
        self.endpoint = endpoint
        self.args = MockArgs(args or {})
        self.path = path
        self.method = method
        self.url = path
        self.url_root = "https://example.com"  # For feed generation


class MockArgs:
    """Mock request.args with get method - matches Flask app usage"""
    def __init__(self, args_dict):
        self._args = args_dict
    
    def get(self, key, default='', type=None):
        """Match Flask's request.args.get() exactly"""
        value = self._args.get(key, default)
        if type and value != default:
            try:
                return type(value)
            except (ValueError, TypeError):
                return default
        return value
    
    def __contains__(self, key):
        return key in self._args
    
    def items(self):
        return self._args.items()


class TILStaticSiteBuilder:
    """Static site builder that exactly matches the Flask app.py behavior"""
    
    def __init__(self, database='til.db', build_dir='_site', templates_dir='templates', 
                 static_dir='static', base_url=''):
        self.database = database
        self.build_dir = Path(build_dir)
        self.templates_dir = Path(templates_dir)
        self.static_dir = Path(static_dir)
        self.base_url = base_url
        self.PER_PAGE = 20  # Match Flask app
        
        # Setup Jinja2 environment with Flask-like behavior
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add Flask-like functions
        self.env.globals['url_for'] = self.url_for
        self.env.globals['request'] = None  # Will be set per template render
        
        # Database connection
        self.conn = None
    
    def connect_database(self):
        """Connect to the TIL database"""
        try:
            self.conn = sqlite3.connect(self.database)
            self.conn.row_factory = sqlite3.Row
            log(f"Connected to database: {self.database}")
        except Exception as e:
            log(f"Error connecting to database: {e}")
            raise
    
    def url_for(self, endpoint, **kwargs):
        """Flask-compatible url_for function that matches app.py routes"""
        # Handle static files
        if endpoint == 'static':
            filename = kwargs.get('filename', '')
            return f"{self.base_url}/static/{filename}"
        
        # Handle main routes - match Flask app exactly
        if endpoint == 'index':
            base_path = f"{self.base_url}/"
            # Handle query parameters for pagination/sorting
            params = []
            for key, value in kwargs.items():
                if key == 'page' and value != 1:
                    params.append(f"page={value}")
                elif key == 'order' and value != 'desc':
                    params.append(f"order={value}")
            if params:
                base_path += "?" + "&".join(params)
            return base_path
            
        elif endpoint == 'topic':
            topic_name = kwargs.get('topic', '')
            base_path = f"{self.base_url}/topic/{topic_name}/" #/
            # Handle pagination for topic pages
            params = []
            for key, value in kwargs.items():
                if key not in ['topic'] and value is not None:
                    if key == 'page' and value != 1:
                        params.append(f"page={value}")
                    elif key == 'order' and value != 'desc':
                        params.append(f"order={value}")
            if params:
                base_path += "?" + "&".join(params)
            return base_path
            
        elif endpoint == 'entry':
            slug = kwargs.get('slug', '')
            return f"{self.base_url}/note/{slug}/" #/
            
        elif endpoint == 'search':
            return f"{self.base_url}/search/" #/
            
        elif endpoint == 'feed':
            return f"{self.base_url}/feed.atom/" #/
            
        elif endpoint == 'stats':
            return f"{self.base_url}/stats/" #/
        
        # Fallback
        return f"{self.base_url}/{endpoint}/" #/
    
    def query_db(self, query, args=(), one=False):
        """Execute a query and return the results - matches Flask app"""
        cur = self.conn.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv
    
    def get_topic_cloud(self):
        """Get topics with their counts - exactly matches Flask app"""
        return self.query_db(
            """
            SELECT t.name as topic, COUNT(*) as count
            FROM entry_topics et
            JOIN topics t ON et.topic_id = t.id
            GROUP BY t.name
            ORDER BY t.name ASC
            """
        )
    
    def process_entries_for_preview(self, entries):
        """Process entries to add previews and modification flags - matches Flask app exactly"""
        processed_entries = []
        for entry in entries:
            entry_dict = dict(entry)  # Convert Row to dict
            
            # Generate preview - EXACT same logic as Flask app
            if entry['content'] and entry['content'].strip():
                preview_text = entry['content'].strip()
            elif entry['html']:
                preview_text = re.sub(r'<[^>]+>', '', entry['html'])
                preview_text = preview_text.strip()
            else:
                preview_text = ""
            
            # Clean up and truncate - EXACT same logic as Flask app
            if preview_text:
                preview_text = ' '.join(preview_text.split())  # Clean whitespace
                if len(preview_text) > 200:  # Flask app uses 200
                    truncated = preview_text[:200]
                    last_space = truncated.rfind(' ')
                    if last_space > 140:  # 70% of 200
                        preview_text = preview_text[:last_space] + "..."
                    else:
                        preview_text = truncated + "..."
            
            entry_dict['preview'] = preview_text
            
            # Add logic to determine if entry was modified - EXACT same logic
            created_date = entry['created_fm'] or entry['created_fs']
            modified_date = entry['modified_fs']
            entry_dict['was_modified'] = (modified_date and 
                                        modified_date[:10] != created_date[:10])
            
            processed_entries.append(entry_dict)
        
        return processed_entries
    
    def clean_build_directory(self):
        """Clean and create build directory"""
        if self.build_dir.exists():
            log(f"Removing existing build directory: {self.build_dir}")
            shutil.rmtree(self.build_dir)
        
        ensure_dir(self.build_dir)
        log(f"Created fresh build directory: {self.build_dir}")
    
    def generate_index_pages(self):
        """Generate index pages with pagination - matches Flask app exactly"""
        log("Generating index pages with pagination")
        
        template = self.env.get_template('index.html')
        
        # Get total count - same query as Flask app
        count = self.query_db("SELECT COUNT(*) as count FROM entries", one=True)["count"]
        
        # Generate pages for both sort orders
        for order in ['desc', 'asc']:
            total_pages = (count + self.PER_PAGE - 1) // self.PER_PAGE
            
            for page in range(1, total_pages + 1):
                offset = (page - 1) * self.PER_PAGE
                
                # EXACT same query as Flask app index route
                order_clause = "DESC" if order == "desc" else "ASC"
                sort_field = "COALESCE(created_fm, created_fs)"
                
                entries = self.query_db(
                    f"""
                    SELECT id, slug, title, content, html, topics_raw, 
                           {sort_field} as created, modified_fs, created_fs, created_fm
                    FROM entries
                    ORDER BY {sort_field} {order_clause}
                    LIMIT ? OFFSET ?
                    """,
                    [self.PER_PAGE, offset]
                )
                
                # Process entries - same as Flask app
                processed_entries = self.process_entries_for_preview(entries)
                
                # Get topic cloud - same as Flask app
                topic_cloud = self.get_topic_cloud()
                
                # Setup mock request - matches Flask app request handling
                args = {}
                if page > 1:
                    args['page'] = str(page)
                if order != 'desc':
                    args['order'] = order
                
                mock_request = MockRequest('index', args)
                self.env.globals['request'] = mock_request
                
                # EXACT same template context as Flask app
                has_next = offset + self.PER_PAGE < count
                has_prev = page > 1
                
                context = {
                    'entries': processed_entries,
                    'topic_cloud': topic_cloud,
                    'page': page,
                    'has_next': has_next,
                    'has_prev': has_prev,
                    'count': count,
                    'current_order': order
                }
                
                # Render template
                html = template.render(**context)
                
                # Determine filename
                if page == 1 and order == 'desc':
                    filename = 'index.html'
                else:
                    # Create subdirectories for clean URLs
                    if page == 1:
                        # /index.html?order=asc -> /order/asc/index.html
                        page_dir = self.build_dir / 'order' / order
                    else:
                        # /index.html?page=2&order=asc -> /page/2/order/asc/index.html
                        page_dir = self.build_dir / 'page' / str(page)
                        if order != 'desc':
                            page_dir = page_dir / 'order' / order
                    
                    ensure_dir(page_dir)
                    filename = page_dir / 'index.html'
                
                # Write file
                if isinstance(filename, str):
                    filepath = self.build_dir / filename
                else:
                    filepath = filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
        
        log(f"Generated index pages with {total_pages} pages for each sort order")
    
    def generate_topic_pages(self):
        """Generate topic pages - matches Flask app topic route exactly"""
        log("Generating topic pages")
        
        # Create topic directory
        topic_dir = self.build_dir / "topic"
        ensure_dir(topic_dir)
        
        # Get all topics
        topics = self.query_db("SELECT DISTINCT name FROM topics")
        
        template = self.env.get_template('topic.html')
        
        for topic_row in topics:
            topic_name = topic_row['name']
            log(f"Generating topic page for: {topic_name}")
            
            # Create directory for this topic
            topic_page_dir = topic_dir / topic_name
            ensure_dir(topic_page_dir)
            
            # EXACT same query as Flask app topic route
            count = self.query_db(
                """
                SELECT COUNT(*) as count 
                FROM entries e
                JOIN entry_topics et ON e.id = et.entry_id
                JOIN topics t ON et.topic_id = t.id
                WHERE t.name = ?
                """, 
                [topic_name], 
                one=True
            )["count"]
            
            # For simplicity, generate first page only (you could add pagination)
            page = 1
            offset = 0
            order = 'desc'
            order_clause = "DESC"
            sort_field = "COALESCE(e.created_fm, e.created_fs)"
            
            # EXACT same query as Flask app topic route
            entries = self.query_db(
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
                [topic_name, self.PER_PAGE, offset]
            )
            
            # Process entries - same as Flask app
            processed_entries = self.process_entries_for_preview(entries)
            
            # Get topic cloud
            topic_cloud = self.get_topic_cloud()
            
            # Setup mock request
            mock_request = MockRequest('topic')
            self.env.globals['request'] = mock_request
            
            # EXACT same template context as Flask app topic route
            has_next = offset + self.PER_PAGE < count
            has_prev = page > 1
            
            context = {
                'entries': processed_entries,
                'topic_cloud': topic_cloud,
                'current_topic': topic_name,
                'page': page,
                'has_next': has_next,
                'has_prev': has_prev,
                'count': count,
                'current_order': order
            }
            
            # Render template
            html = template.render(**context)
            
            # Write topic page
            with open(topic_page_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(html)
        
        log(f"Generated {len(topics)} topic pages")
    
    def generate_entry_pages(self):
        """Generate individual entry pages - matches Flask app entry route exactly"""
        log("Generating individual entry pages")
        
        # Create note directory
        note_dir = self.build_dir / "note"
        ensure_dir(note_dir)
        
        template = self.env.get_template('entry.html')
        
        # Get all entries
        all_entries = self.query_db(
            """
            SELECT slug FROM entries ORDER BY COALESCE(created_fm, created_fs) DESC
            """
        )
        
        for entry_row in all_entries:
            slug = entry_row['slug']
            
            # Create directory for this entry
            entry_dir = note_dir / slug
            ensure_dir(entry_dir)
            
            # EXACT same query as Flask app entry route
            entry = self.query_db(
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
                continue
            
            # Get topics for this entry - EXACT same query as Flask app
            entry_topics = self.query_db(
                """
                SELECT t.name
                FROM topics t
                JOIN entry_topics et ON t.id = et.topic_id
                WHERE et.entry_id = ?
                ORDER BY t.name
                """,
                [entry['id']]
            )
            
            # Get topic cloud
            topic_cloud = self.get_topic_cloud()
            
            # Get related entries - EXACT same query as Flask app
            related = self.query_db(
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
            
            # Setup mock request
            mock_request = MockRequest('entry')
            self.env.globals['request'] = mock_request
            
            # EXACT same template context as Flask app entry route
            context = {
                'entry': entry,
                'entry_topics': entry_topics,
                'topic_cloud': topic_cloud,
                'related': related
            }
            
            # Render template
            html = template.render(**context)
            
            # Write entry page
            with open(entry_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(html)
        
        log(f"Generated {len(all_entries)} entry pages")
    
    def generate_search_page(self):
        """Generate search page - matches Flask app search route"""
        log("Generating search page")
        
        try:
            template = self.env.get_template('search.html')
            
            # Setup mock request for empty search
            mock_request = MockRequest('search', {'q': ''})
            self.env.globals['request'] = mock_request
            
            # Get topic cloud
            topic_cloud = self.get_topic_cloud()
            
            # EXACT same context as Flask app for empty search
            context = {
                'entries': [],
                'topic_cloud': topic_cloud,
                'query': '',
                'page': 1,
                'has_next': False,
                'has_prev': False,
                'count': 0
            }
            
            html = template.render(**context)
            
            with open(self.build_dir / 'search.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            log("Generated search page")
        except Exception as e:
            log(f"Error generating search page: {e}")
    
    def generate_stats_page(self):
        """Generate stats page - matches Flask app stats route exactly"""
        log("Generating stats page")
        
        try:
            template = self.env.get_template('stats.html')
            
            # EXACT same queries as Flask app stats route
            topic_stats = self.query_db(
                """
                SELECT t.name as topic, COUNT(*) as count 
                FROM topics t
                JOIN entry_topics et ON t.id = et.topic_id
                GROUP BY t.name 
                ORDER BY count DESC
                """
            )
            
            total_entries = self.query_db("SELECT COUNT(*) as count FROM entries", one=True)["count"]
            
            date_range = self.query_db(
                """
                SELECT MIN(COALESCE(created_fm, created_fs)) as first_entry, 
                       MAX(COALESCE(created_fm, created_fs)) as last_entry
                FROM entries
                """,
                one=True
            )
            
            topic_cloud = self.get_topic_cloud()
            
            # Setup mock request
            mock_request = MockRequest('stats')
            self.env.globals['request'] = mock_request
            
            # EXACT same template context as Flask app stats route
            context = {
                'topic_cloud': topic_cloud,
                'topic_stats': topic_stats,
                'total_entries': total_entries,
                'date_range': date_range
            }
            
            html = template.render(**context)
            
            with open(self.build_dir / 'stats.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            log("Generated stats page")
        except Exception as e:
            log(f"Error generating stats page: {e}")
    
    def generate_feed(self):
        """Generate Atom feed - matches Flask app feed route patterns"""
        log("Generating Atom feed")
        
        try:
            # Try to find feed template
            for template_name in ['feed.atom', 'feed.xml', 'atom.xml']:
                try:
                    template = self.env.get_template(template_name)
                    break
                except:
                    continue
            else:
                log("No feed template found, skipping feed generation")
                return
            
            # EXACT same query as Flask app feed route
            entries = self.query_db(
                """
                SELECT id, slug, title, html, 
                       COALESCE(created_fm, created_fs) as created
                FROM entries
                ORDER BY COALESCE(created_fm, created_fs) DESC
                LIMIT 20
                """
            )
            
            # Setup mock request
            mock_request = MockRequest('feed')
            mock_request.url_root = "https://example.com"
            self.env.globals['request'] = mock_request
            
            # Template context for feed
            context = {
                'entries': entries,
                'request': mock_request
            }
            
            feed_content = template.render(**context)
            
            with open(self.build_dir / 'feed.atom', 'w', encoding='utf-8') as f:
                f.write(feed_content)
            
            log("Generated Atom feed")
        except Exception as e:
            log(f"Error generating feed: {e}")
    
    def copy_static_files(self):
        """Copy static files to the build directory"""
        if self.static_dir.exists():
            static_target = self.build_dir / "static"
            if static_target.exists():
                shutil.rmtree(static_target)
            
            shutil.copytree(self.static_dir, static_target)
            log(f"Copied static files to {static_target}")
        else:
            log("No static directory found")
    
    def build(self):
        """Build the complete static site"""
        log("Starting TIL static site generation")
        
        # Connect to database
        self.connect_database()
        
        # Verify database has data
        entry_count = self.query_db("SELECT COUNT(*) as count FROM entries", one=True)["count"]
        if entry_count == 0:
            log("ERROR: No entries found in database!")
            return
        
        log(f"Found {entry_count} entries in database")
        
        # Clean build directory
        self.clean_build_directory()
        
        # Generate all pages - matching Flask app routes
        self.generate_index_pages()
        self.generate_topic_pages()
        self.generate_entry_pages()
        self.generate_search_page()
        self.generate_stats_page()
        self.generate_feed()
        
        # Copy static files
        self.copy_static_files()
        
        # Create .nojekyll file for GitHub Pages
        with open(self.build_dir / ".nojekyll", "w") as f:
            f.write("")
        log("Created .nojekyll file for GitHub Pages")
        
        log("Template-based static site generation finished!")
        log(f"Deploy the {self.build_dir} directory to your hosting provider.")
        
        # Close database connection
        if self.conn:
            self.conn.close()


def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(description='TIL Static Site Generator')
    parser.add_argument('--database', '-d', default='til.db', 
                       help='SQLite database file (default: til.db)')
    parser.add_argument('--build-dir', '-b', default='_site', 
                       help='Build output directory (default: _site)')
    parser.add_argument('--templates', '-t', default='templates', 
                       help='Templates directory (default: templates)')
    parser.add_argument('--static', '-s', default='static', 
                       help='Static files directory (default: static)')
    parser.add_argument('--base-url', '-u', default='', 
                       help='Base URL for generated links (default: empty for root)')
    
    args = parser.parse_args()
    
    # Check if database exists
    if not Path(args.database).exists():
        log(f"Error: Database file '{args.database}' not found")
        log("Run your Flask app first to build the database, or use 'flask build' command")
        sys.exit(1)
    
    # Check if templates directory exists
    if not Path(args.templates).exists():
        log(f"Error: Templates directory '{args.templates}' not found")
        sys.exit(1)
    
    # Build the site
    builder = TILStaticSiteBuilder(
        database=args.database,
        build_dir=args.build_dir,
        templates_dir=args.templates,
        static_dir=args.static,
        base_url=args.base_url
    )
    
    try:
        builder.build()
        return 0
    except Exception as e:
        log(f"Error building site: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())