#!/usr/bin/env python3
"""
Database Migration for Claude Integration
Adds new columns to existing TIL database schema
"""

import sqlite3
import sys
import time
import shutil
from pathlib import Path

def migrate_database(db_path):
    """Add new columns to support Claude integration"""
    print(f"🔧 Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    
    try:
        # Check current schema
        cursor = conn.execute("PRAGMA table_info(entries)")
        current_columns = {row[1] for row in cursor.fetchall()}
        print(f"Current columns: {sorted(current_columns)}")
        
        # Add new columns if they don't exist
        new_columns = [
            ("content_type", "TEXT DEFAULT 'til'"),
            ("source_type", "TEXT DEFAULT 'manual'"),
            ("conversation_id", "TEXT"),
            ("message_count", "INTEGER"),
            ("has_excalidraw", "BOOLEAN DEFAULT 0"),
            ("excalidraw_data", "TEXT"),
            ("svg_content", "TEXT"),
            ("excalidraw_elements_count", "INTEGER"),
            ("word_count", "INTEGER"),
            ("tags", "TEXT"),
            ("file_path", "TEXT"),
            ("checksum", "TEXT"),
            ("last_processed", "TEXT")
        ]
        
        for column_name, column_def in new_columns:
            if column_name not in current_columns:
                try:
                    conn.execute(f"ALTER TABLE entries ADD COLUMN {column_name} {column_def}")
                    print(f"  ✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    print(f"  ⚠️  Could not add {column_name}: {e}")
        
        # Create new tables if they don't exist
        
        # Claude conversations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claude_conversations (
                id INTEGER PRIMARY KEY,
                claude_id TEXT UNIQUE,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                message_count INTEGER,
                total_characters INTEGER,
                primary_topics TEXT,
                conversation_type TEXT,
                learning_value_score REAL,
                contains_code BOOLEAN,
                contains_math BOOLEAN,
                processed_to_til BOOLEAN DEFAULT 0,
                til_entry_id INTEGER,
                summary TEXT,
                FOREIGN KEY (til_entry_id) REFERENCES entries (id)
            )
        """)
        print("  ✅ Created claude_conversations table")
        
        # Claude messages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claude_messages (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                message_index INTEGER,
                has_code_blocks BOOLEAN,
                has_math BOOLEAN,
                word_count INTEGER,
                FOREIGN KEY (conversation_id) REFERENCES claude_conversations (id)
            )
        """)
        print("  ✅ Created claude_messages table")
        
        # Excalidraw drawings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS excalidraw_drawings (
                id INTEGER PRIMARY KEY,
                entry_id INTEGER,
                elements_count INTEGER,
                text_elements_count INTEGER,
                shape_elements_count INTEGER,
                arrow_elements_count INTEGER,
                all_text_content TEXT,
                shape_types TEXT,
                canvas_width REAL,
                canvas_height REAL,
                background_color TEXT,
                theme TEXT,
                references_files TEXT,
                embedded_images_count INTEGER,
                FOREIGN KEY (entry_id) REFERENCES entries (id)
            )
        """)
        print("  ✅ Created excalidraw_drawings table")
        
        # Update existing entries to have default content_type
        conn.execute("UPDATE entries SET content_type = 'til' WHERE content_type IS NULL")
        conn.execute("UPDATE entries SET source_type = 'manual' WHERE source_type IS NULL")
        
        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_entries_content_type ON entries(content_type)",
            "CREATE INDEX IF NOT EXISTS idx_entries_source_type ON entries(source_type)",
            "CREATE INDEX IF NOT EXISTS idx_claude_conversations_created ON claude_conversations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_claude_messages_conversation ON claude_messages(conversation_id)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        print("  ✅ Created performance indexes")
        
        conn.commit()
        print("🎉 Database migration completed successfully!")
        
        # Show updated schema
        cursor = conn.execute("PRAGMA table_info(entries)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns: {sorted(updated_columns)}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

def verify_migration(db_path):
    """Verify the migration worked correctly"""
    print(f"🔍 Verifying migration...")
    
    conn = sqlite3.connect(db_path)
    
    try:
        # Check that new columns exist
        cursor = conn.execute("PRAGMA table_info(entries)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required_columns = {
            'content_type', 'source_type', 'conversation_id', 
            'message_count', 'has_excalidraw'
        }
        
        missing_columns = required_columns - columns
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        
        # Check that new tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        required_tables = {
            'entries', 'topics', 'entry_topics', 
            'claude_conversations', 'claude_messages', 'excalidraw_drawings'
        }
        
        missing_tables = required_tables - tables
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        print("✅ Migration verification passed!")
        return True
        
    finally:
        conn.close()

def main():
    db_path = Path("til.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Run rebuild_database.py first to create the initial database")
        sys.exit(1)
    
    # Backup the database first
    backup_path = Path(f"til_backup_{int(time.time())}.db")
    
    shutil.copy2(db_path, backup_path)
    print(f"📦 Created backup: {backup_path}")
    
    try:
        migrate_database(db_path)
        
        if verify_migration(db_path):
            print("\n🎉 Database successfully migrated!")
            print("You can now run the Claude integration script.")
        else:
            print("\n❌ Migration verification failed!")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"You can restore from backup: {backup_path}")

if __name__ == "__main__":
    main()