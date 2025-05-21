"""
Unit tests for TIL Blog application
"""
import os
import tempfile
import pytest
from pathlib import Path
import shutil
import sqlite3

# Import your Flask app 
from app import app, get_db, build_database, root, DATABASE

@pytest.fixture
def client():
    """Create a test client for the app."""
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    test_root = Path(test_dir)
    
    # Save the original values
    original_root = root
    original_database = DATABASE
    
    # Override the root and database path for testing
    app.config['root'] = test_root
    app.config['DATABASE'] = 'test_til.db'
    
    # Create a test database with sample entries
    test_db_path = test_root / app.config['DATABASE']
    
    # Initialize test database
    conn = sqlite3.connect(test_db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            title TEXT,
            path TEXT,
            content TEXT,
            created TEXT,
            updated TEXT,
            topic TEXT
        )
    ''')
    
    # Add some test entries
    conn.execute('''
        INSERT INTO entries (id, title, path, content, created, updated, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        'test-entry-1',
        'Test Entry 1',
        'test/entry1.md',
        '# Test Entry 1\n\nThis is a test entry.',
        '2023-01-01T12:00:00',
        '2023-01-01T12:00:00',
        'testing'
    ))
    conn.execute('''
        INSERT INTO entries (id, title, path, content, created, updated, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        'test-entry-2',
        'Test Entry 2',
        'test/entry2.md',
        '# Test Entry 2\n\nThis is another test entry.',
        '2023-01-02T12:00:00',
        '2023-01-02T12:00:00',
        'python'
    ))
    conn.commit()
    conn.close()
    
    # Create a test client using the Flask application
    with app.test_client() as client:
        with app.app_context():
            yield client
    
    # Clean up - restore original values and remove temp directory
    app.config['root'] = original_root
    app.config['DATABASE'] = original_database
    shutil.rmtree(test_dir)


def test_homepage(client):
    """Test that the homepage loads and contains expected elements."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    
    # Check for basic elements
    assert '<title>' in html
    assert 'Today I Learned' in html
    
    # Check for entries
    assert 'Test Entry 1' in html
    assert 'Test Entry 2' in html


def test_entry_page(client):
    """Test that individual TIL pages load correctly."""
    response = client.get('/til/test-entry-1')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    
    # Check content
    assert 'Test Entry 1' in html
    assert 'This is a test entry' in html
    assert 'testing' in html  # Topic should be displayed


def test_topic_page(client):
    """Test that topic pages load correctly."""
    response = client.get('/topic/testing')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    
    # Check for entries in this topic
    assert 'Test Entry 1' in html
    assert 'testing' in html


def test_atom_feed(client):
    """Test that the Atom feed works."""
    response = client.get('/feed.xml')
    assert response.status_code == 200
    assert response.mimetype == 'application/atom+xml'
    
    # Basic check of XML content
    xml = response.data.decode('utf-8')
    assert '<?xml' in xml
    assert '<entry>' in xml
    assert 'Test Entry' in xml


def test_nonexistent_entry(client):
    """Test that requesting a nonexistent entry returns 404."""
    response = client.get('/til/does-not-exist')
    assert response.status_code == 404


def test_search_functionality(client):
    """Test search functionality if your app has it."""
    response = client.get('/search?q=test')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    
    # Search results should include our test entries
    assert 'Test Entry 1' in html
    assert 'Test Entry 2' in html


def test_get_all_til_urls():
    """Test the function that generates URLs for the static site builder."""
    # This assumes you've added the get_all_til_urls function to your app
    from app import get_all_til_urls
    
    # Mock the database connection
    conn = sqlite3.connect(':memory:')
    conn.execute('''
        CREATE TABLE entries (
            id TEXT PRIMARY KEY,
            title TEXT,
            path TEXT,
            content TEXT,
            created TEXT,
            updated TEXT,
            topic TEXT
        )
    ''')
    conn.execute('INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('test-1', 'Test 1', 'path/to/test.md', 'content', '2023-01-01', '2023-01-01', 'python'))
    conn.commit()
    
    # Mock the get_db function to return our test connection
    import app as app_module
    original_get_db = app_module.get_db
    app_module.get_db = lambda: conn
    
    try:
        urls = get_all_til_urls()
        
        # Check that essential URLs are included
        assert '/' in urls
        assert '/til/test-1' in urls
        assert '/topic/python' in urls
        
    finally:
        # Restore the original function
        app_module.get_db = original_get_db
        conn.close()