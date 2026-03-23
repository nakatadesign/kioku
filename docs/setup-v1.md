# kioku — セットアップガイド v1

---

## 前提条件

| 要件 | 確認方法 | 用途 |
|---|---|---|
| Claude Code v2.1.80 以上 | `claude --version` | メインセッション |
| Bun インストール済み | `bun --version` | Channels プラグインの実行環境（必須） |
| Git 設定済み | `git config user.email` | バージョン管理 |
| GitHub CLI 認証済み | `gh auth status` | リポジトリ作成 |
| Telegram アカウント | — | Channels 接続 |

> **Bun について：** Telegram Channels プラグイン（`telegram@claude-plugins-official`）は  
> Bun で動作します。kioku のシェルスクリプト自体は Bun を使いませんが、  
> `--channels` フラグでプラグインを読み込む際に Bun がなければ起動できません。

---

## Phase 1：リポジトリ作成（Day 1・約 15 分）

### 1-1. GitHub リポジトリ作成

> **Note:** `nakatadesign/kioku` は例です。自分の GitHub ユーザー名とリポ名に置き換えてください。個人インスタンスは `--private` を推奨します。

```bash
gh repo create YOUR_GH_USER/kioku \
  --private \
  --description "Personal knowledge layer for Claude Code" \
  --clone

cd ~/Claude/kioku
```

### 1-2. ディレクトリ構造の初期化

```bash
mkdir -p .claude/commands
mkdir -p inbox daily \
  notes/{ideas,tasks,projects,research} \
  reports scripts .launchd docs logs

# Git に空ディレクトリを含めるための .gitkeep
touch inbox/.gitkeep daily/.gitkeep \
  notes/ideas/.gitkeep notes/tasks/.gitkeep \
  notes/projects/.gitkeep notes/research/.gitkeep \
  reports/.gitkeep logs/.gitkeep
```

### 1-3. `.gitignore` の作成

```bash
cat > .gitignore << 'EOF'
# Telegram bot トークン
.claude/channels/telegram/.env
.env
*.env

# トークンファイル類
*.token
*.key
secrets/
.secrets/

# macOS
.DS_Store

# 一時ファイル
*.tmp
*.bak

# ローカル専用ファイル（通知制御・マーカー）
.last-inbox-check
.last-notified
.daily-notify-count
EOF
```

### 1-4. 初回コミット

```bash
git add -A
git commit -m "init: kioku v1"
git push origin main
```

---

## Phase 2：CLAUDE.md（Day 1・約 20 分）

リポジトリルートに `CLAUDE.md` を作成します。

```markdown
# kioku

個人ナレッジ層。蓄積 → 整理 → 引き出す。能動的に。

## 役割

このリポジトリはナレッジストアです。Claude Code はここでナレッジ司書として動作します。
入力をキャプチャし、ノートを整理し、関連するコンテキストを Telegram 経由で能動的に通知します。

## 入力口

- Mac ターミナル：Claude Code 直接操作（メイン）
- iPhone：Telegram → Channels プラグイン（同じセッション）
- Claude Desktop：GitHub コネクター（別セッション・同じリポジトリ）

## ナレッジフローの原則

**すべての入力はまず inbox/ に入る。** トリガーワードが notes/ に直接書くことはない。
notes/ への移動は /project:process コマンドが担う。

## トリガーワード

| プレフィックス | inbox への書き込み先 | 備考 |
|---|---|---|
| `idea: ...` | inbox/YYYY-MM-DD-ideas.md に追記 | |
| `task: ...` | inbox/YYYY-MM-DD-tasks.md に追記 | |
| `log: ...` | inbox/YYYY-MM-DD-log.md に追記 | |
| `research: ...` | inbox/YYYY-MM-DD-research.md に追記 | |
| `save` または `push` | — | git add + commit + push を実行 |
| `status` | — | git status + 今日の inbox を表示 |
| `process` | — | /project:process を実行 |

## Git コミットルール

- PostToolUse（Write/Edit）：git add -A のみ（コミットしない）
- Stop（セッション終了）：git commit -m "auto: session HH:MM"
- `save` / `push` トリガー：git commit && git push
- スケジュールスクリプト：git commit && git push

## チャネル別の動作

Telegram 経由の場合：
- レスポンスは 3 行以内
- 絵文字でステータス表示：✅ 保存済み、📝 メモ済み、❌ エラー
- 書き込み後は commit + push（push まで実行する）
- 破壊的操作は停止して Telegram に確認メッセージを送ること

ターミナル経由の場合：
- コミット前に差分を表示
- `save` / `push` トリガーまたは明示的な指示があった場合のみ push

Claude Desktop 経由の場合（別セッション）：
- 書き込み前に必ず git pull --rebase origin main を実行
- inbox/ にのみ書き込む（notes/ や daily/ に直接書かない）
- 書き込み後すぐに git commit && git push

## ハードセーフティルール

- 絶対に実行しない：git push --force
- 絶対に実行しない：任意のディレクトリへの rm -rf
- ~/Claude/kioku 以外のディレクトリへの書き込みは確認を取ること
- .claude/settings.json の allowedTools 以外のコマンドは実行しない
- 破壊的操作：コマンドを Telegram に返信して「確認」を待ってから実行

## コンテキスト供給

このリポジトリは他の Claude Code セッションで --add-dir コンテキストとしても使用されます。
notes/ と daily/ がメインのコンテキストディレクトリです。
notes/ のエントリは簡潔で自己完結させること。
```

---

## Phase 3：フック設定（Day 1・約 15 分）

### 3-1. `.claude/settings.json` の作成

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

## Phase 4：Telegram Channels（Day 1・約 10 分）

### 4-1. Bun のインストール確認

```bash
bun --version
# 未インストールの場合：
curl -fsSL https://bun.sh/install | bash
```

### 4-2. Telegram bot の作成

1. Telegram を開く → `@BotFather` を検索
2. `/newbot` を送信
3. 表示名を設定（例：`Nakata Kioku`）
4. `bot` で終わるユーザー名を設定（例：`nakata_kioku_bot`）
5. トークンをコピー

### 4-3. トークンを保存

```bash
mkdir -p ~/.claude/channels/telegram
echo "TELEGRAM_BOT_TOKEN=your_token_here" > ~/.claude/channels/telegram/.env
# your_token_here を実際のトークンに置き換える
```

### 4-4. プラグインのインストール

```bash
cd ~/Claude/kioku
claude
# セッション内で：
/plugin install telegram@claude-plugins-official
exit
```

### 4-5. Channels 付きで起動

```bash
cd ~/Claude/kioku
claude --channels plugin:telegram@claude-plugins-official \
       --dangerously-skip-permissions
```

### 4-6. ペアリングと allowlist 設定

1. Telegram を開く → 自分の bot に DM → `hello` を送信
2. bot から 6 文字のペアリングコードが返ってくる
3. Claude Code セッションにコードを入力
4. **すぐに実行**：`/telegram:access policy allowlist`
5. 確認：`/telegram:access list`（自分の ID のみ表示されること）

iPhone からテスト：
```
idea: kioku のセットアップが完了しました
```
期待されるレスポンス：`✅ 保存済み`

---

## Phase 5：スクリプト作成（Day 2・約 30 分）

### 5-1. `scripts/proactive-check.sh`

基本版です。通知のガバナンス（上限・静音・冷却期間）が必要になったら  
`docs/notification-policy-v1.md` の完全版に差し替えてください。

```bash
#!/bin/bash
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
#private タグが付いたノートは除外してください。
通知にはタイトルとパスのみ含め、本文は含めないこと。
関連するものがなければ何もしないこと。
" \
  --allowedTools "Read,Glob,Grep,Bash(telegram:*)" \
  --max-budget-usd 0.10 \
  --max-turns 5 >> "$LOG" 2>&1
```

```bash
chmod +x scripts/proactive-check.sh
```

### 5-2. `scripts/daily-summary.sh`

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
```

```bash
chmod +x scripts/daily-summary.sh
```

### 5-3. `scripts/weekly-review.sh`

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
```

```bash
chmod +x scripts/weekly-review.sh
```

### 5-4. launchd エージェントの作成と登録

`.launchd/daily.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
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

登録：

```bash
cp .launchd/daily.plist ~/Library/LaunchAgents/com.nakata.kioku.daily.plist
cp .launchd/weekly.plist ~/Library/LaunchAgents/com.nakata.kioku.weekly.plist
launchctl load ~/Library/LaunchAgents/com.nakata.kioku.daily.plist
launchctl load ~/Library/LaunchAgents/com.nakata.kioku.weekly.plist

# 確認
launchctl list | grep kioku
```

---

## 動作確認チェックリスト

**Phase 1-2**
- [ ] `gh repo view YOUR_GH_USER/kioku --json visibility -q '.visibility'` → `PRIVATE`
- [ ] `.gitignore` に `.last-inbox-check`・`.last-notified`・`.daily-notify-count` が含まれている
- [ ] CLAUDE.md のトリガーワード表が `inbox/` への書き込みになっている

**Phase 3**
- [ ] `.claude/settings.json` の PostToolUse が `git add -A` のみ（commit なし）
- [ ] テスト：ファイルを編集 → `git status` でステージングされること
- [ ] テスト：セッション終了 → `git log --oneline -1` で `auto: session` コミットが出ること

**Phase 4**
- [ ] `bun --version` が返ってくる
- [ ] Telegram bot が DM に応答する
- [ ] `/telegram:access list` に自分の ID のみ表示される
- [ ] iPhone テスト：`idea: テスト` → ✅ を受信 → `inbox/` にファイルが作成されている

**Phase 5**
- [ ] `launchctl list | grep kioku` で 2 件表示される
- [ ] 手動テスト：`bash scripts/daily-summary.sh` → Telegram にブリーフが届く
- [ ] 手動テスト：`bash scripts/proactive-check.sh` → `logs/proactive-check.log` が生成される
- [ ] 手動テスト：`bash scripts/weekly-review.sh` → `reports/` にファイルが作成される

---

## 日常的な使い方

```
朝（iPhone・移動中）
  Telegram → "idea: [思いついたこと]"
  → ✅ 保存済み（inbox/ に追記）
  09:00 に朝のブリーフが Telegram に届く

昼（Mac ターミナル）
  他のプロジェクトで Claude Code を使って作業
  kioku をコンテキストとして追加する場合：
    claude --add-dir ~/Claude/kioku/notes --add-dir ~/Claude/kioku/daily
  inbox を整理したいとき：
    /project:process

夕方（ターミナル）
  Telegram → "status"
  → 今日の inbox アイテム + git サマリー

自動
  セッション終了後 → proactive-check（関連ノートがあれば Telegram メンション）
  毎日 09:00 → 日次ブリーフ（Telegram）
  毎週日曜 10:00 → 週次レビュー + Epiplexity スコアリング（Telegram + reports/）
```

---

*ドキュメントバージョン：v1 — 2026-03-23*
