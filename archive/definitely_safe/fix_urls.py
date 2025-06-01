import re
from pathlib import Path

def fix_html_files():
    """Fix URLs in generated HTML files"""
    build_dir = Path("_site")
    base_url = "/TILBlog"
    
    # Find all HTML files
    html_files = list(build_dir.rglob("*.html"))
    
    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix CSS links
        content = re.sub(r'href="/static/', f'href="{base_url}/static/', content)
        
        # Fix page links
        content = re.sub(r'href="/til/', f'href="{base_url}/til/', content)
        content = re.sub(r'href="/topic/', f'href="{base_url}/topic/', content)
        content = re.sub(r'href="/"', f'href="{base_url}/"', content)
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed URLs in {html_file}")

if __name__ == "__main__":
    fix_html_files()