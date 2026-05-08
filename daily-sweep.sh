#!/bin/bash
# Daily system maintenance - runs autonomously
set -e

echo "=== Daily Sweep $(date) ==="

# Clean caches
echo "Cleaning npm cache..."
npm cache clean --force 2>/dev/null || true

echo "Cleaning brew..."
brew cleanup -s 2>/dev/null || true

# Check disk
echo "Disk usage:"
df -h / | tail -1

# Check for dirty repos
echo "Dirty git repos:"
for d in ~/Workspace/*/; do
  [ -d "$d/.git" ] || continue
  if [ -n "$(git -C "$d" status --porcelain 2>/dev/null)" ]; then
    echo "  DIRTY: $d"
  fi
done

# Report outdated packages
echo "Outdated brew packages:"
brew outdated 2>/dev/null | head -5 || echo "  (none)"

echo "=== Done ==="
