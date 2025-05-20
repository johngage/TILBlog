---
title: "Creating a TIL Blog with Flask and Front Matter"
topics: ["flask", "python", "web-development", "obsidian", "markdown"]
created: 2024-01-15
slug: flask-til-blog-frontmatter
---

# Creating a TIL Blog with Flask and Front Matter

Today I learned how to upgrade my TIL blog to use YAML front matter instead of folder structure for organizing topics.

## Key Changes

The new approach uses **front matter** in each markdown file:

```yaml
---
title: "My Note Title"
topics: ["python", "flask", "web-development"]
created: 2024-01-15
---
```

## Benefits

### Multiple Topics per Note
Now each note can belong to multiple topics! This Python Flask tutorial can be tagged with:
- `python`
- `flask` 
- `web-development`
- `authentication` (if it covers login)

### Obsidian Integration
This structure works perfectly with [[Obsidian]] because:
- Front matter is displayed nicely
- Topics can be used with the Dataview plugin
- [[Wiki links]] work automatically
- File organization is flexible

### Auto-Rebuild
The blog now watches for file changes and rebuilds automatically when I save in Obsidian. No more manual rebuilds!

## Wiki Links
I can now link between notes using [[Wiki Links]] syntax, and they'll automatically be converted to proper HTML links in the blog.

## Implementation Notes

The database schema changed to support many-to-many relationships:
- `entries` table for posts
- `topics` table for topic names  
- `entry_topics` junction table

This is much more flexible than the old folder-based system and scales to hundreds of topics easily.
