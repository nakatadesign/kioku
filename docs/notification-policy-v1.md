# kioku — 通知ポリシー v1

プロアクティブ通知はkiokuの差別化の核心です。  
しかし「送りすぎる」ことで「うるさいシステム」に反転するリスクも持ちます。  
このドキュメントは通知のガバナンス・調整方法・ログ運用を定義します。

---

## 通知ガバナンスの原則

### 1. 量の制御

| ルール | デフォルト値 | 設定箇所 |
|---|---|---|
| 1日の最大通知件数 | 3件 | `scripts/proactive-check.sh` の `MAX_DAILY` |
| 同一ノートへの再通知禁止期間 | 24時間 | `.last-notified` マーカー |
| 通知の最小関連件数 | 2件以上 | `scripts/proactive-check.sh` の `MIN_MATCHES` |
| 静音時間 | 22:00〜07:00 | `scripts/proactive-check.sh` の `QUIET_START`/`QUIET_END` |

### 2. 質の制御

通知に含めてよい情報：
- ノートのタイトル
- ノートの保存パス
- 関連と判断した理由（キーワード）

通知に含めてはいけない情報（プライバシー保護）：
- ノートの本文・全文
- タスクの具体的な金額・クライアント名
- `#private` タグが付いたノートの内容
- `secrets/` ディレクトリ以下の内容

---

## 調整可能なパラメータ

`scripts/proactive-check.sh` の冒頭に設定値をまとめます。  
ここを変えるだけで通知の挙動が変わります。

```bash
# ===== 通知ポリシー設定 =====
MAX_DAILY=3          # 1日の最大通知件数（0で無効化）
MIN_MATCHES=2        # 通知する最小関連ノート件数
QUIET_START=22       # 静音開始時刻（時）
QUIET_END=7          # 静音終了時刻（時）
EXCLUDE_TAGS="#private #nopush #draft"  # 通知対象外タグ
NOTIFY_COOLDOWN=86400  # 同一ノート再通知禁止秒数（デフォルト24時間）
# ===========================
```

---

## `scripts/proactive-check.sh`（ガバナンス付き完全版）

```bash
#!/bin/bash
set -euo pipefail

KIOKU=~/Claude/kioku
MARKER="$KIOKU/.last-inbox-check"
NOTIFIED_LOG="$KIOKU/.last-notified"
DAILY_COUNT_FILE="$KIOKU/.daily-notify-count"
LOG="$KIOKU/logs/proactive-check.log"
PROACTIVE_REPORT="$KIOKU/reports/proactive-$(date +%Y-%m-%d).md"

# ===== 通知ポリシー設定 =====
MAX_DAILY=3
MIN_MATCHES=2
QUIET_START=22
QUIET_END=7
EXCLUDE_TAGS="#private #nopush #draft"
NOTIFY_COOLDOWN=86400
# ===========================

mkdir -p "$KIOKU/logs" "$KIOKU/reports"

# 静音時間チェック
CURRENT_HOUR=$(date +%H)
if [ "$CURRENT_HOUR" -ge "$QUIET_START" ] || [ "$CURRENT_HOUR" -lt "$QUIET_END" ]; then
  echo "$(date): quiet hours, skipping" >> "$LOG"
  exit 0
fi

# 1日の通知上限チェック
TODAY=$(date +%Y-%m-%d)
if [ -f "$DAILY_COUNT_FILE" ]; then
  FILE_DATE=$(head -1 "$DAILY_COUNT_FILE" | cut -d' ' -f1)
  FILE_COUNT=$(head -1 "$DAILY_COUNT_FILE" | cut -d' ' -f2)
  if [ "$FILE_DATE" = "$TODAY" ] && [ "$FILE_COUNT" -ge "$MAX_DAILY" ]; then
    echo "$(date): daily limit reached ($FILE_COUNT/$MAX_DAILY)" >> "$LOG"
    exit 0
  fi
fi

# 新しい inbox ファイルを検出（マーカーファイル方式）
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

# Claude に関連チェックを依頼（ガバナンスルール付き）
cd "$KIOKU"
RESULT=$(claude -p "
inbox/ に以下の新しいファイルが追加されました：
${NEW_FILES}

以下のルールで処理してください：

1. notes/ から意味的に関連するコンテンツを検索する
2. 除外タグ（${EXCLUDE_TAGS}）が付いたノートは検索対象から除外する
3. 関連するノートが ${MIN_MATCHES} 件以上ある場合のみ通知を検討する
4. 以下のJSON形式で結果を返してください：
{
  \"should_notify\": true/false,
  \"matched_notes\": [\"ノートタイトル1\", \"ノートタイトル2\"],
  \"reason\": \"関連と判断したキーワード・理由\",
  \"telegram_message\": \"送信するメッセージ（should_notifyがtrueの場合）\"
}

通知メッセージには本文・クライアント名・金額を含めないこと。
タイトルとパスと関連キーワードのみ。
" \
  --allowedTools "Read,Glob,Grep" \
  --max-budget-usd 0.10 \
  --max-turns 5 2>> "$LOG")

# JSON から結果を抽出
SHOULD_NOTIFY=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('should_notify','false'))" 2>/dev/null || echo "false")
MATCHED_NOTES=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(d.get('matched_notes',[])))" 2>/dev/null || echo "")
REASON=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reason',''))" 2>/dev/null || echo "")
TELEGRAM_MSG=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('telegram_message',''))" 2>/dev/null || echo "")

# 24時間以内に同じノートを通知していないか確認
if [ "$SHOULD_NOTIFY" = "True" ] || [ "$SHOULD_NOTIFY" = "true" ]; then
  ALREADY_SENT=false
  if [ -f "$NOTIFIED_LOG" ] && [ -n "$MATCHED_NOTES" ]; then
    CUTOFF=$(date -v-${NOTIFY_COOLDOWN}S +%s 2>/dev/null || date -d "${NOTIFY_COOLDOWN} seconds ago" +%s 2>/dev/null || echo "0")
    while IFS='|' read -r TS NOTE; do
      if [ "$TS" -gt "$CUTOFF" ]; then
        for MATCHED in $(echo "$MATCHED_NOTES" | tr ',' '\n'); do
          if echo "$NOTE" | grep -qF "$(echo $MATCHED | xargs)"; then
            ALREADY_SENT=true
            break 2
          fi
        done
      fi
    done < "$NOTIFIED_LOG"
  fi

  if [ "$ALREADY_SENT" = "true" ]; then
    echo "$(date): already notified about these notes recently, skipping" >> "$LOG"
    exit 0
  fi

  # Telegram に送信
  if [ -n "$TELEGRAM_MSG" ]; then
    claude -p "Telegram に以下のメッセージを送信してください：${TELEGRAM_MSG}" \
      --allowedTools "Bash(telegram:*)" \
      --max-budget-usd 0.05 \
      --max-turns 2 >> "$LOG" 2>&1

    # 通知済みログに記録
    echo "$(date +%s)|${MATCHED_NOTES}" >> "$NOTIFIED_LOG"

    # 1日の通知カウントを更新
    if [ -f "$DAILY_COUNT_FILE" ] && [ "$(head -1 "$DAILY_COUNT_FILE" | cut -d' ' -f1)" = "$TODAY" ]; then
      COUNT=$(head -1 "$DAILY_COUNT_FILE" | cut -d' ' -f2)
      echo "$TODAY $((COUNT + 1))" > "$DAILY_COUNT_FILE"
    else
      echo "$TODAY 1" > "$DAILY_COUNT_FILE"
    fi

    # プロアクティブログに記録
    {
      echo "## $(date +%H:%M) — 通知送信"
      echo ""
      echo "- 新規 inbox：$(echo "$NEW_FILES" | tr '\n' ',' | sed 's/,$//')"
      echo "- 関連ノート：${MATCHED_NOTES}"
      echo "- 判断理由：${REASON}"
      echo "- 送信メッセージ：${TELEGRAM_MSG}"
      echo ""
    } >> "$PROACTIVE_REPORT"

    echo "$(date): notification sent" >> "$LOG"
  fi
else
  echo "$(date): no relevant matches, skipping notification" >> "$LOG"
fi
```

---

## プロアクティブログの読み方

### 生成場所

```
reports/proactive-YYYY-MM-DD.md
```

通知を送った日にのみ生成されます。通知がない日はファイルが作られません。

### 内容の例

```markdown
## 09:42 — 通知送信

- 新規 inbox：inbox/2026-03-23-ideas.md
- 関連ノート：notes/ideas/2026-02-14-ebay-automation.md, notes/projects/clabotch.md
- 判断理由：キーワード「自動化」「Claude Code」が一致
- 送信メッセージ：[kioku] 新しいメモが関連している可能性：eBay自動化メモ, clabotchプロジェクト
```

### 誤通知のチューニング方法

1. `reports/proactive-YYYY-MM-DD.md` を開く
2. 誤通知だった場合：判断理由を確認
3. 除外したいキーワードが共通していれば `EXCLUDE_TAGS` に追加
4. 通知が多すぎる場合：`MIN_MATCHES` を 3 に増やす
5. 通知が少なすぎる場合：`MIN_MATCHES` を 1 に減らす

---

## gitignore に追加

```gitignore
# 通知制御用ローカルファイル
.last-notified
.daily-notify-count
```

---

## 通知に含めない情報（プライバシー）

Telegram はサードパーティサービスです。通知メッセージに以下を含めてはいけません：

- ノートの本文・全文
- クライアント名・会社名
- 金額・取引情報
- `#private` タグが付いたノートの内容
- パスワード・トークン・API キー（当然）

ノートにセンシティブな内容が含まれる場合は `#private` タグを付けてください。  
proactive-check は除外タグとして処理し、通知対象から外します。

---

## Channels API 変更への備え

Channels は 2026年3月時点で Research Preview です。  
API・プラグイン仕様が変更される可能性があります。

対応方針：
- Telegram 送信部分は `claude -p "... Telegram に送信してください"` という抽象的な指示にする
- プラグイン名（`telegram@claude-plugins-official`）が変わった場合は起動コマンドを更新するだけ
- 最悪 Channels が廃止された場合：`proactive-check.sh` の送信部分を  
  curl + Telegram Bot API に差し替えれば同じ運用を継続できる

```bash
# Channels 廃止時のフォールバック（Bot API 直接呼び出し）
# TELEGRAM_BOT_TOKEN は ~/.claude/channels/telegram/.env から読む
source ~/.claude/channels/telegram/.env
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${YOUR_CHAT_ID}" \
  -d "text=${TELEGRAM_MSG}" > /dev/null
```

---

*ドキュメントバージョン：v1 — 2026-03-23*
