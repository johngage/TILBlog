<%*
// Get topics from user
const topicsInput = await tp.system.prompt("Enter topics (comma-separated)", "");
const topics = topicsInput.split(',').map(t => `"${t.trim()}"`).join(', ');

// Get current timestamp
const now = tp.date.now("YYYY-MM-DD HH:mm:ss");

// Generate slug
const slug = tp.file.title.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-');

// Optional: Ask for source/reference
const source = await tp.system.prompt("Source/Reference URL (optional - press Enter to skip)", "");

// Build the front matter
let frontMatter = `---
title: "${tp.file.title}"
topics: [${topics}]
created: ${now}
modified: ${now}
slug: ${slug}`;
excalidraw-plugin: parsed 
tags: 
  - excalidraw 
excalidraw-open-md: true

if (source && source.trim() !== "") {
  frontMatter += `\nsource: "${source.trim()}"`;
}

frontMatter += `\n---`;

// Output the front matter
tR += frontMatter;
%>

# <% tp.file.title %>

## Summary

<% tp.file.cursor() %>

## Details

## Links/References

<%* if (source && source.trim() !== "") { %>- [Source](<% source.trim() %>)
<%* } %>