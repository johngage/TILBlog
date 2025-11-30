# TILNET - Today I Learned Network

A self-documenting knowledge management system that transforms your learning journey and Claude AI conversations into a searchable, beautiful static website.

## 🌟 What is TILNET?

TILNET combines the simplicity of markdown files with the power of SQLite to create a fast, searchable archive of everything you learn. Inspired by Simon Willison's TIL pattern, TILNET adds:

- **Instant Search**: Ctrl+K to search across all your notes
- **Claude Integration**: Import and analyze your AI conversations
- **Smart Organization**: Automatic topic extraction and linking
- **Simple Deployment**: One command to build and deploy
- **Beautiful Design**: Clean, responsive, dark mode support

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/tilnet.git
cd tilnet
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add Your First TIL

Create a markdown file in `content/`:

```markdown
---
title: "Learning Python Decorators"
topics:
  - python
  - programming
created: 2024-01-15
---

Today I learned how Python decorators work...
```

### 3. Build and Deploy with One Command

```bash
python til_deploy.py
```

That's it! This single command:
- ✅ Rebuilds your database from markdown files
- ✅ Generates a static site with search
- ✅ Commits all changes
- ✅ Deploys to GitHub Pages

Your site will be live at: `https://yourusername.github.io/tilnet/`

## 📁 Project Structure

```
tilnet/
├── content/              # Your markdown TIL entries
├── templates/            # HTML templates (customizable)
├── static/               # CSS and JavaScript
├── til_deploy.py        # 🌟 One-command deployment
├── til_static_builder.py # Static site generator
├── rebuild_database.py   # Database management
└── app.py               # Local development server
```

## ✨ Features

### One-Command Deployment
Unlike complex CI/CD setups, TILNET uses a simple Python script:

```bash
python til_deploy.py
```

This is:
- **Transparent**: Read the script to see exactly what happens
- **Portable**: Works with any git host (GitHub, GitLab, etc.)
- **Customizable**: Easy to modify for different hosting providers
- **Educational**: Great for learning deployment concepts

### Instant Search (Ctrl+K)
- Blazing fast client-side search
- Search across titles, content, and topics
- Highlighted matches
- Works offline

### Smart Organization
- Automatic topic extraction
- Cross-references between entries
- Chronological and topic-based browsing
- Modified date tracking

## 🛠️ Deployment Options

### Primary Method: Simple Python Script (Recommended)

The `til_deploy.py` script is the heart of TILNET's simplicity:

```bash
python til_deploy.py
```

What it does:
1. 📄 Updates database from your markdown files
2. 🏗️  Generates static site with search index
3. 📦 Commits all changes to git
4. 🌐 Deploys to GitHub Pages

**Why we recommend this:**
- **One command** - No complex configuration
- **Readable** - Open the script and understand every step
- **Portable** - Easy to adapt for Netlify, Vercel, S3, etc.
- **Reliable** - You control when deployment happens

### Alternative: GitHub Actions (Advanced)

For automatic deployment on every push, you can enable GitHub Actions:

1. Rename the example workflow:
```bash
mv .github/workflows/deploy.yml.example .github/workflows/deploy.yml
```

2. Update the workflow file to use `_site` instead of `build` directory

3. Push to GitHub - deployments will happen automatically

**Note**: This is more complex and locks you into GitHub's infrastructure. We recommend starting with `til_deploy.py` and only switching to Actions if you need true CI/CD.

## 🎨 Customization

### Adapting for Different Hosts

The beauty of `til_deploy.py` is how easy it is to modify:

```python
# For Netlify
run_command("netlify deploy --prod --dir=_site", "Netlify deployment")

# For Vercel
run_command("vercel --prod _site/", "Vercel deployment")

# For S3
run_command("aws s3 sync _site/ s3://your-bucket/", "S3 deployment")
```

### Site Configuration

Edit `til_static_builder.py` to customize:

```python
# Change base URL for your GitHub Pages
builder = TILStaticSiteBuilder(
    base_url='/your-repo-name'  # Update this
)
```

### Styling

Modify `static/styles.css` for custom styling. The design follows Simon Willison's aesthetic:
- Clean typography
- Subtle colors
- Focus on readability

## 🔧 Advanced Usage

### Local Development

For local testing with hot reload:

```bash
python app.py
# Visit http://localhost:5000
```

### Manual Build Steps

If you prefer to run steps separately:

```bash
# Step 1: Update database
python rebuild_database.py

# Step 2: Generate static site
python til_static_builder.py --base-url '/your-repo'

# Step 3: Test locally
cd _site
python -m http.server 8000

# Step 4: Deploy manually
git add _site/
git commit -m "Update site"
git subtree push --prefix=_site origin gh-pages
```

### Import Claude Conversations

1. Export your Claude data
2. Place in `claude_exports/latest/`
3. Run: `python claude_tilnet_integration.py`

### Database Access

Query your knowledge directly:

```bash
sqlite3 til.db
sqlite> SELECT title, created FROM entries WHERE topics_raw LIKE '%python%';
```

## 🤝 Contributing

TILNET is designed to be forked and customized:

1. Fork the repository
2. Make your improvements
3. Share back with the community

Some ideas:
- Add support for other note formats
- Create new themes
- Add analytics integration
- Build import scripts for other platforms

## 📚 Philosophy

TILNET follows these principles:

1. **Simple > Complex**: One command deployment over CI/CD pipelines
2. **Readable > Clever**: Clear Python over obscure YAML
3. **Portable > Convenient**: Works anywhere, not just GitHub
4. **Educational > Magical**: You should understand how it works

## 🙏 Acknowledgments

- Simon Willison for the TIL concept and design inspiration
- The Python community for excellent libraries
- Claude AI for being a great learning companion
- You, for documenting your learning journey!

## 🚨 Troubleshooting

### "GitHub Pages not updating"
- Wait 2-3 minutes - GitHub Pages has a delay
- Check: `https://github.com/yourusername/tilnet/settings/pages`
- Ensure gh-pages branch exists

### "Search not working"
- Check browser console for errors
- Verify `search-index.json` exists in `_site/`
- Try Ctrl+Shift+R to hard refresh

### "Database not building"
- Check your markdown files have proper frontmatter
- Run `python rebuild_database.py` and check for errors
- Ensure content files are in `content/` directory

## 📄 License

MIT License - Feel free to use TILNET for your own learning journey!

---

**Start documenting what you learn today!** Run `python til_deploy.py` and share your knowledge with the world.

---
2025-11-29: Starting again. 
- on Mac, cd to ~/TILBlog
	- cd /Users/johngage/TILBlog
- invoke existing conda environment
	- conda activate tilblog
- make sure each file has frontmatter:

```---
title: "Your Title"
topics:
  - topic1
  - topic2
created: 2024-11-29
---

Your content...
```
# Your daily workflow:
cd /Users/johngage/TILBlog
conda activate tilblog
python til_deploy.py

---
