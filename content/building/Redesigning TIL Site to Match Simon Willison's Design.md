---
title: Claude builds new TILBlog
topics:
  - Claude
  - til-build
created: 2025-05-26 12:46:26
modified: 2025-05-26 12:46:26
slug: redesigning-til-simon-willison-style
date: 2025-05-26
excalidraw-plugin: parsed
tags:
  - excalidraw
excalidraw-open-md: true
---
Documenting a complete rebuild of the TIL Blog site,  to create an open-source system merging Obsidian, SQLite, and a static website generator.  Extensions are the use of Excalidraw and SVG, to create an iterative loop of documented innovation.

---

# Redesigning TIL Site to Match Simon Willison's Design

Today I worked with Claude to completely redesign my TIL site to match Simon Willison's clean, professional design. This conversation serves as complete documentation of the transformation process.

## 🎯 Key Design Elements Identified

From analyzing Simon's TIL site, the critical elements are:

### **1. Topic Browse Section** (Most Important!)
- **Contrasting background box** with light gray (`#f8f9fa`) 
- **Small typography** (13px) with topic links
- **Count numbers** after each topic in muted color
- **Middle dot separators** (`·`) between topics
- This is the **signature feature** of Simon's design

### **2. Minimal Header**
- **Very thin header** with just site title
- **Normal font weight** (not bold)
- **Simple underline on hover**

### **3. Entry List Design**
- **16px title font size** (larger than body)
- **Topics as small rounded pills** (`#f1f8ff` background)
- **12px metadata** (date, topics)
- **100-character preview text** in muted color (`#586069`)

### **4. Typography & Colors**
- **System font stack** (Apple/Segoe UI/Roboto)
- **14px base font size** (smaller than typical)
- **GitHub-style colors**: `#0366d6` for links, `#586069` for muted text

## 🔧 Implementation Process

### Step 1: CSS Transformation
Replaced existing CSS with Simon Willison-inspired design focusing on:
- Compact typography (14px base)
- GitHub-style color scheme
- Prominent topic browse section
- Clean, minimal spacing

### Step 2: Template Updates
Updated `index.html` to include:

```html
<section class="topic-browse">
    <h2>Browse by topic:</h2>
    <div class="topic-links">
        {% for topic in topic_cloud %}
            <a href="/topic/{{ topic.topic }}">{{ topic.topic }}</a> 
            <span class="topic-count">{{ topic.count }}</span>
            {%- if not loop.last %}<span class="topic-separator">·</span>{% endif %}
        {% endfor %}
    </div>
</section>
```

### Step 3: Entry List Structure
Updated entry display to show:
- Title (16px, medium weight)
- Date + topics on same line (12px, muted)
- 100-character preview (13px, muted)

## 💡 Key Insights

1. **Existing Flask infrastructure was perfect** - `get_topic_cloud()` function and database structure needed no changes
2. **Topic browse section is the defining feature** - This gray box at the top immediately shows content scope
3. **Restraint in design** - Simon's success comes from clean, functional design that gets out of the way

## 🎯 Results

The transformation provides:
- ✅ **Professional, clean appearance**
- ✅ **Immediate topic navigation**
- ✅ **Compact, scannable entry list**
- ✅ **Responsive mobile design**
- ✅ **Perfect integration with existing Flask routes**

## 🚀 Next Steps

- Import Claude conversations using the fixed integration script
- Implement conversation partitioning for topic-specific segments
- Continue using this self-documentation approach for future development

This conversation demonstrates the power of using Claude interactions as living documentation for development processes.