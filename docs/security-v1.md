# kioku — セキュリティ v1

---

## リスク一覧

| リスク | 深刻度 | 対策状況 |
|---|---|---|
| Telegram bot への不正アクセス | **高** | allowlist ポリシーで対処 |
| `--dangerously-skip-permissions` の悪用 | **高** | 4層防御（allowlist・WorkingDirectory・CLAUDE.md・ログ）で対処 |
| リポジトリへの個人情報露出 | **中** | Private リポジトリで対処 |
| トークン・シークレットの Git 混入 | **中** | .gitignore で対処 |
| 通知経由のプライバシー漏洩 | **中** | 通知ポリシーで対処（本ドキュメント参照） |
| スケジュール自動化の暴走 | **低** | --max-budget-usd 制限で対処 |
| 無人操作の事後追跡不能 | **中** | 全スクリプトのログ出力で対処 |

---

## ルール 1：Telegram allowlist（最優先 — 最初にやること）

Channels のデフォルト pairing モードでは、ペアリングコードを入手した人が  
誰でも Claude Code セッションにアクセスできます。  
ペアリング後すぐに allowlist に切り替えます：

```
/telegram:access policy allowlist
```

確認：
```
/telegram:access list
```

自分の Telegram ユーザー ID だけが表示されているはずです。

**ペアリングコードは絶対に共有しないこと。** これは Claude Code セッションへのフルアクセス権です。

---

## ルール 2：個人インスタンスは必ず Private

> **注意：** kioku テンプレート本体（`nakatadesign/kioku`）の公開設定は配布方針に従います。以下の Private ルールは、テンプレートから作成した**個人運用用のリポジトリ**に適用されます。

個人インスタンスには個人のアイデア・プロジェクトログ・タスク・リサーチメモが含まれます。

```bash
gh repo view YOUR_GH_USER/YOUR_KIOKU_REPO --json visibility -q '.visibility'
# 個人インスタンスでは期待される出力：PRIVATE
```

---

## ルール 3：`.gitignore` — シークレットを絶対にコミットしない

```gitignore
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

# ローカル専用ファイル
.last-inbox-check
.last-notified
.daily-notify-count
```

Telegram bot トークンは `~/.claude/channels/telegram/.env` にのみ保存します。  
kioku リポジトリの外です。コミットされることはありません。

---

## ルール 4：`--dangerously-skip-permissions` の4層防御

単独の対策では不十分です。4層を組み合わせます：

| 防御層 | 設定 | 効果 |
|---|---|---|
| **allowlist** | `/telegram:access policy allowlist` | 自分以外からの指示を受け付けない |
| **WorkingDirectory** | launchd plist に設定 | 別ディレクトリへの意図しない操作を防ぐ |
| **CLAUDE.md 禁止事項** | ハードセーフティルール | エージェントの自制を促す |
| **ログ** | stdout/stderr をファイルに残す | 事後の追跡を可能にする |

launchd plist の設定：

```xml
<key>WorkingDirectory</key>
<string>/Users/nakata/Claude/kioku</string>
<key>StandardOutPath</key>
<string>/Users/nakata/Claude/kioku/logs/[スクリプト名].log</string>
<key>StandardErrorPath</key>
<string>/Users/nakata/Claude/kioku/logs/[スクリプト名].log</string>
```

ログの確認：

```bash
tail -f ~/Claude/kioku/logs/daily-summary.log
tail -f ~/Claude/kioku/logs/proactive-check.log
git -C ~/Claude/kioku log --oneline -10
```

CLAUDE.md に追記するハードセーフティルール：

```markdown
## ハードセーフティルール

- 絶対に実行しない：git push --force
- 絶対に実行しない：任意のディレクトリへの rm -rf
- ~/Claude/kioku 以外のディレクトリへの書き込みは確認を取ること
- 破壊的操作：コマンドを Telegram に返信して「確認」を待ってから実行
```

---

## ルール 5：通知に含めない情報（プライバシー）

Telegram はサードパーティサービスです。  
通知メッセージに含めてよい情報と、含めてはいけない情報を明確にします。

**含めてよい情報：**
- ノートのタイトル
- ノートの保存パス
- 関連と判断したキーワード

**含めてはいけない情報：**
- ノートの本文・全文
- クライアント名・会社名・固有名詞（ノート内）
- 金額・取引情報
- `#private` タグが付いたノートの内容
- パスワード・トークン・API キー

センシティブな内容のノートには `#private` タグを付けてください。  
proactive-check の除外タグ設定（`EXCLUDE_TAGS`）が対象から外します。

---

## ルール 6：スケジュール自動化のコスト上限

| スクリプト | 上限 |
|---|---|
| `daily-summary.sh` | `--max-budget-usd 0.30` |
| `weekly-review.sh` | `--max-budget-usd 1.00` |
| `proactive-check.sh` | `--max-budget-usd 0.10`（通知送信の追加呼び出しは `0.05`） |

---

## ルール 7：Claude Desktop からの書き込みルール

Claude Desktop は別セッションです。同じリポジトリを操作するため：

- 書き込み前に必ず `git pull --rebase origin main` を実行
- `inbox/` にのみ書き込む（`notes/` や `daily/` に直接書かない）
- 書き込み後すぐに `git commit && git push`

コンフリクトが発生した場合：`git rebase --continue` で解決します。  
inbox への追記は append-only のためコンフリクトはほぼ起きません。

---

## ルール 8：Mac mini M4 への移行時（将来）

- Tailscale 経由でのみアクセス可能（設定済み）
- Telegram Channels はポートを公開しない（Bot API ポーリング、アウトバウンドのみ）
- ログは Mac mini 上に残るため `ssh` して確認
- セキュリティモデルはそのまま維持されます

---

## セキュリティチェックリスト

**初回利用前：**

- [ ] GitHub リポジトリを **Private** で作成済み
- [ ] `.gitignore` に `.env`・`*.token`・`.last-inbox-check`・`.last-notified`・`.daily-notify-count` が含まれている
- [ ] Telegram bot トークンが `~/.claude/channels/telegram/.env` にのみ保存されている
- [ ] ペアリング後に `/telegram:access policy allowlist` を設定済み
- [ ] CLAUDE.md にハードセーフティルールを追記済み
- [ ] launchd plist に `WorkingDirectory`・`StandardOutPath`・`StandardErrorPath` を設定済み
- [ ] すべての `claude -p` 呼び出しに `--max-budget-usd` を設定済み
- [ ] `logs/` ディレクトリが存在する
- [ ] proactive-check の `EXCLUDE_TAGS` に `#private` が含まれている

**継続的な運用：**

- [ ] 週次でログファイルを確認（予期しない操作がないか）
- [ ] 月次で `reports/proactive-*.md` を確認（誤通知のチューニング）
- [ ] Telegram bot トークンを 90 日ごとに `/revoke` でローテーション
- [ ] 月次で `git log --oneline -20` を確認
- [ ] Telegram アプリの再インストール後に allowlist を再確認

---

*ドキュメントバージョン：v1 — 2026-03-23*
