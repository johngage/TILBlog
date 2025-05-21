#!/bin/bash
# Simple script to build and publish TIL blog

echo "=========================================="
echo "  TIL Blog Publishing Script"
echo "=========================================="

# Change this to your actual database file
DATABASE_PATH = "til.db"



# Build the static site
echo "Building static site..."
python local_build.py

# Check if build succeeded
if [ $? -ne 0 ]; then
  echo "Error: Build script failed!"
  exit 1
fi

# Add changes to git
echo "Adding build directory to git..."
git add build

# Commit changes
echo "Committing changes..."
echo -n "Enter commit message (or press enter for default): "
read message

if [ -z "$message" ]; then
  message="Update static site $(date '+%Y-%m-%d %H:%M')"
fi

git commit -m "$message"

# Push to GitHub
echo "Pushing to GitHub..."
git push origin main

echo ""
echo "=========================================="
echo "  Deployment complete!"
echo "  Your site should be available at:"
echo "  https://YOUR_USERNAME.github.io/TILBlog/"
echo "=========================================="