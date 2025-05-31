#!/usr/bin/env python3
"""
Test Claude Export Processor
Minimal version to test with your specific export format
"""

import json
from pathlib import Path

def test_claude_processing():
    """Test processing with actual export format"""
    claude_exports_dir = Path("claude_exports")
    
    for export_file in claude_exports_dir.glob("*.json"):
        print(f"Testing {export_file.name}...")
        
        with open(export_file, 'r') as f:
            data = json.load(f)
        
        # TODO: Modify this based on your actual export format
        conversations = extract_conversations_from_export(data)
        
        print(f"Found {len(conversations)} conversations")
        
        for i, conv in enumerate(conversations[:3]):  # Show first 3
            print(f"  Conversation {i+1}:")
            print(f"    Keys: {list(conv.keys())}")
            if 'messages' in conv:
                print(f"    Messages: {len(conv['messages'])}")

def extract_conversations_from_export(data):
    """Extract conversations - MODIFY THIS based on debug output above"""
    
    # Pattern 1: Standard format with 'conversations' key
    if isinstance(data, dict) and 'conversations' in data:
        return data['conversations']
    
    # Pattern 2: Alternative format with 'chats' key  
    elif isinstance(data, dict) and 'chats' in data:
        return data['chats']
    
    # Pattern 3: Direct array of conversations
    elif isinstance(data, list):
        return data
    
    # Pattern 4: Single conversation object
    elif isinstance(data, dict) and 'messages' in data:
        return [data]
    
    # Add more patterns based on your debug output
    else:
        print(f"Unknown format. Top-level keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        return []

if __name__ == "__main__":
    test_claude_processing()
