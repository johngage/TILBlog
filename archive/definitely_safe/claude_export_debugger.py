#!/usr/bin/env python3
"""
Debug Claude Export Format
Examines the actual structure of Claude export files
"""

import json
from pathlib import Path
from pprint import pprint

def examine_claude_exports():
    """Examine the structure of Claude export files"""
    claude_exports_dir = Path("claude_exports")
    
    if not claude_exports_dir.exists():
        print("❌ claude_exports directory not found")
        return
    
    export_files = list(claude_exports_dir.glob("*.json"))
    
    if not export_files:
        print("❌ No JSON files found in claude_exports directory")
        return
    
    print(f"🔍 Found {len(export_files)} export files:")
    for f in export_files:
        print(f"  - {f.name}")
    
    print("\n" + "="*50)
    
    for export_file in export_files:
        print(f"\n📄 Examining {export_file.name}")
        print("-" * 30)
        
        try:
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"File size: {export_file.stat().st_size:,} bytes")
            print(f"JSON type: {type(data)}")
            
            if isinstance(data, dict):
                print(f"Top-level keys: {sorted(data.keys())}")
                
                # Examine each top-level key
                for key, value in data.items():
                    print(f"\n  📋 Key: '{key}'")
                    print(f"    Type: {type(value)}")
                    
                    if isinstance(value, list):
                        print(f"    Length: {len(value)}")
                        if value:
                            print(f"    First item type: {type(value[0])}")
                            if isinstance(value[0], dict):
                                print(f"    First item keys: {sorted(value[0].keys())}")
                                
                                # Show sample of first item
                                print(f"    Sample first item:")
                                sample_item = {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                                             for k, v in list(value[0].items())[:5]}
                                pprint(sample_item, width=120, depth=2)
                    
            elif isinstance(data, list):
                print(f"Array length: {len(data)}")
                if data:
                    print(f"First item type: {type(data[0])}")
                    if isinstance(data[0], dict):
                        print(f"First item keys: {sorted(data[0].keys())}")
            
            # Look for conversation-like structures
            conversation_indicators = find_conversation_structures(data)
            if conversation_indicators:
                print(f"\n  🗣️  Possible conversation structures:")
                for path, info in conversation_indicators.items():
                    print(f"    {path}: {info}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {export_file.name}: {e}")
        except Exception as e:
            print(f"❌ Error examining {export_file.name}: {e}")

def find_conversation_structures(data, path=""):
    """Recursively find structures that look like conversations"""
    conversation_indicators = {}
    
    def search_recursive(obj, current_path):
        if isinstance(obj, dict):
            # Look for conversation-like keys
            conv_keys = {'messages', 'chats', 'conversations', 'dialogue', 'exchanges'}
            message_keys = {'role', 'content', 'text', 'message', 'human', 'assistant'}
            
            found_conv_keys = [k for k in obj.keys() if k.lower() in conv_keys]
            found_msg_keys = [k for k in obj.keys() if k.lower() in message_keys]
            
            if found_conv_keys:
                for key in found_conv_keys:
                    value = obj[key]
                    if isinstance(value, list) and value:
                        conversation_indicators[f"{current_path}.{key}"] = f"Array of {len(value)} items"
            
            if found_msg_keys:
                conversation_indicators[current_path] = f"Message-like object with keys: {found_msg_keys}"
            
            # Recurse into nested objects
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    search_recursive(value, f"{current_path}.{key}" if current_path else key)
        
        elif isinstance(obj, list):
            # Check if this looks like a list of messages
            if obj and isinstance(obj[0], dict):
                first_item_keys = set(obj[0].keys())
                message_indicators = {'role', 'content', 'text', 'message'}
                
                if any(key.lower() in message_indicators for key in first_item_keys):
                    conversation_indicators[current_path] = f"Message array with {len(obj)} items"
            
            # Recurse into list items
            for i, item in enumerate(obj[:3]):  # Only check first 3 items
                if isinstance(item, (dict, list)):
                    search_recursive(item, f"{current_path}[{i}]")
    
    search_recursive(data, path)
    return conversation_indicators

def suggest_processing_approach():
    """Suggest how to modify the processing based on findings"""
    print("\n" + "="*50)
    print("💡 SUGGESTED NEXT STEPS:")
    print("-" * 25)
    
    claude_exports_dir = Path("claude_exports")
    export_files = list(claude_exports_dir.glob("*.json"))
    
    for export_file in export_files:
        try:
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"\n📄 For {export_file.name}:")
            
            # Check for common Claude export patterns
            if isinstance(data, dict):
                if 'conversations' in data:
                    print("  ✅ Found 'conversations' key - standard format")
                elif 'chats' in data:
                    print("  ✅ Found 'chats' key - alternative format")
                elif any('message' in k.lower() for k in data.keys()):
                    print("  ⚠️  Found message-like keys - might need custom processing")
                else:
                    print("  ❓ Structure unclear - manual inspection needed")
                    print(f"     Top-level keys: {list(data.keys())}")
            
            elif isinstance(data, list):
                if data and isinstance(data[0], dict):
                    first_keys = data[0].keys()
                    if any(k.lower() in ['role', 'content', 'message'] for k in first_keys):
                        print("  ✅ Looks like a direct message array")
                    else:
                        print("  ❓ Array of objects - might be conversations")
        
        except Exception as e:
            print(f"  ❌ Could not analyze {export_file.name}: {e}")
    
    print(f"\n🔧 RECOMMENDED ACTIONS:")
    print("1. Run the database migration script first:")
    print("   python database_migration.py")
    print("\n2. Based on the export format above, you may need to modify")
    print("   the _extract_conversations() method in claude_integration_starter.py")
    print("\n3. If the export format is unclear, create a minimal test:")
    print("   - Look at the actual JSON structure")
    print("   - Modify the processing logic accordingly")

def create_test_processor():
    """Create a minimal test version of the processor"""
    print(f"\n🧪 Creating test processor...")
    
    test_code = '''#!/usr/bin/env python3
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
'''
    
    with open("test_claude_processor.py", 'w') as f:
        f.write(test_code)
    
    print("Created test_claude_processor.py")
    print("Run it with: python test_claude_processor.py")

def main():
    print("🔍 Claude Export Format Debugger")
    print("=" * 40)
    
    examine_claude_exports()
    suggest_processing_approach()
    create_test_processor()

if __name__ == "__main__":
    main()