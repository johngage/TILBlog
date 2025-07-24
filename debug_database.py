#!/usr/bin/env python3
"""
Enhanced Database Debugging for TILNET
Provides comprehensive database diagnostics and health checks
"""
import sqlite3
import os
import json
from pathlib import Path


def debug_database():
    """Main database debugging function"""
    print("🔍 TILNET Database Diagnostics")
    print("=" * 40)
    
    databases = {
        'til.db': 'TIL Entries Database',
        'conversations.db': 'Claude Conversations Database'
    }
    
    for db_file, description in databases.items():
        print(f"\n📊 {description}")
        print("-" * 30)
        
        if os.path.exists(db_file):
            print(f"✅ {db_file} exists")
            try:
                _analyze_database(db_file)
            except Exception as e:
                print(f"❌ Error analyzing {db_file}: {e}")
        else:
            print(f"❌ {db_file} not found")
            _suggest_creation(db_file)
    
    # Check for related files
    _check_related_files()


def _analyze_database(db_file):
    """Analyze a specific database file"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"   📋 Tables: {tables}")
    
    # Analyze each table
    for table in tables:
        if table.startswith('sqlite_'):  # Skip system tables
            continue
            
        try:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            # Get recent entries (if has common date columns)
            recent_info = ""
            for date_col in ['created_fs', 'created_at', 'date']:
                try:
                    cursor.execute(f"SELECT {date_col} FROM {table} ORDER BY {date_col} DESC LIMIT 1")
                    latest = cursor.fetchone()
                    if latest:
                        recent_info = f", latest: {latest[0][:10]}"
                        break
                except:
                    continue
            
            print(f"     • {table}: {count:,} rows{recent_info}")
            
        except Exception as e:
            print(f"     • {table}: Error reading ({e})")
    
    # Check for FTS tables (full-text search)
    fts_tables = [t for t in tables if '_fts' in t]
    if fts_tables:
        print(f"   🔍 FTS enabled: {fts_tables}")
    
    # Database size
    size = os.path.getsize(db_file)
    print(f"   💾 Size: {size:,} bytes ({size/1024/1024:.1f} MB)")
    
    conn.close()


def _suggest_creation(db_file):
    """Suggest how to create missing database"""
    if db_file == 'til.db':
        print("   💡 To create: python rebuild_database.py")
    elif db_file == 'conversations.db':
        print("   💡 To create: python claude_integration.py")


def _check_related_files():
    """Check for related configuration and data files"""
    print(f"\n🔧 Related Files")
    print("-" * 30)
    
    related_files = {
        'high_value_conversations.json': 'Claude high-value conversations',
        'tilnet_meta_conversation.json': 'TILNET meta-conversation',
        'conversation_priorities.json': 'Conversation priorities',
        'tilnet-datasette-metadata.json': 'Datasette metadata config',
        'datasette-metadata.json': 'Datasette metadata config (alt)',
        'content/': 'Content directory',
        '_site/': 'Generated static site',
        'claude_exports/': 'Claude export data'
    }
    
    for file_path, description in related_files.items():
        path = Path(file_path)
        if path.exists():
            if path.is_file():
                size = path.stat().st_size
                print(f"   ✅ {file_path}: {size:,} bytes")
            else:
                # Directory - count contents
                try:
                    contents = list(path.rglob('*'))
                    files = [f for f in contents if f.is_file()]
                    print(f"   ✅ {file_path}: {len(files)} files")
                except:
                    print(f"   ✅ {file_path}: directory exists")
        else:
            print(f"   ❌ {file_path}: not found")


def check_datasette_setup():
    """Check if Datasette is properly configured"""
    print(f"\n📡 Datasette Configuration")
    print("-" * 30)
    
    # Check for metadata files
    metadata_files = ['tilnet-datasette-metadata.json', 'datasette-metadata.json']
    metadata_found = False
    
    for metadata_file in metadata_files:
        if Path(metadata_file).exists():
            print(f"   ✅ Metadata: {metadata_file}")
            metadata_found = True
            
            # Show a preview of the metadata
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    if 'databases' in metadata:
                        print(f"     • Configured databases: {list(metadata['databases'].keys())}")
                    if 'title' in metadata:
                        print(f"     • Site title: {metadata['title']}")
            except:
                pass
    
    if not metadata_found:
        print("   ❌ No Datasette metadata found")
        print("   💡 Datasette provides web interface for database exploration")
    
    # Check if datasette is installed
    try:
        import subprocess
        result = subprocess.run(['datasette', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Datasette installed: {result.stdout.strip()}")
            print("   🚀 Run: datasette conversations.db til.db")
        else:
            print("   ❌ Datasette not found")
            print("   💡 Install: pip install datasette")
    except:
        print("   ❌ Datasette not installed")
        print("   💡 Install: pip install datasette")


def show_quick_queries():
    """Show some useful quick database queries"""
    print(f"\n🔧 Quick Database Queries")
    print("-" * 30)
    
    queries = [
        ("Recent TIL entries", "til.db", "SELECT title, created_fs FROM entries ORDER BY created_fs DESC LIMIT 5"),
        ("Topic distribution", "til.db", "SELECT topics_raw, COUNT(*) as count FROM entries GROUP BY topics_raw ORDER BY count DESC LIMIT 5"),
        ("Conversation summary", "conversations.db", "SELECT COUNT(*) as total, AVG(length(chat_messages)) as avg_length FROM conversations"),
        ("Recent conversations", "conversations.db", "SELECT name, created_at FROM conversations ORDER BY created_at DESC LIMIT 3")
    ]
    
    for description, db, query in queries:
        print(f"\n   {description}:")
        print(f"   sqlite3 {db} \"{query}\"")


if __name__ == "__main__":
    debug_database()
    check_datasette_setup() 
    show_quick_queries()
    
    print(f"\n✨ Debug complete!")
    print("💡 Pro tip: Use 'datasette conversations.db til.db' for web interface")