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
