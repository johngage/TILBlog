#!/usr/bin/env python
"""
Performance testing script for TIL blog rebuild process
Tests different scenarios and measures timing
"""
import os
import sys
import time
import sqlite3
import shutil
import subprocess
from pathlib import Path

def log(message):
    """Print a timestamped log message"""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def time_function(func, description):
    """Time how long a function takes to run"""
    log(f"🕐 Starting: {description}")
    start_time = time.time()
    
    try:
        result = func()
        elapsed = time.time() - start_time
        log(f"✅ Completed: {description} in {elapsed:.2f} seconds")
        return elapsed, True, result
    except Exception as e:
        elapsed = time.time() - start_time
        log(f"❌ Failed: {description} after {elapsed:.2f} seconds - {e}")
        return elapsed, False, None

def get_database_stats():
    """Get current database statistics"""
    try:
        conn = sqlite3.connect("til.db")
        entries_count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        topics_count = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        conn.close()
        return entries_count, topics_count
    except Exception as e:
        log(f"Error getting database stats: {e}")
        return 0, 0

def rebuild_database():
    """Rebuild the database from content files"""
    result = subprocess.run(["python", "rebuild_database.py"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Database rebuild failed: {result.stderr}")
    return result.returncode == 0

def build_static_site():
    """Build the static site"""
    result = subprocess.run(["python", "til_static_builder.py"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Static site build failed: {result.stderr}")
    return result.returncode == 0

def count_generated_files():
    """Count files in the generated site"""
    build_dir = Path("_site")
    if not build_dir.exists():
        return 0, 0, 0
        
    html_files = len(list(build_dir.rglob("*.html")))
    css_files = len(list(build_dir.rglob("*.css")))
    total_files = len(list(build_dir.rglob("*")))
    
    return html_files, css_files, total_files

def create_test_content():
    """Create a test TIL entry"""
    test_content = f"""---
title: "Performance Test Entry {int(time.time())}"
date: {time.strftime('%Y-%m-%d')}
topics: 
  - testing
  - performance
---

# Performance Test Entry

This is a test entry created at {time.strftime('%Y-%m-%d %H:%M:%S')} to test rebuild performance.

## Test Details

- Created by performance test script
- Used to measure incremental rebuild times
- Should be automatically cleaned up after testing
"""
    
    # Create test file
    test_file = Path("content/testing/performance-test.md")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(test_file, "w") as f:
        f.write(test_content)
    
    return test_file

def cleanup_test_content(test_file):
    """Remove test content"""
    if test_file and test_file.exists():
        test_file.unlink()
        # Remove directory if empty
        try:
            test_file.parent.rmdir()
        except OSError:
            pass  # Directory not empty

def run_performance_tests():
    """Run comprehensive performance tests"""
    log("🧪 Starting TIL Blog Performance Tests")
    log("=" * 50)
    
    # Initial state
    entries_count, topics_count = get_database_stats()
    log(f"📊 Initial state: {entries_count} entries, {topics_count} topics")
    
    # Test 1: Full rebuild from scratch
    log("\n🔄 Test 1: Full database rebuild")
    rebuild_time, rebuild_success, _ = time_function(rebuild_database, "Full database rebuild")
    
    if rebuild_success:
        new_entries, new_topics = get_database_stats()
        log(f"📊 After rebuild: {new_entries} entries, {new_topics} topics")
    
    # Test 2: Static site generation (cold)
    log("\n🏗️  Test 2: Static site generation (cold)")
    if Path("_site").exists():
        shutil.rmtree("_site")
    
    build_time, build_success, _ = time_function(build_static_site, "Static site generation (cold)")
    
    if build_success:
        html_files, css_files, total_files = count_generated_files()
        log(f"📊 Generated: {html_files} HTML files, {css_files} CSS files, {total_files} total files")
    
    # Test 3: Static site generation (warm/incremental)
    log("\n🔥 Test 3: Static site generation (warm)")
    warm_build_time, warm_build_success, _ = time_function(build_static_site, "Static site generation (warm)")
    
    # Test 4: Add new content and measure incremental rebuild
    log("\n➕ Test 4: Incremental rebuild with new content")
    test_file = create_test_content()
    
    try:
        # Rebuild database with new content
        inc_rebuild_time, inc_rebuild_success, _ = time_function(
            rebuild_database, "Incremental database rebuild"
        )
        
        # Rebuild site with new content
        inc_build_time, inc_build_success, _ = time_function(
            build_static_site, "Incremental site rebuild"
        )
        
        if inc_build_success:
            new_html, new_css, new_total = count_generated_files()
            log(f"📊 After increment: {new_html} HTML files")
            
    finally:
        cleanup_test_content(test_file)
    
    # Test 5: Deployment simulation (without actual push)
    log("\n🚀 Test 5: Deployment preparation")
    deploy_prep_time, deploy_success, _ = time_function(
        lambda: subprocess.run(["git", "add", "_site"], check=True),
        "Git staging of _site directory"
    )
    
    # Summary
    log("\n" + "=" * 50)
    log("📈 PERFORMANCE SUMMARY")
    log("=" * 50)
    
    if rebuild_success:
        log(f"🔄 Full database rebuild: {rebuild_time:.2f}s")
    if build_success:
        log(f"🏗️  Cold static build: {build_time:.2f}s")
    if warm_build_success:
        log(f"🔥 Warm static build: {warm_build_time:.2f}s")
        if build_success and warm_build_success:
            speedup = build_time / warm_build_time
            log(f"   📊 Warm build speedup: {speedup:.1f}x faster")
    
    if inc_rebuild_success and inc_build_success:
        total_incremental = inc_rebuild_time + inc_build_time
        log(f"➕ Incremental rebuild: {total_incremental:.2f}s (DB: {inc_rebuild_time:.2f}s + Build: {inc_build_time:.2f}s)")
    
    # Performance recommendations
    log("\n💡 OPTIMIZATION RECOMMENDATIONS")
    log("=" * 50)
    
    if rebuild_time > 5.0:
        log("⚡ Database rebuild is slow (>5s). Consider:")
        log("   - Only rebuilding changed files")
        log("   - Using file modification time checks")
        log("   - Implementing incremental updates")
    
    if build_time > 3.0:
        log("⚡ Static site generation is slow (>3s). Consider:")
        log("   - Template caching")
        log("   - Only regenerating changed pages")
        log("   - Optimizing database queries")
    
    if warm_build_time > build_time * 0.8:
        log("⚡ Warm builds aren't much faster than cold builds. Consider:")
        log("   - Implementing proper incremental builds")
        log("   - Caching rendered templates")
    
    total_workflow_time = (rebuild_time if rebuild_success else 0) + (build_time if build_success else 0)
    log(f"\n⏱️  Total workflow time: {total_workflow_time:.2f}s")
    
    if total_workflow_time < 10:
        log("✅ Performance is good for typical usage")
    elif total_workflow_time < 30:
        log("⚠️  Performance is acceptable but could be improved")
    else:
        log("❌ Performance needs optimization for frequent updates")

if __name__ == "__main__":
    run_performance_tests()