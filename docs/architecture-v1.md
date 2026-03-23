# kioku — アーキテクチャ v1

---

## システム全体図

```
入力層
─────────────────────────────────────────────────────────────
  PC（Mac ターミナル）       スマートフォン（Telegram）
  Claude Code 直接操作       Channels プラグイン
       │                        │
       └────────────────────────┘
                     │
コア層               ▼
─────────────────────────────────────────────────────────────
          Claude Code セッション
          --channels plugin:telegram
          --dangerously-skip-permissions
          WorkingDirectory: ~/Claude/kioku
                     │
          フック：    │
          PostToolUse → git add -A のみ（コミットしない）
          Stop       → git commit + proactive-check
                     │
保存層               ▼
─────────────────────────────────────────────────────────────
                  your-username/kioku（GitHub Private）
                  ├── inbox/   ← すべての入力の正規入口
                  ├── daily/
                  ├── notes/
                  └── reports/

出力層
─────────────────────────────────────────────────────────────
  launchd + claude -p        Epiplexity 評価      --add-dir
  日次・週次サマリー自動生成    知識品質スコアリング    他CCセッションへ供給
         │                         │
         └─────────────────────────┘
                     │
             Telegram プロアクティブ通知
             定期トリガー ＋ 文脈トリガー
```

---

## フック定義

### `.claude/settings.json`

コミット戦略のポリシー：
- **PostToolUse**：`git add -A` のみ（ステージング）。コミットしない
- **Stop**：`git commit`（セッション終了時に1回だけコミット）＋ proactive-check 起動
- **SessionStart**：`git pull --rebase`（常に最新を取得してから始める）

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "cd ~/Claude/kioku && git add -A 2>/dev/null || true"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd ~/Claude/kioku && git pull --rebase origin main 2>/dev/null || true"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd ~/Claude/kioku && git add -A && git diff-index --quiet HEAD || git commit -m \"auto: session $(date +%H:%M)\" 2>/dev/null || true"
          }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/Claude/kioku/scripts/proactive-check.sh >> ~/Claude/kioku/logs/proactive-check.log 2>&1 || true"
          }
        ]
      }
    ]
  }
}
```

---

## ナレッジフロー詳細

### inbox → notes の二段構え

```
1. トリガーワード受信
   → inbox/YYYY-MM-DD-[種別].md に追記（自動）
   → git add -A（PostToolUse フック）

2. セッション終了
   → git commit -m "auto: session HH:MM"（Stop フック）
   → proactive-check.sh 起動

3. /project:process 実行（手動またはスケジュール）
   → inbox/ の各ファイルを読んで分類
   → notes/[種別]/ に移動・整理
   → inbox/ のファイルをアーカイブまたは削除
   → git commit -m "process: YYYY-MM-DD"
```

### `/project:process` コマンド定義（`.claude/commands/process.md`）

```markdown
---
description: inbox/ の未処理アイテムをすべて分類・移動する
allowed-tools: Read, Write, Glob, Bash(mv:*), Bash(git:*)
---
inbox/ 内の全 .md ファイルを処理する:
1. 各ファイルの内容を読んで種別を判定（ideas / tasks / research / log）
2. YAML フロントマターを付与（title, date, tags, type）
3. 適切なディレクトリに移動:
   - ideas → notes/ideas/YYYY-MM-DD-slug.md
   - tasks → notes/tasks/YYYY-MM-DD-slug.md
   - research → notes/research/YYYY-MM-DD-slug.md
   - log → daily/YYYY-MM-DD.md にマージ
4. 処理済みの inbox ファイルを削除
5. git commit -m "process: YYYY-MM-DD"
```

---

## proactive-check の設計（マーカーファイル方式）

### 問題点（旧方式）
`git diff HEAD~1..HEAD` は直近 1 コミットの差分しか見ない。  
連続コミット・squash・複数ファイルコミットが発生すると inbox の取りこぼしやノイズが生じる。

### 解決策（マーカーファイル方式）
チェック済みファイルのリストを `.last-inbox-check` に記録し、  
「前回チェック以降に増えた inbox ファイル」を特定する。

### `scripts/proactive-check.sh`

```bash
#!/bin/bash
set -euo pipefail

KIOKU=~/Claude/kioku
MARKER="$KIOKU/.last-inbox-check"
LOG="$KIOKU/logs/proactive-check.log"

mkdir -p "$KIOKU/logs"

# 現在の inbox ファイル一覧を取得
CURRENT=$(find "$KIOKU/inbox" -name "*.md" -not -name ".gitkeep" 2>/dev/null | sort)

if [ -z "$CURRENT" ]; then
  echo "$(date): inbox is empty, skipping" >> "$LOG"
  exit 0
fi

# マーカーファイルがなければ初回実行として全ファイルを記録して終了
if [ ! -f "$MARKER" ]; then
  echo "$CURRENT" > "$MARKER"
  echo "$(date): first run, marker initialized" >> "$LOG"
  exit 0
fi

# 前回チェック以降に増えたファイルを特定
PREV=$(cat "$MARKER")
NEW_FILES=$(comm -23 <(echo "$CURRENT") <(echo "$PREV"))

# マーカーを更新
echo "$CURRENT" > "$MARKER"

if [ -z "$NEW_FILES" ]; then
  echo "$(date): no new inbox files" >> "$LOG"
  exit 0
fi

echo "$(date): new inbox files: $NEW_FILES" >> "$LOG"

# Claude に関連チェックを依頼
cd "$KIOKU"
claude -p "
inbox/ に以下の新しいファイルが追加されました：
${NEW_FILES}

notes/ から意味的に関連するコンテンツを検索してください（キーワード一致で十分）。
関連するノートが 2 件以上あれば Telegram にこのメッセージを送信してください：
「[kioku] 新しいメモが関連している可能性：[ノートタイトル]」
関連するものがなければ、静かに終了してください（何も送らない）。
" \
  --allowedTools "Read,Glob,Grep,Bash(telegram:*)" \
  --max-budget-usd 0.10 \
  --max-turns 5 >> "$LOG" 2>&1
```

---

## スケジュール自動化

### launchd plist — ログ出力付き

```xml
<!-- ~/Library/LaunchAgents/com.nakata.kioku.daily.plist -->
<plist version="1.0"><dict>
  <key>Label</key><string>com.nakata.kioku.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-l</string>
    <string>/Users/nakata/Claude/kioku/scripts/daily-summary.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/nakata/Claude/kioku</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/nakata/Claude/kioku/logs/daily-summary.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/nakata/Claude/kioku/logs/daily-summary.log</string>
  <key>RunAtLoad</key><false/>
  <key>KeepAlive</key><false/>
</dict></plist>
```

`-l` フラグ（ログインシェル）を付けることで PATH に claude コマンドが含まれる。  
週次も同じ構造に `<key>Weekday</key><integer>0</integer>` を追加。

### `scripts/daily-summary.sh`

```bash
#!/bin/bash
set -euo pipefail
KIOKU=~/Claude/kioku
cd "$KIOKU"

echo "=== $(date) daily-summary start ==="

git pull --rebase origin main 2>/dev/null || true

claude -p "
inbox/ と daily/$(date +%Y-%m-%d).md（存在する場合）を読んでください。
日本語で朝のブリーフを生成してください（3〜5 箇条書き）：
- 未処理の inbox アイテム
- 今日に関連する notes/ のノート 1〜2 件
- 進行中または期限が近いタスク
結果を Telegram に送信してください。簡潔に。
" \
  --allowedTools "Read,Glob,Grep,Bash(telegram:*)" \
  --max-budget-usd 0.30

git add -A
git diff-index --quiet HEAD || \
  git commit -m "auto: 日次ブリーフ $(date +%Y-%m-%d)"
git push origin main 2>/dev/null || true

echo "=== $(date) daily-summary end ==="
```

### `scripts/weekly-review.sh`

```bash
#!/bin/bash
set -euo pipefail
KIOKU=~/Claude/kioku
WEEK=$(date +%Y-W%V)
cd "$KIOKU"

echo "=== $(date) weekly-review start ==="

git pull --rebase origin main 2>/dev/null || true

claude -p "
notes/ と reports/ の全ファイルを読んでください。
1. 各ノートを構造的情報密度で HIGH/MEDIUM/LOW にスコアリング
   （HIGH = 再利用可能な洞察・汎化できるもの、LOW = 一回限り・時間依存）
2. HIGH ノートの上位 3 件をリスト化
3. 30 日以上経過した LOW ノートをクリーンアップ候補としてフラグ
4. 結果を reports/weekly-${WEEK}.md に出力
5. Telegram サマリーを送信：上位 3 ノート ＋ クリーンアップ候補件数
" \
  --allowedTools "Read,Glob,Write,Bash(telegram:*)" \
  --max-budget-usd 1.00

git add -A
git diff-index --quiet HEAD || \
  git commit -m "auto: 週次レビュー ${WEEK}"
git push origin main 2>/dev/null || true

echo "=== $(date) weekly-review end ==="
```

---

---

## 他セッションへのコンテキスト供給（`--add-dir`）

他のプロジェクト（totonoe・clabotch 等）で作業するとき：

```bash
cd ~/Claude/totonoe
claude --add-dir ~/Claude/kioku/notes --add-dir ~/Claude/kioku/daily
```

- `notes/` と `daily/` を読み取り専用コンテキストとして追加
- kioku への書き込みは発生しない
- process コマンドも実行されない

---

## ログの確認

```bash
# 日次サマリーのログ
tail -f ~/Claude/kioku/logs/daily-summary.log

# 週次レビューのログ
tail -f ~/Claude/kioku/logs/weekly-review.log

# proactive-check のログ
tail -f ~/Claude/kioku/logs/proactive-check.log

# 全ログ一覧
ls -lth ~/Claude/kioku/logs/
```

---

*ドキュメントバージョン：v1 — 2026-03-23*
