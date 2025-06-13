#!/usr/bin/env python3
"""
Unified Claude Integration for TILNET
Combines database management, TIL entry creation, and advanced processing
"""

import json
import sqlite3
import re
import subprocess
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse


def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")


class UnifiedClaudeIntegration:
    def __init__(self, conversations_db='conversations.db', til_db='til.db', 
                 claude_exports_dir='claude_exports', content_dir='content/claude-conversations'):
        self.conversations_db = Path(conversations_db)
        self.til_db = Path(til_db)
        self.claude_exports_dir = Path(claude_exports_dir)
        self.content_dir = Path(content_dir)
        
        # Processing stats
        self.processed_conversations = 0
        self.created_entries = 0
        
        # Topic detection (simplified from enhanced version)
        self.topic_keywords = {
            'tilnet': ['tilnet', 'til', 'blog', 'static site', 'deployment'],
            'python': ['python', 'django', 'flask', 'sqlite', 'script'],
            'database': ['sql', 'sqlite', 'database', 'query', 'schema'],
            'web-development': ['html', 'css', 'static site', 'github pages'],
            'system-design': ['architecture', 'design', 'system', 'workflow'],
            'automation': ['script', 'deploy', 'build', 'automation'],
            'documentation': ['document', 'guide', 'tutorial', 'how-to']
        }
    
    def run_full_integration(self, force_reprocess=False):
        """Run complete Claude integration workflow"""
        log("🤖 Starting Unified Claude Integration")
        log("=" * 50)
        
        # Step 1: Import latest exports (from production version)
        self._import_latest_exports()
        
        # Step 2: Setup database and FTS (from production version)
        self._setup_database_and_fts()
        
        # Step 3: Extract high-value conversations (from production version)
        self._extract_high_value_conversations()
        
        # Step 4: Create TIL entries (from enhanced version, simplified)
        self._create_til_entries(force_reprocess)
        
        # Step 5: Show final status
        self._show_integration_status()
        
        log(f"✅ Integration complete: {self.created_entries} TIL entries created")
    
    def _import_latest_exports(self):
        """Import latest Claude exports to conversations database"""
        log("📥 Importing Claude exports...")
        
        latest_export = self.claude_exports_dir / "latest" / "conversations.json"
        
        if latest_export.exists():
            log(f"Found latest export: {latest_export}")
            result = subprocess.run([
                "sqlite-utils", "insert", str(self.conversations_db), "conversations",
                str(latest_export), "--pk", "uuid", "--replace"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                log("✅ Successfully imported conversations")
            else:
                log(f"❌ Import failed: {result.stderr}")
        else:
            log("📂 No new exports found, using existing conversations.db")
    
    def _setup_database_and_fts(self):
        """Setup full-text search on conversations database"""
        log("🔍 Setting up full-text search...")
        
        result = subprocess.run([
            "sqlite-utils", "enable-fts", str(self.conversations_db), "conversations",
            "name", "chat_messages", "--create-triggers", "--replace"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            log("✅ FTS search enabled")
        else:
            log(f"❌ FTS setup failed: {result.stderr}")
    
    def _extract_high_value_conversations(self):
        """Extract and save high-value conversations for analysis"""
        log("💎 Extracting high-value conversations...")
        
        # High-value conversation query (from production version)
        cmd = [
            "sqlite-utils", "query", str(self.conversations_db),
            """SELECT 
                 uuid,
                 name, 
                 created_at,
                 substr(chat_messages, 1, 1000) as content_preview,
                 length(chat_messages) as size
               FROM conversations 
               WHERE name LIKE '%TIL%' 
                  OR name LIKE '%implementation%' 
                  OR name LIKE '%TILNET%'
                  OR name LIKE '%deploy%'
                  OR name LIKE '%architecture%'
                  OR chat_messages LIKE '%sqlite-utils%'
                  OR length(chat_messages) > 5000
               ORDER BY length(chat_messages) DESC
               LIMIT 20""",
            "--json-cols"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            conversations = json.loads(result.stdout)
            log(f"Found {len(conversations)} high-value conversations")
            
            # Save for analysis
            with open("high_value_conversations.json", "w") as f:
                json.dump(conversations, f, indent=2)
            
            return conversations
        else:
            log(f"❌ Error extracting conversations: {result.stderr}")
            return []
    
    def _create_til_entries(self, force_reprocess=False):
        """Create TIL entries from high-value conversations"""
        log("📝 Creating TIL entries from conversations...")
        
        # Ensure content directory exists
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Load high-value conversations
        high_value_file = Path("high_value_conversations.json")
        if not high_value_file.exists():
            log("No high-value conversations file found")
            return
        
        with open(high_value_file) as f:
            conversations = json.load(f)
        
        log(f"Processing {len(conversations)} conversations...")
        
        for conv_data in conversations:
            try:
                if self._should_create_til_entry(conv_data, force_reprocess):
                    self._create_single_til_entry(conv_data)
                    self.created_entries += 1
            except Exception as e:
                log(f"❌ Error processing conversation '{conv_data.get('name', 'unknown')}': {e}")
        
        log(f"Created {self.created_entries} TIL entries")
    
    def _should_create_til_entry(self, conv_data: Dict, force_reprocess: bool) -> bool:
        """Check if we should create a TIL entry for this conversation"""
        if force_reprocess:
            return True
        
        # Generate conversation ID
        conv_id = f"claude_{conv_data.get('uuid', 'unknown')}"
        
        # Check if already processed in TIL database
        if self.til_db.exists():
            conn = sqlite3.connect(str(self.til_db))
            existing = conn.execute(
                "SELECT 1 FROM entries WHERE slug LIKE ? LIMIT 1",
                [f"%{conv_id[:12]}%"]  # Partial match on conversation ID
            ).fetchone()
            conn.close()
            
            return existing is None
        
        return True
    
    def _create_single_til_entry(self, conv_data: Dict):
        """Create a single TIL entry from conversation data"""
        # Generate basic info
        title = self._generate_title(conv_data)
        slug = self._generate_slug(title)
        conv_id = f"claude_{conv_data.get('uuid', 'unknown')}"
        topics = self._detect_topics(conv_data)
        created_at = conv_data.get('created_at', datetime.now().isoformat())[:19]
        
        # Create simplified markdown content
        markdown_content = self._create_markdown_content(conv_data, title, topics)
        
        # Save markdown file
        self._save_markdown_file(slug, markdown_content, created_at)
        
        log(f"  📄 Created: {title}")
    
    def _generate_title(self, conv_data: Dict) -> str:
        """Generate title from conversation name"""
        name = conv_data.get('name', '')
        
        if name and len(name.strip()) > 0:
            # Clean up the name
            title = name.strip()
            if not title.startswith('Claude'):
                title = f"Claude: {title}"
            return title
        
        # Fallback
        date_str = conv_data.get('created_at', '')[:10]
        return f"Claude Discussion - {date_str}"
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug"""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = slug.strip('-')
        return slug[:60]  # Reasonable length
    
    def _detect_topics(self, conv_data: Dict) -> List[str]:
        """Detect topics using simple keyword matching"""
        content = (conv_data.get('name', '') + ' ' + 
                  conv_data.get('content_preview', '')).lower()
        
        detected_topics = []
        
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in content for keyword in keywords):
                detected_topics.append(topic)
        
        # Default topics
        if not detected_topics:
            detected_topics = ['claude-chat', 'general']
        
        return detected_topics[:3]  # Limit to 3 topics
    
    def _create_markdown_content(self, conv_data: Dict, title: str, topics: List[str]) -> str:
        """Create markdown content with frontmatter"""
        created_at = conv_data.get('created_at', '')[:10]
        size = conv_data.get('size', 0)
        preview = conv_data.get('content_preview', '')[:500]
        
        # Frontmatter
        frontmatter = f"""---
title: "{title}"
date: {created_at}
topics: {topics}
source: claude-conversation
conversation_id: {conv_data.get('uuid', 'unknown')}
size: {size}
---

"""
        
        # Content
        content = f"""# {title}

**Source:** Claude conversation  
**Date:** {created_at}  
**Size:** {size:,} characters  

## Summary

This entry was automatically generated from a Claude conversation titled "{conv_data.get('name', 'Unknown')}".

## Preview

{preview}...

## Topics

{', '.join(topics)}

## Notes

- This is an automatically generated entry from Claude conversation data
- Full conversation available in conversations.db
- Use Datasette to explore: `datasette conversations.db`

## Related

- [All Claude Conversations](/topic/claude-chat/)
- [TILNET System](/topic/tilnet/)
"""
        
        return frontmatter + content
    
    def _save_markdown_file(self, slug: str, content: str, created_at: str):
        """Save markdown file in date-organized structure"""
        # Create date-based directory
        date_str = created_at[:7]  # YYYY-MM
        date_dir = self.content_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        filename = f"{created_at[:10]}-{slug}.md"
        filepath = date_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _show_integration_status(self):
        """Show final integration status"""
        log("📊 Integration Status:")
        
        # Check conversations database
        if self.conversations_db.exists():
            result = subprocess.run([
                "sqlite-utils", "query", str(self.conversations_db),
                "SELECT COUNT(*) as count FROM conversations"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                log(f"  💬 Total conversations: {data[0]['count']}")
        
        # Check high-value conversations
        if Path("high_value_conversations.json").exists():
            with open("high_value_conversations.json") as f:
                high_value = json.load(f)
                log(f"  💎 High-value conversations: {len(high_value)}")
        
        # Check TIL entries created
        log(f"  📝 TIL entries created: {self.created_entries}")
        
        # Check content directory
        if self.content_dir.exists():
            md_files = list(self.content_dir.glob("**/*.md"))
            log(f"  📄 Markdown files: {len(md_files)}")
        
        log("")
        log("🔍 Next steps:")
        log("  1. Run: python rebuild_database.py  # Update TIL database")
        log("  2. Run: python til_deploy.py       # Deploy updated site")
        log("  3. Explore: datasette conversations.db  # Analyze conversations")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Unified Claude Integration for TILNET')
    parser.add_argument('--force', action='store_true', 
                       help='Force reprocessing of existing conversations')
    parser.add_argument('--conversations-db', default='conversations.db',
                       help='Path to conversations database')
    parser.add_argument('--til-db', default='til.db',
                       help='Path to TIL database')
    parser.add_argument('--exports-dir', default='claude_exports',
                       help='Directory containing Claude exports')
    parser.add_argument('--content-dir', default='content/claude-conversations',
                       help='Directory for generated markdown files')
    
    args = parser.parse_args()
    
    # Create integrator
    integrator = UnifiedClaudeIntegration(
        conversations_db=args.conversations_db,
        til_db=args.til_db,
        claude_exports_dir=args.exports_dir,
        content_dir=args.content_dir
    )
    
    # Run integration
    try:
        integrator.run_full_integration(args.force)
    except KeyboardInterrupt:
        log("Integration interrupted by user")
    except Exception as e:
        log(f"❌ Integration failed: {e}")
        raise


if __name__ == "__main__":
    main()