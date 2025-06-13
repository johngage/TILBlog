---
title: Designing TILNET to be clonable
topics:
  - til-build
created: 2025-06-08
date: 2025-06-08
---
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

### 3️⃣ Connect Your Obsidian Vault (2 minutes)

#### Option A: Start Fresh with TILNET as Your Vault

```bash
# Open Obsidian and create a new vault
# Choose the tilnet/content folder as your vault location
# Now any note you create in Obsidian goes straight to TILNET!
```

#### Option B: Use Part of Your Existing Vault

If you have an existing Obsidian vault with many notes:

```bash
# Create a TIL folder in your existing vault
mkdir ~/ObsidianVault/TIL

# Link it to TILNET (Mac/Linux)
ln -s ~/ObsidianVault/TIL content

# Windows (run as Administrator)
mklink /D content "C:\Users\YOU\ObsidianVault\TIL"
```

Now only notes in your `TIL` folder will be published!

#### Option C: Copy Select Notes

For maximum control, copy only the notes you want to publish:

```bash
# Copy specific notes to TILNET
cp ~/ObsidianVault/python-decorators.md content/
cp ~/ObsidianVault/Projects/learned-today.md content/
```

### 🚨 Large Vault? Here's What to Do

If you have 100+ notes in Obsidian:

**DON'T** put your entire vault in `content/` - you'll publish everything!

**DO** one of these:

1. **Subfolder Method**: Create a `TIL` or `Public` folder in Obsidian, symlink only that
2. **Tag Method**: Tag notes with `#til-public`, then copy those to `content/`
3. **New Vault**: Keep TILNET as a separate, focused learning vault

### 4️⃣ Create Your First TIL (30 seconds)

In Obsidian, create a new note with this template:

````markdown
---
title: "My First TIL"
topics:
  - learning
  - obsidian
created: 2024-01-20
---

Today I learned how to connect Obsidian with TILNET!

## Key Points

- TILNET reads any .md file in the content folder
- Obsidian's [[wiki links]] are automatically converted
- Images should go in static/images/

## Code Example

```python
# This code will have syntax highlighting!
print("Hello from Obsidian + TILNET!")
````

````

💡 **Obsidian Template Tip**: Save this as a template in Obsidian for quick TIL creation!

### 5️⃣ Deploy to the World (1 minute)

```bash
python til_deploy.py
````

### 6️⃣ View Your Site! (30 seconds)

Visit: `https://YOUR-USERNAME.github.io/tilnet/`

---

## That's It! You're Done! 🎉

Your Obsidian notes are now a beautiful website with:

- ✅ All your wiki links working
- ✅ Instant search (Ctrl+K)
- ✅ Topic organization
- ✅ Syntax highlighting
- ✅ Mobile friendly

## Obsidian + TILNET Workflow

1. **Write in Obsidian** - Use all your favorite plugins
2. **Save** - Just regular Obsidian saving
3. **Deploy** - Run `python til_deploy.py`
4. **Share** - Your notes are online!

## Obsidian-Specific Tips

### Wiki Links

```markdown
[[My Other Note]] → Automatically converted to HTML links
![[image.png]] → Put images in static/images/
```

### Frontmatter Template

Create an Obsidian template with TILNET frontmatter:

```yaml
---
title: "{{title}}"
topics:
  - 
created: {{date}}
modified: 
---
```

### Daily Notes

Perfect for TIL! Set Obsidian's daily note template to:

```markdown
---
title: "Daily Notes - {{date}}"
topics:
  - daily
created: {{date}}
---

## Today I Learned

- 
```

### Large Vault Organization

```
ObsidianVault/
├── Personal/        # Not published
├── Projects/        # Not published  
├── Archive/         # Not published
└── TIL/            # ← Only this syncs to TILNET
    ├── python/
    ├── web-dev/
    └── daily/
```

### Exclude Patterns

If you accidentally put your whole vault in `content/`, create `content/.tilignore`:

```
Personal/
Private/
.obsidian/
Templates/
Archive/
*.draft.md
```

## Next Steps

- **Set up hotkeys** in Obsidian for quick TIL creation
- **Use Dataview** to see all your TILs within Obsidian
- **Try Excalidraw** - drawings work great in TILNET!

## FAQ

**Q: Can I use Obsidian plugins?** A: Yes! But remember only standard Markdown features will appear on your website.

**Q: What about my private notes?** A: Only notes in the `content/` folder are published. Keep private notes elsewhere.

**Q: Can I preview before deploying?** A: Run `python app.py` and visit http://localhost:5000

---

_Remember: The best TIL is the one you actually write. Open Obsidian and start now!_