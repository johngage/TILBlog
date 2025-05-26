#!/usr/bin/env python3
"""
Claude Chat Integration Starter
Quick way to get Claude conversations into your TIL system
"""

import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import frontmatter

class ClaudeIntegrationStarter:
    def __init__(self, db_path: Path, claude_exports_dir: Path):
        self.db_path = db_path
        self.claude_exports_dir = claude_exports_dir
        self.processed_conversations = 0
        
    def quick_start_integration(self):
        """Quick integration of Claude exports"""
        print("🤖 Starting Claude chat integration...")
        
        # Step 1: Process official Claude exports
        export_files = list(self.claude_exports_dir.glob("*.json"))
        
        if not export_files:
            print("📥 No Claude export files found.")
            print("To get started:")
            print("1. Go to Claude Settings → Privacy → Export Data")
            print("2. Download the export when ready")
            print("3. Place JSON files in claude_exports/ folder")
            return
        
        print(f"Found {len(export_files)} export files")
        
        # Process each export file
        for export_file in export_files:
            try:
                self.process_claude_export(export_file)
            except Exception as e:
                print(f"❌ Error processing {export_file}: {e}")
        
        print(f"✅ Processed {self.processed_conversations} conversations")
        
        # Generate documentation from significant conversations
        self.generate_documentation_entries()
    
    def process_claude_export(self, export_file: Path):
        """Process a single Claude export JSON file"""
        print(f"📄 Processing {export_file.name}...")
        
        with open(export_file, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        # Handle different export formats
        conversations = self._extract_conversations(export_data)
        
        for conv_data in conversations:
            if self._is_documentation_worthy(conv_data):
                self._create_conversation_entry(conv_data)
                self.processed_conversations += 1
    
    def _extract_conversations(self, export_data: Dict) -> List[Dict]:
        """Extract conversations from different export formats"""
        # Handle different possible JSON structures
        if 'conversations' in export_data:
            return export_data['conversations']
        elif 'chats' in export_data:
            return export_data['chats']
        elif isinstance(export_data, list):
            return export_data
        else:
            # Single conversation
            return [export_data]
    
    def _is_documentation_worthy(self, conv_data: Dict) -> bool:
        """Determine if conversation should become a TIL entry"""
        # Look for conversations that would make good documentation
        
        messages = conv_data.get('messages', [])
        if len(messages) < 4:  # Too short to be useful
            return False
            
        content = ' '.join([msg.get('content', '') for msg in messages])
        
        # Documentation indicators
        doc_indicators = [
            'how to',
            'architecture',
            'implementation',
            'database',
            'system',
            'design',
            'workflow',
            'process',
            'tutorial',
            'guide',
            'setup',
            'configuration'
        ]
        
        # Technical indicators
        technical_indicators = [
            '```',  # Code blocks
            'sql',
            'python',
            'javascript',
            'error',
            'debug',
            'function',
            'class',
            'import'
        ]
        
        # Check for documentation keywords
        doc_score = sum(1 for indicator in doc_indicators 
                       if indicator.lower() in content.lower())
        
        # Check for technical content
        tech_score = sum(1 for indicator in technical_indicators 
                        if indicator.lower() in content.lower())
        
        # Include if it has documentation value or significant technical content
        return doc_score >= 2 or tech_score >= 3 or len(content) > 2000
    
    def _create_conversation_entry(self, conv_data: Dict):
        """Create a TIL entry from a conversation"""
        title = self._generate_title(conv_data)
        slug = self._generate_slug(title)
        
        # Extract key information
        messages = conv_data.get('messages', [])
        created_at = conv_data.get('created_at', datetime.now().isoformat())
        
        # Generate markdown content
        markdown_content = self._format_conversation_as_til(conv_data)
        
        # Detect topics automatically
        topics = self._detect_topics(conv_data)
        
        # Save to database
        self._save_conversation_entry({
            'slug': slug,
            'title': title,
            'content': markdown_content,
            'content_type': 'conversation',
            'source_type': 'claude_export',
            'conversation_id': conv_data.get('id', str(hash(str(conv_data)))),
            'message_count': len(messages),
            'created_fm': created_at,
            'topics': topics
        })
        
        print(f"  📝 Created TIL entry: {title}")
    
    def _generate_title(self, conv_data: Dict) -> str:
        """Generate a meaningful title for the conversation"""
        # Try to get title from conversation data
        if 'title' in conv_data and conv_data['title']:
            return f"Learning: {conv_data['title']}"
        
        # Generate from first few messages
        messages = conv_data.get('messages', [])
        if messages:
            first_message = messages[0].get('content', '')
            
            # Extract meaningful parts
            sentences = first_message.split('.')[:2]  # First two sentences
            title_text = '. '.join(sentences).strip()
            
            # Clean up and truncate
            title_text = re.sub(r'\s+', ' ', title_text)
            if len(title_text) > 60:
                title_text = title_text[:60] + "..."
            
            return f"Claude Discussion: {title_text}"
        
        return f"Claude Conversation - {datetime.now().strftime('%Y-%m-%d')}"
    
    def _format_conversation_as_til(self, conv_data: Dict) -> str:
        """Format conversation as a TIL markdown entry"""
        messages = conv_data.get('messages', [])
        created_at = conv_data.get('created_at', '')
        
        markdown_lines = [
            f"# Learning from Claude Discussion",
            f"",
            f"**Date:** {created_at[:10] if created_at else 'Unknown'}",
            f"**Messages:** {len(messages)}",
            f"",
        ]
        
        # Add summary section
        summary = self._generate_summary(messages)
        if summary:
            markdown_lines.extend([
                "## Key Insights",
                "",
                summary,
                ""
            ])
        
        # Add conversation details
        markdown_lines.extend([
            "## Conversation Details",
            ""
        ])
        
        # Format key messages (not all, to keep it readable)
        key_messages = self._extract_key_messages(messages)
        
        for i, msg in enumerate(key_messages):
            role = "**Human:**" if msg.get('role') == 'human' else "**Claude:**"
            content = msg.get('content', '')
            
            # Clean up content
            content = self._clean_message_content(content)
            
            markdown_lines.extend([
                f"### Exchange {i+1}",
                "",
                f"{role}",
                f"{content}",
                ""
            ])
        
        # Add tags and references
        markdown_lines.extend([
            "## Related Topics",
            "",
            "- Add relevant topic tags",
            "- Link to related TIL entries",
            ""
        ])
        
        return '\n'.join(markdown_lines)
    
    def _extract_key_messages(self, messages: List[Dict]) -> List[Dict]:
        """Extract the most important messages from conversation"""
        if len(messages) <= 6:
            return messages
        
        # Take first 2, last 2, and 2 from middle with most content
        key_messages = []
        
        # First 2 messages
        key_messages.extend(messages[:2])
        
        # Middle messages with most content
        middle_messages = messages[2:-2]
        if middle_messages:
            # Sort by content length and take top 2
            middle_sorted = sorted(middle_messages, 
                                 key=lambda x: len(x.get('content', '')), 
                                 reverse=True)
            key_messages.extend(middle_sorted[:2])
        
        # Last 2 messages
        key_messages.extend(messages[-2:])
        
        return key_messages
    
    def _clean_message_content(self, content: str) -> str:
        """Clean and format message content"""
        # Truncate very long messages
        if len(content) > 1000:
            content = content[:1000] + "\n\n*[Message truncated for readability]*"
        
        # Fix formatting issues
        content = re.sub(r'\n{3,}', '\n\n', content)  # Reduce excessive newlines
        
        return content.strip()
    
    def _generate_summary(self, messages: List[Dict]) -> str:
        """Generate a summary of the conversation"""
        # Simple keyword-based summary
        all_content = ' '.join([msg.get('content', '') for msg in messages])
        
        # Extract key topics mentioned
        topics = self._extract_key_phrases(all_content)
        
        if topics:
            return f"This conversation covered: {', '.join(topics[:5])}"
        
        return ""
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text"""
        # Simple approach - look for common technical terms
        technical_terms = [
            'database', 'SQL', 'Python', 'JavaScript', 'API', 'function',
            'system', 'architecture', 'design', 'implementation', 'error',
            'debug', 'performance', 'optimization', 'security', 'authentication',
            'frontend', 'backend', 'framework', 'library', 'algorithm'
        ]
        
        found_terms = []
        text_lower = text.lower()
        
        for term in technical_terms:
            if term.lower() in text_lower:
                found_terms.append(term)
        
        return found_terms[:10]  # Limit to top 10
    
    def _detect_topics(self, conv_data: Dict) -> List[str]:
        """Auto-detect topics for the conversation"""
        messages = conv_data.get('messages', [])
        content = ' '.join([msg.get('content', '') for msg in messages])
        
        # Topic mapping based on keywords
        topic_keywords = {
            'python': ['python', 'django', 'flask', 'pandas'],
            'database': ['sql', 'sqlite', 'database', 'query'],
            'web-development': ['html', 'css', 'javascript', 'react'],
            'system-design': ['architecture', 'design', 'system'],
            'debugging': ['error', 'debug', 'fix', 'problem'],
            'data-analysis': ['data', 'analysis', 'visualization'],
            'documentation': ['document', 'guide', 'tutorial', 'how-to']
        }
        
        detected_topics = []
        content_lower = content.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_topics.append(topic)
        
        return detected_topics if detected_topics else ['general', 'claude-chat']
    
    def _save_conversation_entry(self, entry_data: Dict):
        """Save conversation entry to database"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Insert main entry
            conn.execute("""
                INSERT OR REPLACE INTO entries (
                    slug, title, content, content_type, source_type,
                    conversation_id, message_count, created_fm, topics_raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                entry_data['slug'], entry_data['title'], entry_data['content'],
                entry_data['content_type'], entry_data['source_type'],
                entry_data['conversation_id'], entry_data['message_count'],
                entry_data['created_fm'], ','.join(entry_data['topics'])
            ])
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug"""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        return slug.strip('-')[:50]  # Limit length
    
    def generate_documentation_entries(self):
        """Generate special documentation entries from Claude conversations"""
        print("📚 Generating documentation entries...")
        
        # This could analyze all processed conversations and create
        # high-level documentation entries like:
        # - "TIL System Architecture (from Claude discussions)"
        # - "Database Design Decisions (from Claude conversations)"
        # - "Implementation Patterns (from Claude discussions)"
        
        # For now, create a master index entry
        self._create_documentation_index()
    
    def _create_documentation_index(self):
        """Create an index of all Claude-generated documentation"""
        title = "Documentation from Claude Conversations"
        
        markdown_content = f"""# {title}

This entry serves as an index of all documentation and insights derived from Claude conversations.

## Overview

Claude conversations have been processed and converted into TIL entries to capture:

- System architecture discussions
- Implementation decisions and rationale  
- Debugging sessions and solutions
- Design patterns and best practices
- Technical explanations and tutorials

## How to Use This Documentation

1. **Search by topic** - Use the search function to find specific technical topics
2. **Browse by date** - See how understanding evolved over time
3. **Follow conversation threads** - Related discussions are linked together

## Integration Benefits

By integrating Claude conversations into the TIL system, we gain:

- **Searchable knowledge base** of all technical discussions
- **Documentation of decision-making process** 
- **Reusable explanations** for complex concepts
- **Learning pattern analysis** through Datasette

## Next Steps

- Set up automated Claude export processing
- Implement conversation-to-TIL automation
- Add conversation relationship mapping
- Create learning analytics dashboard

*This documentation system is self-improving - as more conversations are processed, the knowledge base becomes more comprehensive and valuable.*
""".strip()

        entry_data = {
            'slug': 'claude-conversations-documentation-index',
            'title': title,
            'content': markdown_content,
            'content_type': 'documentation',
            'source_type': 'claude_integration',
            'conversation_id': 'meta-documentation',
            'message_count': 0,
            'created_fm': datetime.now().isoformat(),
            'topics': ['documentation', 'claude-integration', 'system-overview']
        }
        
        self._save_conversation_entry(entry_data)
        print(f"  📋 Created documentation index")

# Quick start script
def main():
    # Setup directories
    claude_exports_dir = Path("claude_exports")
    claude_exports_dir.mkdir(exist_ok=True)
    
    db_path = Path("til.db")
    
    # Run the integration
    integrator = ClaudeIntegrationStarter(db_path, claude_exports_dir)
    integrator.quick_start_integration()

if __name__ == "__main__":
    main()