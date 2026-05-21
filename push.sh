#!/bin/bash
# StockForge auto-push helper
# Usage: ./push.sh "Description of changes"
# Or:    ./push.sh  (auto-generates message from git diff)

cd /root/StockForge

MESSAGE="${1:-}"
if [ -z "$MESSAGE" ]; then
    CHANGES=$(git diff --stat HEAD 2>/dev/null | tail -1)
    FILES=$(git diff --name-only HEAD 2>/dev/null | head -5 | tr '\n' ', ')
    MESSAGE="StockForge update: ${FILES:-no changes}"
fi

git add -A
git diff --cached --quiet || {
    git commit -m "$MESSAGE"
    git push origin main
    echo "✅ Pushed to kishoreHQ/StockForge"
} || echo "⚠️ Nothing to commit or push failed"
