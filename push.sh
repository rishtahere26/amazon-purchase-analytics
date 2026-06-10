#!/bin/bash
# Publish to GitHub (github.com/rishtahere26/amazon-purchase-analytics).
# The repo contains ONLY code + synthetic demo data; real data is gitignored.
# Requirements: git + GitHub CLI (`brew install gh`), then `gh auth login`.
set -e
cd "$(dirname "$0")"

REPO_NAME="amazon-purchase-analytics"
VISIBILITY="${1:-private}"   # ./push.sh public  -> public repo + live Pages demo

if ! command -v gh &> /dev/null; then
  echo "GitHub CLI not found. Install with: brew install gh && gh auth login"
  exit 1
fi

[ -d .git ] || git init -b main
git add README.md Makefile .gitignore push.sh etl sql analytics web docs
git commit -m "Amazon purchase analytics: ETL -> SQLite -> dashboard" || echo "Nothing new to commit."

if ! gh repo view "$REPO_NAME" &> /dev/null; then
  gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --push
else
  git remote get-url origin &> /dev/null || git remote add origin "https://github.com/rishtahere26/$REPO_NAME.git"
  git push -u origin main
fi

# GitHub Pages from /docs (live demo works once repo is public)
gh api -X POST "repos/rishtahere26/$REPO_NAME/pages" \
  -f "source[branch]=main" -f "source[path]=/docs" 2>/dev/null \
  && echo "Pages enabled: https://rishtahere26.github.io/$REPO_NAME/" \
  || echo "Pages note: serves only when the repo is public (or on a paid plan).
  Flip with: gh repo edit rishtahere26/$REPO_NAME --visibility public --accept-visibility-change-consequences"

echo "Done -> https://github.com/rishtahere26/$REPO_NAME"
