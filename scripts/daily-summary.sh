#!/bin/bash
set -euo pipefail
KIOKU=~/Claude/kioku
cd "$KIOKU"
echo "=== $(date) daily-summary start ==="
git pull --rebase origin main 2>/dev/null || true

claude -p "
inbox/ と daily/$(date +%Y-%m-%d).md（存在する場合）を読んでください。
日本語で朝のブリーフを生成してください（3〜5 箇条書き）：
未処理の inbox アイテム・今日の関連ノート・進行中のタスク。
結果を Telegram に送信してください。簡潔に。
" \
  --allowedTools "Read,Glob,Grep,Bash(telegram:*)" \
  --max-budget-usd 0.30

git add -A
git diff-index --quiet HEAD || \
  git commit -m "auto: 日次ブリーフ $(date +%Y-%m-%d)"
git push origin main 2>/dev/null || true
echo "=== $(date) daily-summary end ==="
