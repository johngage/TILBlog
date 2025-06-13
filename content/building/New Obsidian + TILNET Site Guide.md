---
type: new
title: New Obsidian Site Deploy
topics:
  - til-build
  - sqlite
created: 2025-05-22
---
# Obsidian + TILNET Integration Guide

## 🎯 Overview

TILNET works beautifully with Obsidian! This guide covers every integration scenario, from simple to advanced.

## 🚀 Quick Setup (Choose One)

### Option 1: TILNET as a New Vault (Simplest)

```bash
# Clone TILNET
git clone https://github.com/YOUR-USERNAME/tilnet.git

# Open Obsidian
# Click "Open folder as vault"
# Navigate to tilnet/content/
# Click "Open"
```

**Pros**: Everything just works, full git integration **Cons**: Separate from your existing notes

### Option 2: Subfolder in Existing Vault (Recommended)

```bash
# In your existing Obsidian vault
mkdir TIL

# In your TILNET directory
rm -rf content
ln -s /path/to/ObsidianVault/TIL content
```

**Pros**: Integrated with your main vault, selective publishing **Cons**: Need to remember which folder publishes

### Option 3: Cherry-Pick Publishing (Most Control)

Keep vaults separate, copy notes you want to publish:

```bash
# Create a script: publish-til.sh
#!/bin/bash
cp ~/Obsidian/Blog/ready-to-publish/*.md ~/tilnet/content/
cd ~/tilnet
python til_deploy.py
```

**Pros**: Total control, review before publishing **Cons**: Extra step in workflow

## 📁 Large Vault Strategies

### The Problem

You have 1,000+ notes but only want to publish TILs. Here's how to handle it:

### Strategy 1: Folder Structure

```
ObsidianVault/
├── 📝 TIL/                 # ← Only this publishes
│   ├── 2024-01-20.md
│   ├── python-tips.md
│   └── web-dev/
├── 🔒 Personal/            # Private
├── 📚 Reference/           # Private
├── 💼 Work/               # Private
└── 📎 Attachments/         # Private
```

### Strategy 2: Tag-Based Workflow

1. Tag notes you want to publish with `#til-public`
2. Use this Dataview query to see them:

```dataview
LIST
FROM #til-public
SORT file.ctime DESC
```

3. Manually copy or script the export:

```python
# export_tagged_tils.py
import os
import shutil
from pathlib import Path

vault = Path("/path/to/ObsidianVault")
tilnet = Path("/path/to/tilnet/content")

for md_file in vault.rglob("*.md"):
    with open(md_file, 'r') as f:
        if '#til-public' in f.read():
            shutil.copy(md_file, tilnet / md_file.name)
```

### Strategy 3: Separate Public Vault

Maintain two vaults:

- **Main Vault**: Everything (private)
- **TILNET Vault**: Just your public TILs

Use Obsidian's "Move file to another vault" command when ready to publish.

## 🎨 Obsidian Templates for TILNET

### Basic TIL Template

Save as `Templates/TIL Template.md`:

```markdown
---
title: "{{title}}"
topics:
  - {{cursor}}
created: {{date:YYYY-MM-DD}}
---

## What I Learned

## Key Points

- 

## Example

## References

- 
```

### Daily TIL Template

Save as `Templates/Daily TIL.md`:

```markdown
---
title: "Daily Notes - {{date:YYYY-MM-DD}}"
topics:
  - daily
created: {{date:YYYY-MM-DD}}
---

## Today I Learned

### Morning
- 

### Afternoon
- 

### Evening
- 

## Interesting Links

- 

## Tomorrow's Goals

- 
```

### Technical Topic Template

````markdown
---
title: "{{title}}"
topics:
  - programming
  - {{language}}
created: {{date:YYYY-MM-DD}}
---

## The Problem

## The Solution

```{{language}}
// Code here
````

## How It Works

## When to Use This

## References

- [Official Docs](https://claude.ai/chat/089c3eda-fd7a-43bf-b6b4-1ba38a8462c2)

````

## 🔧 Advanced Configuration

### Custom Frontmatter Processing

Add to your Obsidian notes, TILNET will handle:

```yaml
---
title: "Advanced Frontmatter"
topics:
  - obsidian
  - tilnet
created: 2024-01-20
modified: 2024-01-21
author: Your Name
draft: false
aliases:
  - "Alternative Title"
  - "Another Name"
---
````

### Handling Obsidian-Specific Features

|Obsidian Feature|TILNET Behavior|Solution|
|---|---|---|
|[[Wiki Links]]|✅ Converted to HTML|Automatic|
|![[Embedded Images]]|⚠️ Needs setup|Put images in `static/images/`|
|Dataview Queries|❌ Not rendered|Use for organization only|
|Mermaid Diagrams|✅ Works|Standard markdown|
|LaTeX Math|✅ Works|MathJax included|
|Callouts|⚠️ Partial|Converts to blockquotes|
|Canvas Files|❌ Not supported|Export as image|

### Image Handling

```bash
# Option 1: Copy attachments folder
cp -r ObsidianVault/Attachments/* tilnet/static/images/

# Option 2: Symlink attachments
ln -s /path/to/ObsidianVault/Attachments tilnet/static/images
```

Update Obsidian settings:

- Settings → Files & Links → Default location for new attachments
- Set to: "In the folder specified below"
- Folder path: `Attachments`

### .tilignore File

Create `content/.tilignore` to exclude files:

```
.obsidian/
Templates/
Archive/
*.canvas
*.draft.md
*-private.md
_*.md
.DS_Store
```

## 🚄 Optimized Workflow

### 1. Hotkeys Setup

Add these Obsidian hotkeys:

- `Cmd+Shift+T`: Create new TIL from template
- `Cmd+Shift+P`: Run publish script
- `Cmd+Shift+O`: Open TILNET preview

### 2. QuickAdd Plugin Configuration

1. Install QuickAdd plugin
2. Create macro: "New TIL"
    - Create new file from template
    - Add to TIL folder
    - Open in new pane

### 3. Shell Commands Plugin

Install Shell Commands plugin and add:

```bash
Name: Deploy TILNET
Command: cd /path/to/tilnet && python til_deploy.py
```

Now deploy with one click from Obsidian!

### 4. Automated Sync Script

```python
# watch_and_deploy.py
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TILHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            print(f"Detected change: {event.src_path}")
            subprocess.run(["python", "til_deploy.py"])

observer = Observer()
observer.schedule(TILHandler(), path='content/', recursive=True)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

## 📊 Tracking Your TILs in Obsidian

### Dataview Dashboard

Create `TIL Dashboard.md`:

````markdown
# TIL Dashboard

## Recent TILs
```dataview
TABLE topics, created
FROM "TIL"
SORT created DESC
LIMIT 10
```

## TILs by Topic
```dataview
TABLE length(rows) as Count
FROM "TIL"
GROUP BY topics
SORT length(rows) DESC
```

## This Week's Learning
```dataview
LIST
FROM "TIL"
WHERE created >= date(today) - dur(7 days)
SORT created DESC
```
````

## 🎯 Best Practices

### DO:

- ✅ Keep TILs focused and concise
- ✅ Use descriptive titles
- ✅ Tag consistently
- ✅ Include code examples
- ✅ Add images to `/static/images/`
- ✅ Test locally before deploying

### DON'T:

- ❌ Put private notes in content/
- ❌ Use complex Obsidian plugins in TILs
- ❌ Forget to add frontmatter
- ❌ Include sensitive information
- ❌ Make TILs too long (aim for < 500 words)

## 🚨 Troubleshooting

### "My notes aren't showing up"

Check:

1. Notes are in `content/` folder
2. Have valid frontmatter (---)
3. Have a title
4. Run `python rebuild_database.py` manually

### "Images are broken"

1. Put images in `static/images/`
2. Reference as `/static/images/myimage.png`
3. Don't use Obsidian's `![[image]]` syntax

### "Wiki links not working"

TILNET converts [[Note Name]] to links, but the target note must:

1. Exist in content/
2. Have matching title in frontmatter
3. Be published (not draft)

---

_Happy learning! Your Obsidian vault + TILNET = 🚀_