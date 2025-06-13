---
title: Building TILBlog in Claude
topics:
  - til-build
created: 2025-05-26 13:29:20
modified: 2025-05-26 13:29:20
slug: building-tilblog
date: 2025-05-26
excalidraw-plugin: parsed
tags:
  - excalidraw
excalidraw-open-md: true
---
TIL for TILNET

Many sequential Claude conversations were required, because Claude conversations reached limits, and had to be restarted.  
- Challenge: provide new conversation with enough context of the state of development to enable useful coding suggestions

So, all Claude conversations will be harvested, turned into archive Markdown files, and posted to [[TILNET]], so that they may be analyzed by NotebookLM, and by new versions of Claude.
- Goal: improve Claude's ability to develop code
- Goal: create the human-side documentation

As a side-note, the process of working with Claude Sonnet 4 for the past week to design a database repository for Obsidian notes that then feeds into a static site generator has been instructive.

Most major design issues have been addressed.

---
14:01: 2025-06-01
### Do not use this; exhaustive dump of all code, content- see [[#Short sequence to capture essence of TILBLOG code]]
- Generated complete site survey, using a large shell script. Need to update it as site updates; generates copies of .py files, .html; 
- snapshot.sh
	```sh
	#!/bin/zsh

# TILNET Project Context Snapshot

# Run this script to generate a comprehensive project snapshot for Claude

echo "=== TILNET PROJECT SNAPSHOT ==="

echo "Generated: $(date)"

echo ""

echo "=== PROJECT DIRECTORY TREE ==="

tree -a -I '.git|__pycache__|*.pyc|node_modules|.DS_Store' 2>/dev/null || find . -type f -not -path '*/\.*' -not -path '*/__pycache__/*' | sort

echo ""

echo "=== PYTHON FILES ==="

find . -name "*.py" -type f | while read file; do

echo "--- FILE: $file ---"

cat "$file"

echo ""

done


echo "=== HTML FILES ==="

find . -name "*.html" -type f | while read file; do

echo "--- FILE: $file ---"

cat "$file"

echo ""

done


echo "=== CSS FILES ==="

find . -name "*.css" -type f | while read file; do

echo "--- FILE: $file ---"

cat "$file"

echo ""

done


echo "=== JAVASCRIPT FILES ==="

find . -name "*.js" -type f | while read file; do

echo "--- FILE: $file ---"

cat "$file"

echo ""

done

  

echo "=== CONFIGURATION FILES ==="

for config in requirements.txt package.json Dockerfile docker-compose.yml .env.example config.py settings.py; do

if [[ -f "$config" ]]; then

echo "--- FILE: $config ---"

cat "$config"

echo ""

fi

done

  

echo "=== PROJECT STATUS ==="

echo "Last modified files (last 5):"

find . -type f -not -path '*/\.*' -not -path '*/__pycache__/*' -exec ls -lt {} + | head -5

echo ""

  

echo "=== END SNAPSHOT ==="
	```


---


### Short sequence to capture essence of TILBLOG code

# Just the tree structure
tree -I '.git|__pycache__|*.pyc|node_modules'

# List Python files with line counts (helps prioritize)
find . -name "*.py" | xargs wc -l | sort -n

# Show just til_deploy.py and the files it imports/executes
cat til_deploy.py

# Quick way to show specific files Claude requests
cat file1.py file2.py file3.py

---
After repeated Claude improvements, I'll clean up the repository, then reduce it to the minimum required for deployment as a cloned site. Then, I'll tune it so that it can be deployed on an existing Obsidian vault.   Zsolt's would be ideal. 

Deciding what should be in the template deployable site. It should include the new elements: speech, multi-lingual, drawing, gesture.


---
