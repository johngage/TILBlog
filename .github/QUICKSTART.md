# TILNET Quick Start - 5 Minutes to Your First Deploy! 🚀

## The Simplest Path to Your Own TIL Site

### 1️⃣ Fork and Clone (30 seconds)

Click "Fork" on GitHub, then:
```bash
git clone https://github.com/YOUR-USERNAME/tilnet.git
cd tilnet
```

### 2️⃣ Set Up Python (1 minute)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ Write Your First TIL (2 minutes)

Create `content/my-first-til.md`:
```markdown
---
title: "My First TIL"
topics:
  - learning
  - tilnet
created: 2024-01-20
---

Today I learned how to set up TILNET! It's amazingly simple:

- Just write markdown files
- Run one command to deploy
- Everything else is automatic!
```

### 4️⃣ Deploy to the World (1 minute)

```bash
python til_deploy.py
```

### 5️⃣ View Your Site! (30 seconds)

Visit: `https://YOUR-USERNAME.github.io/tilnet/`

---

## That's It! You're Done! 🎉

Your site now has:
- ✅ Beautiful design
- ✅ Instant search (Ctrl+K)
- ✅ Topic organization  
- ✅ RSS feed
- ✅ Dark mode
- ✅ Mobile friendly

## What Just Happened?

The `til_deploy.py` script did everything:
1. Built a database from your markdown
2. Generated a static site with search
3. Pushed it to GitHub Pages

## Next Steps

- Add more TILs to `content/`
- Run `python til_deploy.py` again
- That's the entire workflow!

## Tips

- **Categories**: Use folders in `content/` like `content/python/`, `content/web/`
- **Images**: Put them in `static/images/` and reference with `/static/images/myimage.png`
- **Preview locally**: Run `python app.py` and visit http://localhost:5000

## No CI/CD, No YAML, No Complexity

Just:
1. Write markdown
2. Run `python til_deploy.py`
3. Share your learning!

---

*Remember: The best TIL is the one you actually write. Start now!*