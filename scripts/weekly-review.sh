#!/bin/bash
set -euo pipefail
KIOKU=~/Claude/kioku
WEEK=$(date +%Y-W%V)
cd "$KIOKU"
echo "=== $(date) weekly-review start ==="
git pull --rebase origin main 2>/dev/null || true

claude -p "
notes/ と reports/ の全ファイルを読んでください。
各ノートを HIGH/MEDIUM/LOW でスコアリング（構造的情報密度）。
上位 3 件と 30 日以上経過した LOW ノートを reports/weekly-${WEEK}.md に出力。
Telegram サマリーを送信してください。
" \
  --allowedTools "Read,Glob,Write,Bash(telegram:*)" \
  --max-budget-usd 1.00

git add -A
git diff-index --quiet HEAD || \
  git commit -m "auto: 週次レビュー ${WEEK}"
git push origin main 2>/dev/null || true
echo "=== $(date) weekly-review end ==="
