#!/bin/bash
# kioku プロアクティブ通知スクリプト
#
# ローカル検索（memory エンジン）で新規 inbox と既存ノートの関連を検出し、
# Telegram Bot API で直接通知する。Claude API は使用しない。
#
# ガバナンス付き完全版は docs/notification-policy-v1.md を参照。
# 設計方針は docs/memory-design-v2.md を参照。
set -euo pipefail

KIOKU=~/Claude/kioku
MARKER="$KIOKU/.last-inbox-check"
LOG="$KIOKU/logs/proactive-check.log"
MEMORY_PYTHON="$KIOKU/memory/.venv/bin/python"
MEMORY_DB="$KIOKU/memory/data/kioku.db"
TELEGRAM_ENV="$HOME/.claude/channels/telegram/.env"

# 通知ポリシー
MIN_MATCHES=2  # 通知する最小関連ノート件数

mkdir -p "$KIOKU/logs"

# --- 新規 inbox ファイルの検出（マーカーファイル方式）---

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

# --- memory エンジンによるローカル検索 ---

if [ ! -f "$MEMORY_DB" ] || [ ! -f "$MEMORY_PYTHON" ]; then
  echo "$(date): memory 未セットアップ、スキップ" >> "$LOG"
  exit 0
fi

cd "$KIOKU"

# 各新規ファイルからクエリを生成して検索
NOTIFY_TITLES=""
NOTIFY_COUNT=0

while IFS= read -r NEW_FILE; do
  [ -z "$NEW_FILE" ] && continue

  # YAML フロントマターを除去し、本文先頭500バイトをクエリにする
  QUERY=$(sed '/^---$/,/^---$/d' "$NEW_FILE" | head -c 500)

  if [ -z "$QUERY" ]; then
    echo "$(date): empty query from $NEW_FILE, skipping" >> "$LOG"
    continue
  fi

  # memory search を実行（JSON 出力）
  RESULT=$("$MEMORY_PYTHON" -m memory.cli search --query "$QUERY" --limit 5 --json 2>> "$LOG") || {
    echo "$(date): memory search failed for $NEW_FILE" >> "$LOG"
    continue
  }

  # 結果件数を取得
  COUNT=$(echo "$RESULT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

  echo "$(date): $NEW_FILE → $COUNT 件の関連ノート" >> "$LOG"

  if [ "$COUNT" -ge "$MIN_MATCHES" ]; then
    # タイトルを抽出（通知用、本文は含めない）
    TITLES=$(echo "$RESULT" | python3 -c "
import sys, json
results = json.load(sys.stdin)
for r in results[:3]:
    print(f\"  - {r['title']} ({r['source_path']})\")
" 2>/dev/null || echo "")

    if [ -n "$TITLES" ]; then
      NOTIFY_TITLES="${NOTIFY_TITLES}${TITLES}
"
      NOTIFY_COUNT=$((NOTIFY_COUNT + 1))
    fi
  fi
done <<< "$NEW_FILES"

# --- Telegram Bot API 直接通知 ---

if [ "$NOTIFY_COUNT" -eq 0 ]; then
  echo "$(date): no matches above threshold, skipping notification" >> "$LOG"
  exit 0
fi

# Telegram 環境変数の読み込み
if [ ! -f "$TELEGRAM_ENV" ]; then
  echo "$(date): Telegram 環境変数なし ($TELEGRAM_ENV)、通知スキップ" >> "$LOG"
  echo "$(date): 通知内容（ログ記録のみ）:" >> "$LOG"
  echo "$NOTIFY_TITLES" >> "$LOG"
  exit 0
fi

# shellcheck source=/dev/null
source "$TELEGRAM_ENV"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "$(date): TELEGRAM_BOT_TOKEN または TELEGRAM_CHAT_ID が未設定、通知スキップ" >> "$LOG"
  echo "$(date): 設定方法は docs/setup-v1.md の Phase 4 を参照してください" >> "$LOG"
  echo "$(date): 通知内容（ログ記録のみ）:" >> "$LOG"
  echo "$NOTIFY_TITLES" >> "$LOG"
  exit 0
fi

# メッセージ組み立て
MSG="[kioku] 新しいメモに関連するノートがあります:
${NOTIFY_TITLES}"

# Bot API で送信
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MSG}" 2>> "$LOG") || true

if [ "$HTTP_CODE" = "200" ]; then
  echo "$(date): Telegram 通知送信成功" >> "$LOG"
else
  echo "$(date): Telegram 通知送信失敗 (HTTP $HTTP_CODE)" >> "$LOG"
fi
