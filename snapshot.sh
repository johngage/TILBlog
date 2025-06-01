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