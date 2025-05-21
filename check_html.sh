#!/bin/bash
# Check the content of HTML files in the build directory

echo "Checking index.html:"
echo "-----------------"
head -n 5 build/index.html
echo "..."
echo ""

echo "Checking a TIL entry:"
echo "-----------------"
head -n 5 build/til/sample-1.html
echo "..."
echo ""

echo "File types in build directory:"
echo "-----------------"
find build -type f | grep -v ".nojekyll" | xargs file | grep -v "HTML"
echo ""

echo "This will show any files that aren't recognized as HTML. If all is well, there should be nothing displayed above except for CSS/JS files."