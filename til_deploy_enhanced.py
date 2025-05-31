#!/usr/bin/env python3
"""
Enhanced TIL Deploy with TILNET Integration
"""
import subprocess
import os
import json
from pathlib import Path

def main():
    print("🚀 Enhanced TIL Deployment with TILNET Integration")
    
    # Step 0: Process Claude conversations if available
    if Path("claude_exports/latest/conversations.json").exists():
        print("🤖 Processing Claude conversations...")
        subprocess.run(["python", "claude_tilnet_integration.py"])
    else:
        print("📂 No new conversation exports found")
    
    # Step 1: Run original TIL deployment
    print("📝 Running TIL static site generation...")
    subprocess.run(["python", "til_static_builder.py"])
    
    # Step 2: Show TILNET status
    print("\n📊 TILNET System Status:")
    try:
        result = subprocess.run([
            "sqlite-utils", "query", "conversations.db",
            "SELECT COUNT(*) as conversations FROM conversations"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"  💬 Total conversations: {data[0]['conversations']}")
        
        # Check for high-value conversations
        if Path("high_value_conversations.json").exists():
            with open("high_value_conversations.json") as f:
                high_value = json.load(f)
                print(f"  💎 High-value conversations: {len(high_value)}")
                
        # Check if TILNET meta-conversation exists
        if Path("tilnet_meta_conversation.json").exists():
            meta_size = Path("tilnet_meta_conversation.json").stat().st_size
            print(f"  🔄 Meta-conversation: {meta_size:,} bytes (recursive knowledge active)")
            
    except Exception as e:
        print(f"  ❌ Error checking TILNET status: {e}")
    
    print("✅ Enhanced deployment complete!")
    print("🌐 Datasette available at: http://localhost:8080")

if __name__ == "__main__":
    main()
