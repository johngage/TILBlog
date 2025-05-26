<%*
// Get topics from user
const topicsInput = await tp.system.prompt("Enter topics (comma-separated)", "");
const topics = topicsInput.split(',').map(t => `"${t.trim()}"`).join(', ');

// Get current timestamp
const now = tp.date.now("YYYY-MM-DD HH:mm:ss");

// Generate slug
const slug = tp.file.title.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-');
%>---
title: "<% tp.file.title %>"
topics: [<% topics %>]
created: <% now %>
modified: <% now %>
slug: <% slug %>
date: <% tp.date.now("YYYY-MM-DD") %>
excalidraw-plugin: parsed 
tags: 
  - excalidraw 
excalidraw-open-md: true
---

# <% tp.file.title %>

## What I Learned

<% tp.file.cursor() %>

## Details

## References