#!/bin/bash
# ガバナンス付き完全版は docs/notification-policy-v1.md を参照してください。
# このファイルは setup-v1.md Phase 5-1 の「基本版」に
# security-v1.md / notification-policy-v1.md のプライバシー要件を追加したものです。
set -euo pipefail

KIOKU=~/Claude/kioku
MARKER="$KIOKU/.last-inbox-check"
LOG="$KIOKU/logs/proactive-check.log"

mkdir -p "$KIOKU/logs"

CURRENT=$(find "$KIOKU/inbox" -name "*.md" -not -name ".gitkeep" 2>/dev/null | sort)

if [ -z "$CURRENT" ]; then
  echo "$(date): inbox is empty, skipping" >> "$LOG"
  exit 0
fi

if [ ! -f "$MARKER" ]; then
  echo "$CURRENT" > "$MARKER"
  echo "$(date): first run, marker initialized" >> "$LOG"
  exit 0
fi

PREV=$(cat "$MARKER")
NEW_FILES=$(comm -23 <(echo "$CURRENT") <(echo "$PREV") || true)
echo "$CURRENT" > "$MARKER"

if [ -z "$NEW_FILES" ]; then
  echo "$(date): no new inbox files" >> "$LOG"
  exit 0
fi

echo "$(date): new inbox files: $NEW_FILES" >> "$LOG"

cd "$KIOKU"
claude -p "
inbox/ に以下の新しいファイルが追加されました：
${NEW_FILES}

notes/ から意味的に関連するコンテンツを検索してください。
関連するノートが 2 件以上あれば Telegram に送信：
「[kioku] 新しいメモが関連している可能性：[ノートタイトル]」

【除外ルール】
- #private / #nopush / #draft タグが付いたノートは検索対象から除外すること。
- secrets/ ディレクトリ以下のファイルは一切参照しないこと。

【通知に含めてよい情報】
- ノートのタイトル
- ノートの保存パス
- 関連と判断したキーワード（短い理由）

【通知に含めてはいけない情報】
- ノートの本文・全文
- クライアント名・会社名・固有名詞（ノート内の記載）
- 金額・取引情報
- パスワード・トークン・API キー・認証情報

関連するものがなければ何もしないこと。
" \
  --allowedTools "Read,Glob,Grep,Bash(telegram:*)" \
  --max-budget-usd 0.10 \
  --max-turns 5 >> "$LOG" 2>&1
