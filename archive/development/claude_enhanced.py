#!/usr/bin/env python3
"""
Enhanced Claude Chat Integration System
Advanced processing of Claude conversations into TIL entries with better topic detection,
conversation threading, and integration with the deployment pipeline.
"""

import json
import sqlite3
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import frontmatter
import argparse
import time
from collections import Counter


def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")


class EnhancedClaudeIntegration:
    def __init__(self, db_path: Path, claude_exports_dir: Path, content_dir: Path = None):
        self.db_path = db_path
        self.claude_exports_dir = claude_exports_dir
        self.content_dir = content_dir or Path("content/claude-conversations")
        self.processed_conversations = 0
        self.skipped_conversations = 0
        
        # Enhanced topic detection
        self.topic_keywords = {
            'python': ['python', 'django', 'flask', 'pandas', 'numpy', 'fastapi', 'pydantic'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'typescript', 'npm'],
            'database': ['sql', 'sqlite', 'postgres', 'mysql', 'database', 'query', 'schema'],
            'web-development': ['html', 'css', 'frontend', 'backend', 'api', 'rest', 'graphql'],
            'system-design': ['architecture', 'design', 'system', 'scalability', 'microservices'],
            'debugging': ['error', 'debug', 'fix', 'problem', 'troubleshoot', 'exception'],
            'data-analysis': ['data', 'analysis', 'visualization', 'csv', 'json', 'analytics'],
            'documentation': ['document', 'guide', 'tutorial', 'how-to', 'explanation'],
            'deployment': ['deploy', 'production', 'server', 'hosting', 'ci/cd', 'docker'],
            'static-sites': ['static', 'generator', 'jekyll', 'hugo', 'netlify', 'github-pages'],
            'automation': ['script', 'automate', 'workflow', 'pipeline', 'cron', 'scheduling'],
            'til-system': ['til', 'blog', 'knowledge', 'learning', 'notes', 'journal']
        }
        
        # Conversation quality indicators
        self.quality_indicators = {
            'high_value': ['implementation', 'architecture', 'solution', 'algorithm', 'pattern'],
            'technical': ['function', 'class', 'method', 'variable', 'import', 'library'],
            'learning': ['learn', 'understand', 'explain', 'concept', 'principle', 'theory'],
            'problem_solving': ['issue', 'problem', 'solve', 'fix', 'bug', 'error'],
            'code_blocks': ['```', 'code', 'example', 'snippet']
        }
        
    def process_all_exports(self, force_reprocess: bool = False):
        """Process all Claude export files"""
        log("🤖 Starting enhanced Claude chat integration...")
        
        # Ensure directories exist
        self.claude_exports_dir.mkdir(exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Find export files
        export_files = list(self.claude_exports_dir.glob("**/*.json"))    

        if not export_files:
            log("📥 No Claude export files found.")
            self._show_setup_instructions()
            return
        
        log(f"Found {len(export_files)} export files")
        
        # Process each export file
        for export_file in export_files:
            try:
                self._process_export_file(export_file, force_reprocess)
            except Exception as e:
                log(f"❌ Error processing {export_file}: {e}")
        
        # Generate summary and documentation
        self._generate_integration_summary()
        
        log(f"✅ Processed {self.processed_conversations} conversations")
        log(f"⏭️  Skipped {self.skipped_conversations} conversations (already processed or low quality)")
        
    def _process_export_file(self, export_file: Path, force_reprocess: bool):
        """Process a single Claude export JSON file"""
        log(f"📄 Processing {export_file.name}...")
        
        with open(export_file, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        conversations = self._extract_conversations(export_data)
        log(f"   Found {len(conversations)} conversations in {export_file.name}")
        
        for conv_data in conversations:
            if self._should_process_conversation(conv_data, force_reprocess):
                if self._is_documentation_worthy(conv_data):
                    self._create_conversation_entry(conv_data)
                    self.processed_conversations += 1
                else:
                    self.skipped_conversations += 1
            else:
                self.skipped_conversations += 1
    
    def _should_process_conversation(self, conv_data: Dict, force_reprocess: bool) -> bool:
        """Check if conversation should be processed"""
        if force_reprocess:
            return True
            
        # Generate conversation ID
        conv_id = self._generate_conversation_id(conv_data)
        
        # Check if already processed
        conn = sqlite3.connect(self.db_path)
        existing = conn.execute(
            "SELECT 1 FROM entries WHERE conversation_id = ? LIMIT 1",
            [conv_id]
        ).fetchone()
        conn.close()
        
        return existing is None
    
    def _generate_conversation_id(self, conv_data: Dict) -> str:
        """Generate unique ID for conversation"""
        if 'id' in conv_data:
            return f"claude_{conv_data['id']}"
        
        # Generate hash from conversation content
        messages = conv_data.get('messages', [])
        content_hash = hashlib.md5(
            json.dumps(messages, sort_keys=True).encode()
        ).hexdigest()[:12]
        
        return f"claude_{content_hash}"
    
    def _extract_conversations(self, export_data: Dict) -> List[Dict]:
        """Extract conversations from different export formats"""
        # Handle Anthropic's official export format
        if isinstance(export_data, list):
            # Each item is a conversation
            return export_data
        elif 'conversations' in export_data:
            return export_data['conversations']
        elif 'chats' in export_data:
            return export_data['chats']
        elif 'data' in export_data and isinstance(export_data['data'], list):
            return export_data['data']
        else:
            # Single conversation
            return [export_data]
    
    def _is_documentation_worthy(self, conv_data: Dict) -> bool:
        """Enhanced determination of documentation worthiness"""
        messages = conv_data.get('chat_messages', conv_data.get('messages', []))

        
        if len(messages) < 4:  # Too short
            return False
        
        # Combine all message content
        all_content = self._get_conversation_content(conv_data)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(all_content)
        
        # Length bonus
        length_score = min(len(all_content) / 1000, 3)  # Max 3 points for length
        
        # Technical depth score
        tech_score = self._calculate_technical_score(all_content)
        
        total_score = quality_score + length_score + tech_score
        
        # Debug scoring
        log(f"   Conversation scoring: quality={quality_score:.1f}, "
            f"length={length_score:.1f}, tech={tech_score:.1f}, total={total_score:.1f}")
        
        return total_score >= 5.0  # Threshold for inclusion
    
    def _calculate_quality_score(self, content: str) -> float:
        """Calculate quality score based on content indicators"""
        content_lower = content.lower()
        score = 0.0
        
        for category, keywords in self.quality_indicators.items():
            category_score = sum(1 for keyword in keywords if keyword in content_lower)
            
            # Weight different categories
            if category == 'code_blocks':
                score += min(category_score * 1.5, 4)  # Code blocks are valuable
            elif category == 'high_value':
                score += min(category_score * 1.2, 3)
            else:
                score += min(category_score * 0.8, 2)
        
        return score
    
    def _calculate_technical_score(self, content: str) -> float:
        """Calculate technical depth score"""
        technical_patterns = [
            r'```\w+',  # Code blocks with language
            r'def \w+\(',  # Python functions
            r'class \w+',  # Class definitions
            r'SELECT.*FROM',  # SQL queries
            r'import \w+',  # Import statements
            r'\.py$',  # File extensions
            r'http[s]?://',  # URLs
            r'\$\s+\w+',  # Command line
        ]
        
        score = 0.0
        for pattern in technical_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.MULTILINE))
            score += min(matches * 0.5, 2)  # Max 2 points per pattern
        
        return score
    
    def _get_conversation_content(self, conv_data: Dict) -> str:
      """Extract all text content from conversation"""
      # Handle Claude export format
      messages = conv_data.get('chat_messages', conv_data.get('messages', []))
      content_parts = []
    
      for msg in messages:
        # Extract text from complex content structure
        if 'content' in msg and isinstance(msg['content'], list):
            for content_item in msg['content']:
                if isinstance(content_item, dict) and 'text' in content_item:
                    content_parts.append(content_item['text'])
        elif 'text' in msg:
            content_parts.append(str(msg['text']))
    
      return ' '.join(content_parts)
    
    def _create_conversation_entry(self, conv_data: Dict):
        """Create a TIL entry from conversation with enhanced processing"""
        title = self._generate_enhanced_title(conv_data)
        slug = self._generate_slug(title)
        conv_id = self._generate_conversation_id(conv_data)
        
        # Enhanced topic detection
        topics = self._detect_enhanced_topics(conv_data)
        
        # Generate both database entry and markdown file
        created_at = self._extract_date(conv_data)
        
        # Create markdown file for version control
        markdown_content = self._format_conversation_as_markdown(conv_data, title, topics)
        self._save_markdown_file(slug, markdown_content, topics, created_at)
        
        # Create database entry
        entry_data = {
            'slug': slug,
            'title': title,
            'content': self._extract_key_content(conv_data),
            'html': None,  # Will be generated by rebuild_database.py
            'content_type': 'claude-conversation',
            'source_type': 'claude_export',
            'conversation_id': conv_id,
            'message_count': len(conv_data.get('messages', [])),
            'created_fm': created_at,
            'topics': topics
        }
        
        self._save_database_entry(entry_data)
        log(f"  📝 Created TIL entry: {title}")
    
    def _generate_enhanced_title(self, conv_data: Dict) -> str:
        """Generate better titles using content analysis"""
        messages = conv_data.get('messages', [])
        
        if not messages:
            return f"Claude Discussion - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Look for explicit topics in first message
        first_content = messages[0].get('content', '')
        
        # Try to extract main topic from first user message
        topic_patterns = [
            r'how (?:do|can) (?:i|we) (.{1,50})',
            r'explain (.{1,50})',
            r'help (?:me )?(?:with )?(.{1,50})',
            r'create (.{1,50})',
            r'build (.{1,50})',
            r'implement (.{1,50})',
            r'understand (.{1,50})',
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, first_content.lower())
            if match:
                topic = match.group(1).strip()
                # Clean up the topic
                topic = re.sub(r'\s+', ' ', topic)
                topic = topic.split('.')[0]  # Take first sentence
                if len(topic) > 3:
                    return f"Learning: {topic.title()}"
        
        # Fallback: detect main topics and create title
        topics = self._detect_enhanced_topics(conv_data)
        if topics:
            main_topic = topics[0].replace('-', ' ').title()
            return f"Claude Discussion: {main_topic}"
        
        return f"Claude Conversation - {self._extract_date(conv_data)[:10]}"
    
    def _detect_enhanced_topics(self, conv_data: Dict) -> List[str]:
        """Enhanced topic detection with scoring"""
        content = self._get_conversation_content(conv_data).lower()
        
        topic_scores = {}
        
        for topic, keywords in self.topic_keywords.items():
            score = 0
            for keyword in keywords:
                # Count occurrences with diminishing returns
                count = content.count(keyword.lower())
                score += min(count, 3)  # Max 3 points per keyword
            
            if score > 0:
                topic_scores[topic] = score
        
        # Sort by score and return top topics
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        detected_topics = [topic for topic, score in sorted_topics if score >= 2]
        
        # Always include at least one topic
        if not detected_topics:
            detected_topics = ['general', 'claude-chat']
        elif len(detected_topics) == 1:
            detected_topics.append('claude-chat')
        
        return detected_topics[:4]  # Limit to 4 topics
    
    def _extract_date(self, conv_data: Dict) -> str:
        """Extract date from conversation data"""
        # Try different date fields
        for date_field in ['created_at', 'timestamp', 'date']:
            if date_field in conv_data:
                date_str = conv_data[date_field]
                if isinstance(date_str, str):
                    try:
                        # Parse ISO format or other common formats
                        if 'T' in date_str:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        continue
        
        # Fallback to current time
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _format_conversation_as_markdown(self, conv_data: Dict, title: str, topics: List[str]) -> str:
        """Format conversation as markdown with front matter"""
        messages = conv_data.get('messages', [])
        created_at = self._extract_date(conv_data)
        conv_id = self._generate_conversation_id(conv_data)
        
        # Create front matter
        front_matter = {
            'title': title,
            'date': created_at[:10],
            'topics': topics,
            'source': 'claude-conversation',
            'conversation_id': conv_id,
            'message_count': len(messages)
        }
        
        # Create content
        content = [
            f"# {title}",
            "",
            f"**Source:** Claude conversation",
            f"**Date:** {created_at[:10]}",
            f"**Messages:** {len(messages)}",
            "",
        ]
        
        # Add summary
        summary = self._generate_conversation_summary(conv_data)
        if summary:
            content.extend([
                "## Summary",
                "",
                summary,
                ""
            ])
        
        # Add key insights
        insights = self._extract_key_insights(conv_data)
        if insights:
            content.extend([
                "## Key Insights",
                ""
            ])
            for insight in insights:
                content.append(f"- {insight}")
            content.append("")
        
        # Add selected conversation excerpts
        key_exchanges = self._extract_key_exchanges(messages)
        if key_exchanges:
            content.extend([
                "## Key Discussion Points",
                ""
            ])
            
            for i, exchange in enumerate(key_exchanges):
                content.extend([
                    f"### Point {i+1}",
                    "",
                    exchange,
                    ""
                ])
        
        # Create the complete markdown with front matter
        markdown_doc = frontmatter.Post(
            content='\n'.join(content),
            metadata=front_matter
        )
        
        return frontmatter.dumps(markdown_doc)
    
    def _extract_key_exchanges(self, messages: List[Dict]) -> List[str]:
        """Extract key exchanges from conversation"""
        if len(messages) <= 4:
            return self._format_all_messages(messages)
        
        # Score messages by importance
        scored_messages = []
        for i, msg in enumerate(messages):
            content = msg.get('content', '')
            score = self._score_message_importance(content)
            scored_messages.append((i, msg, score))
        
        # Sort by score and take top exchanges
        scored_messages.sort(key=lambda x: x[2], reverse=True)
        
        # Take top scoring messages but maintain chronological order
        selected_indices = sorted([x[0] for x in scored_messages[:6]])
        key_messages = [messages[i] for i in selected_indices]
        
        return self._format_all_messages(key_messages)
    
    def _score_message_importance(self, content: str) -> float:
        """Score message importance for extraction"""
        score = 0.0
        content_lower = content.lower()
        
        # Length bonus (but with diminishing returns)
        score += min(len(content) / 200, 2)
        
        # Code block bonus
        score += content.count('```') * 1.5
        
        # Question/answer patterns
        if any(pattern in content_lower for pattern in ['how', 'what', 'why', 'when', 'explain']):
            score += 1
        
        # Technical content
        tech_words = ['function', 'class', 'error', 'solution', 'implement', 'database']
        score += sum(0.5 for word in tech_words if word in content_lower)
        
        return score
    
    def _format_all_messages(self, messages: List[Dict]) -> List[str]:
      """Format messages for display"""
      formatted = []
    
      for msg in messages:
        sender = msg.get('sender', 'unknown')
        
        # Extract content text
        content = ""
        if 'content' in msg and isinstance(msg['content'], list):
            text_parts = []
            for content_item in msg['content']:
                if isinstance(content_item, dict) and 'text' in content_item:
                    text_parts.append(content_item['text'])
            content = ' '.join(text_parts)
        elif 'text' in msg:
            content = str(msg['text'])
        
        # Clean and truncate if necessary
        if len(content) > 800:
            content = content[:800] + "\n\n*[Message truncated]*"
        
        role_label = "**Human:**" if sender == 'human' else "**Claude:**"
        formatted.append(f"{role_label}\n{content}")
    
      return formatted
    
    def _generate_conversation_summary(self, conv_data: Dict) -> str:
        """Generate an intelligent summary of the conversation"""
        content = self._get_conversation_content(conv_data)
        topics = self._detect_enhanced_topics(conv_data)
        
        # Extract key concepts
        key_concepts = self._extract_key_concepts(content)
        
        summary_parts = []
        
        if topics:
            summary_parts.append(f"Discussion focused on {', '.join(topics[:3])}")
        
        if key_concepts:
            summary_parts.append(f"covering {', '.join(key_concepts[:3])}")
        
        return '. '.join(summary_parts) + '.' if summary_parts else ""
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key technical concepts from content"""
        # This is a simplified approach - could be enhanced with NLP
        concept_patterns = [
            r'(?:using|with|for) (\w+(?:\.\w+)*)',  # Libraries/frameworks
            r'(?:create|build|implement) (?:a |an )?(\w+)',  # Things being built
            r'(?:error|problem|issue) (?:with |in )?(\w+)',  # Problems
        ]
        
        concepts = set()
        for pattern in concept_patterns:
            matches = re.findall(pattern, content.lower())
            concepts.update([match for match in matches if len(match) > 2])
        
        return list(concepts)[:5]
    
    def _extract_key_insights(self, conv_data: Dict) -> List[str]:
        """Extract key learning insights from conversation"""
        content = self._get_conversation_content(conv_data)
        insights = []
        
        # Look for insight patterns
        insight_patterns = [
            r'(?:learned|discovered|realized|found out) (?:that )?(.{10,100})',
            r'(?:key|important|main) (?:point|insight|takeaway) (?:is )?(.{10,100})',
            r'(?:solution|answer) (?:is|was) (.{10,100})',
        ]
        
        for pattern in insight_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:3]:  # Limit insights
                clean_insight = re.sub(r'\s+', ' ', match.strip())
                if len(clean_insight) > 10:
                    insights.append(clean_insight)
        
        return insights[:5]  # Limit to 5 insights
    
    def _extract_key_content(self, conv_data: Dict) -> str:
        """Extract key content for database storage"""
        messages = conv_data.get('messages', [])
        
        # Combine first and last few messages for preview
        key_messages = []
        if len(messages) <= 4:
            key_messages = messages
        else:
            key_messages = messages[:2] + messages[-2:]
        
        content_parts = []
        for msg in key_messages:
            role = "Human" if msg.get('role') == 'human' else "Claude"
            content = msg.get('content', '')[:300]  # Truncate for preview
            content_parts.append(f"{role}: {content}")
        
        return '\n\n'.join(content_parts)
    
    def _save_markdown_file(self, slug: str, markdown_content: str, topics: List[str], created_at: str):
        """Save conversation as markdown file"""
        # Create date-based directory structure
        date_str = created_at[:10]  # YYYY-MM-DD
        date_dir = self.content_dir / date_str[:7]  # YYYY-MM
        date_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{date_str}-{slug}.md"
        filepath = date_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        log(f"  📄 Saved markdown: {filepath.relative_to(Path.cwd())}")
    
    def _save_database_entry(self, entry_data: Dict):
        """Save conversation entry to database (for immediate use)"""
        conn = sqlite3.connect(self.db_path)
        
        # Ensure conversation-specific columns exist
        try:
            conn.execute("""
                ALTER TABLE entries ADD COLUMN content_type TEXT DEFAULT 'markdown'
            """)
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("""
                ALTER TABLE entries ADD COLUMN source_type TEXT DEFAULT 'file'
            """)
        except sqlite3.OperationalError:
            pass
        
        try:
            conn.execute("""
                ALTER TABLE entries ADD COLUMN conversation_id TEXT
            """)
        except sqlite3.OperationalError:
            pass
        
        try:
            conn.execute("""
                ALTER TABLE entries ADD COLUMN message_count INTEGER DEFAULT 0
            """)
        except sqlite3.OperationalError:
            pass
        
        try:
            # Insert/update entry
            conn.execute("""
                INSERT OR REPLACE INTO entries (
                    slug, title, content, html, content_type, source_type,
                    conversation_id, message_count, created_fm, topics_raw,
                    created_fs, modified_fs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                entry_data['slug'], entry_data['title'], entry_data['content'],
                entry_data['html'], entry_data['content_type'], entry_data['source_type'],
                entry_data['conversation_id'], entry_data['message_count'],
                entry_data['created_fm'], ','.join(entry_data['topics']),
                entry_data['created_fm'], entry_data['created_fm']  # Use same for created/modified
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
        slug = slug.strip('-')
        return slug[:60]  # Reasonable length limit
    
    def _generate_integration_summary(self):
        """Generate summary report of integration"""
        log("📊 Generating integration summary...")
        
        # Query processed conversations
        conn = sqlite3.connect(self.db_path)
        conv_stats = conn.execute("""
            SELECT 
                content_type,
                COUNT(*) as count,
                AVG(message_count) as avg_messages
            FROM entries 
            WHERE source_type = 'claude_export'
            GROUP BY content_type
        """).fetchall()
        
        topic_stats = conn.execute("""
            SELECT topics_raw, COUNT(*) as count
            FROM entries 
            WHERE source_type = 'claude_export'
            GROUP BY topics_raw
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        conn.close()
        
        # Display summary
        if conv_stats:
            log("📈 Integration Statistics:")
            for stat in conv_stats:
                log(f"   {stat[0]}: {stat[1]} entries (avg {stat[2]:.1f} messages)")
        
        if topic_stats:
            log("🏷️  Top Topics:")
            for topic_row in topic_stats[:5]:
                topics = topic_row[0] if topic_row[0] else "untagged"
                log(f"   {topics}: {topic_row[1]} conversations")
    
    def _show_setup_instructions(self):
        """Show setup instructions for Claude exports"""
        print("""
📋 Claude Export Setup Instructions:

1. **Get Claude Exports:**
   - Go to Claude Settings → Privacy → Export Data
   - Request your data export
   - Download when ready (you'll get an email)

2. **Prepare Export Files:**
   - Extract the downloaded archive
   - Place JSON files in: {self.claude_exports_dir}/
   - Files should contain conversation data

3. **Run Integration:**
   python claude_integration.py --process-all

4. **Integration with TIL System:**
   - Conversations become markdown files in content/claude-conversations/
   - Database entries are created for immediate use
   - Run your normal TIL deployment: python til_deploy.py

💡 Pro Tips:
- Use --force to reprocess existing conversations
- Check content/claude-conversations/ for generated markdown files
- Conversations are automatically categorized by topic
- Only high-quality, technical conversations are processed
        """.format(self=self))


def main():
    """Main entry point with CLI"""
    parser = argparse.ArgumentParser(description='Enhanced Claude Chat Integration')
    parser.add_argument('--process-all', action='store_true', 
                       help='Process all export files')
    parser.add_argument('--force', action='store_true', 
                       help='Force reprocessing of existing conversations')
    parser.add_argument('--exports-dir', default='claude_exports', 
                       help='Directory containing Claude export files')
    parser.add_argument('--database', default='til.db', 
                       help='TIL database file')
    parser.add_argument('--content-dir', default='content/claude-conversations', 
                       help='Directory for generated markdown files')
    
    args = parser.parse_args()
    
    # Setup paths
    exports_dir = Path(args.exports_dir)
    db_path = Path(args.database)
    content_dir = Path(args.content_dir)
    
    # Create integrator
    integrator = EnhancedClaudeIntegration(db_path, exports_dir, content_dir)
    
    if args.process_all:
        integrator.process_all_exports(args.force)
    else:
        # Show help if no action specified
        integrator._show_setup_instructions()


if __name__ == "__main__":
    main()