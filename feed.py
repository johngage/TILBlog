import os
import pathlib
from datetime import datetime
from flask import url_for, request
# from werkzeug.contrib.atom import AtomFeed
from urllib.parse import urljoin

def get_atom_feed(app, entries):
    """Generate Atom feed from entries"""
    feed = AtomFeed(
        "John Gage: Today I Learned",
        feed_url=request.url,
        url=request.url_root,
        author="Your Name"
    )
    
    for entry in entries:
        # Create full URL for entry
        entry_url = urljoin(
            request.url_root,
            url_for('entry', topic=entry['topic'], slug=entry['slug'])
        )
        
        # Convert created date to datetime object
        created = datetime.strptime(entry['created'], "%Y-%m-%d %H:%M:%S")
        
        # Add entry to feed
        feed.add(
            title=entry['title'],
            content=entry['html'],
            content_type="html",
            author="Your Name",
            url=entry_url,
            updated=created,
            published=created,
            id=entry_url
        )
    
    return feed