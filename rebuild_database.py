#!/usr/bin/env python3

import os
import pathlib
import frontmatter
import sys

def validate_content_files(content_dir):
    """Validate all markdown files before rebuilding database"""
    print("🔍 Validating content files...")
    
    if not content_dir.exists():
        print(f"❌ Content directory {content_dir} not found!")
        return False
    
    md_files = list(content_dir.glob("**/*.md"))
    print(f"Found {len(md_files)} markdown files to validate")
    
    issues_found = 0
    
    for filepath in md_files:
        file_issues = validate_single_file(filepath, content_dir)
        issues_found += len(file_issues)
    
    if issues_found == 0:
        print("✅ All content files validated successfully!")
        return True
    else:
        print(f"❌ Found {issues_found} issues in content files")
        print("Fix these issues before rebuilding the database")
        return False

def validate_single_file(filepath, content_dir):
    """Validate a single markdown file"""
    issues = []
    relative_path = filepath.relative_to(content_dir)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for proper frontmatter structure
        if not content.startswith('---'):
            issues.append(f"📄 {relative_path}: Missing opening --- for frontmatter")
            return issues
        
        # Try to parse frontmatter
        try:
            post = frontmatter.loads(content)
            fm = post.metadata
            body = post.content
        except Exception as e:
            issues.append(f"📄 {relative_path}: Invalid YAML frontmatter - {e}")
            return issues
        
        # Check for content after frontmatter that should be IN frontmatter
        lines = body.strip().split('\n')
        for i, line in enumerate(lines[:5]):  # Check first 5 lines of content
            if line.startswith('title:') or line.startswith('topics:') or line.startswith('created:'):
                issues.append(f"📄 {relative_path}: Found '{line.split(':')[0]}:' in content - should be in frontmatter")
        
        # Check for title (either in frontmatter or as first heading)
        has_title = bool(fm.get('title'))
        has_heading = any(line.startswith('# ') for line in lines)
        
        if not has_title and not has_heading:
            issues.append(f"📄 {relative_path}: No title in frontmatter and no # heading in content")
        
        # Check for topics
        if not fm.get('topics'):
            issues.append(f"📄 {relative_path}: No topics specified in frontmatter")
        elif not isinstance(fm['topics'], list):
            issues.append(f"📄 {relative_path}: Topics should be a list (use - topic1, - topic2)")
        
        # Report success for files with no issues
        if not issues:
            title = fm.get('title') or 'No title'
            topics = fm.get('topics', [])
            print(f"  ✅ {relative_path} - '{title}' (topics: {topics})")
    
    except Exception as e:
        issues.append(f"📄 {relative_path}: Error reading file - {e}")
    
    # Print issues for this file
    for issue in issues:
        print(f"  ⚠️  {issue}")
    
    return issues

def main():
    # Get the directory where the script is located
    root = pathlib.Path(__file__).parent.resolve()
    db_path = root / "til.db"
    content_dir = root / "content"
    
    print("🚀 Starting TIL Database Rebuild")
    print("=" * 40)
    
    # Step 1: Validate content files
    if not validate_content_files(content_dir):
        print("\n❌ Content validation failed!")
        print("Please fix the issues above before rebuilding the database.")
        print("\nCommon fixes:")
        print("  - Move title:, topics:, created: INTO the frontmatter (between --- lines)")
        print("  - Ensure topics are formatted as a list:")
        print("    topics:")
        print("      - topic1")
        print("      - topic2")
        print("  - Add a title to your frontmatter or a # heading to your content")
        return 1
    
    # Step 2: Remove old database if it exists
    if db_path.exists():
        print("\n🗑️  Removing old database...")
        os.remove(db_path)
        print("Old database removed.")
    
    # Step 3: Import and rebuild
    print("\n🔨 Building new database...")
    try:
        from app import build_database
        build_database(root)
        print("✅ Database rebuild complete!")
        
        # Quick verification
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        entry_count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        topic_count = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        conn.close()
        
        print(f"📊 Database contains: {entry_count} entries, {topic_count} topics")
        
    except Exception as e:
        print(f"❌ Database rebuild failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())