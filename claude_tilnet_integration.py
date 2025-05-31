#!/usr/bin/env python3
"""
TILNET-Claude Integration - Production Ready
"""
import subprocess
import sqlite3
import json
from pathlib import Path
from datetime import datetime

def process_conversations_for_tilnet():
    """Process Claude conversations for TILNET knowledge base"""
    
    print("🤖 Processing Claude conversations for TILNET...")
    
    # 1. Check if fresh exports exist
    latest_export = Path("claude_exports/latest/conversations.json")
    if latest_export.exists():
        print("📥 Importing latest conversation export...")
        subprocess.run([
            "sqlite-utils", "insert", "conversations.db", "conversations",
            str(latest_export), "--pk", "uuid", "--replace"
        ])
    else:
        print("📂 No new exports found, using existing conversations.db")
    
    # 2. Ensure FTS is enabled and updated
    print("🔍 Updating full-text search index...")
    subprocess.run([
        "sqlite-utils", "enable-fts", "conversations.db", "conversations",
        "name", "chat_messages", "--create-triggers", "--replace"
    ])
    
    # 3. Extract high-value conversations for TIL entries
    print("💎 Extracting high-value conversations...")
    cmd = [
        "sqlite-utils", "query", "conversations.db",
        """SELECT 
             name, 
             created_at,
             substr(chat_messages, 1, 4000) as content_preview,
             length(chat_messages) as size
           FROM conversations 
           WHERE name LIKE '%TIL%' 
              OR name LIKE '%implementation%' 
              OR name LIKE '%TILNET%'
              OR chat_messages LIKE '%sqlite-utils%'
              OR chat_messages LIKE '%recursive%'
           ORDER BY length(chat_messages) DESC
           LIMIT 10""",
        "--json-cols"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ High-value conversations identified:")
        conversations = json.loads(result.stdout)
        for conv in conversations:
            print(f"  - {conv['name']} ({conv['size']:,} chars)")
        
        # Save for analysis
        with open("high_value_conversations.json", "w") as f:
            json.dump(conversations, f, indent=2)
            
        print(f"💾 Saved {len(conversations)} conversations to high_value_conversations.json")
        
    else:
        print(f"❌ Error extracting conversations: {result.stderr}")
    
    # 4. Test FTS search with proper syntax
    print("\n🔍 Testing FTS search capabilities:")
    search_tests = [
        ('\"sqlite-utils\"', 'SQLite Utils discussions'),
        ('TILNET', 'TILNET conversations'),
        ('implementation', 'Implementation discussions')
    ]
    
    for term, description in search_tests:
        search_cmd = [
            "sqlite-utils", "query", "conversations.db",
            f"SELECT COUNT(*) as count FROM conversations_fts WHERE conversations_fts MATCH '{term}'"
        ]
        search_result = subprocess.run(search_cmd, capture_output=True, text=True)
        if search_result.returncode == 0:
            count_data = json.loads(search_result.stdout)
            print(f"  {description}: {count_data[0]['count']} conversations")
    
    # 5. Show system status
    print("\n📊 TILNET System Status:")
    status_cmd = [
        "sqlite-utils", "query", "conversations.db",
        "SELECT COUNT(*) as total_conversations FROM conversations"
    ]
    status_result = subprocess.run(status_cmd, capture_output=True, text=True)
    
    if status_result.returncode == 0:
        data = json.loads(status_result.stdout)
        print(f"  Total conversations: {data[0]['total_conversations']}")
    
    print("✅ TILNET conversation processing complete!")

if __name__ == "__main__":
    process_conversations_for_tilnet()
