#!/usr/bin/env python3
"""Debug database for GitHub workflow"""
import sqlite3
import os

def debug_database():
    db_files = ['til.db', 'conversations.db']
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"✅ {db_file} exists")
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"   Tables: {[t[0] for t in tables]}")
                conn.close()
            except Exception as e:
                print(f"   Error reading {db_file}: {e}")
        else:
            print(f"❌ {db_file} not found")

if __name__ == "__main__":
    debug_database()
