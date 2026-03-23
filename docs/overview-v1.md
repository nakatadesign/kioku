# kioku — 概要 v1

> Claude Code のための個人ナレッジ管理テンプレート。  
> 蓄積 → 整理 → 引き出す。能動的に、安全に。

---

## kioku とは

**kioku（記憶）** は Git ベースの個人ナレッジリポジトリテンプレートです。  
PC とスマートフォンの入力を単一の情報源に集約し、必要になる前に関連する知識をプッシュ通知します。

ツールではありません。Claude Code が住むワーキングディレクトリです。

---

## 解決する問題

あるセッションで得た知識は、セッションが終わると消える。  
スマホでメモしたアイデアは、ワークフローに入ってこない。  
過去の関連する思考は埋もれたまま、同じことを考え直す。

kioku はナレッジを **永続的・持ち運び可能・能動的** にすることでこれを解決します。

---

## 他のPKMテンプレートとの違い

同種のプロジェクト（COG-second-brain・Claudsidian・brainqub3）との比較です。

| | COG-second-brain | Claudsidian | brainqub3 | **kioku** |
|---|---|---|---|---|
| Obsidian依存 | あり（推奨） | **Vault が中心UI（必須）** | なし | **なし** |
| スマホ入力口 | なし | なし | なし | **Telegram Channels** |
| 自動コミット | 手動実行 | 手動推奨 | なし | **Stopフック（1セッション1コミット）** |
| 定期サマリー | `/daily-brief`（手動） | weekly（手動） | なし | **launchd 自動（09:00・日曜10:00）** |
| プロアクティブ通知 | なし | なし | なし | **定期＋文脈トリガー** |
| 通知ガバナンス | — | — | — | **上限・静音・冷却期間・除外タグ** |
| 通知ログ | — | — | — | **`reports/proactive-*.md`** |
| tmux不要 | — | — | — | **✅ launchd のみ** |

> Claudsidian は [@heyitsnoah](https://github.com/heyitsnoah/claudesidian) が開発（★1,800）。  
> COG-second-brain は [@huytieu](https://github.com/huytieu/COG-second-brain) が開発（★258）。  
> Claude Code Channels は 2026年3月20日に Research Preview として公開。

---

## 本質的な差別化

Channels 対応は他テンプレートが追随できる機能です。  
長く残る差は **「安全に無人で回す設計」** と **「プロアクティブの品質・制御」** にあります。

### 安全な無人運用の設計

- `--dangerously-skip-permissions` を使いながら、WorkingDirectory・allowlist・CLAUDE.md禁止事項・ログの4層で制御
- Stop フックによる1セッション1コミット（git log が読める）
- 全スケジュールジョブの stdout/stderr をファイルに保存（事後追跡可能）
- `--max-budget-usd` によるコスト上限（暴走を金銭面でも防ぐ）

### プロアクティブ通知の品質制御

「向こうから来る」ことの価値は、通知が適切な量・質・タイミングで届いて初めて成立します。

- **量**：1日上限・静音時間・同一ノート24時間冷却期間
- **質**：最小マッチ件数・除外タグ（`#private` 等）・通知内容のプライバシー制限
- **追跡**：`reports/proactive-YYYY-MM-DD.md` に送信根拠を記録→誤通知のチューニングが可能
- **調整**：パラメータをスクリプト冒頭に集約→1箇所変えるだけで挙動が変わる

---

## PC とスマートフォンから使う

| 入力口 | 方法 | セッション |
|---|---|---|
| Mac ターミナル | Claude Code 直接操作 | メインセッション |
| iPhone | Telegram → Claude Code Channels | 同じメインセッション |
| Claude Desktop | GitHub コネクター（読み取り）＋自然言語で書き込み | 別セッション・同じリポジトリ |

3つすべてが同一の Git リポジトリに書き込みます。**Git が唯一の真実です。**  
どのクライアントも書き換え可能。コンフリクトは `git pull --rebase` で解決します。

---

## 正規のナレッジフロー

**すべての入力はまず `inbox/` に入る。** トリガーワードは種別を示すが、直接 `notes/` には書かない。

```
トリガーワード入力
    │
    ▼
inbox/YYYY-MM-DD-[種別].md に追記     ← 自動（即時）
    │
    ▼
/project:process を実行（手動またはスケジュール）
    │
    ▼
notes/ 以下に移動・整理               ← process コマンドが担う
```

### トリガーワード一覧

| プレフィックス | inbox への書き込み先 | process 後の移動先 |
|---|---|---|
| `idea: ...` | `inbox/YYYY-MM-DD-ideas.md` | `notes/ideas/` |
| `task: ...` | `inbox/YYYY-MM-DD-tasks.md` | `notes/tasks/` |
| `log: ...` | `inbox/YYYY-MM-DD-log.md` | `daily/YYYY-MM-DD.md` にマージ |
| `research: ...` | `inbox/YYYY-MM-DD-research.md` | `notes/research/` |
| `save` / `push` | — | git add + commit + push |
| `status` | — | git status ＋ 今日の inbox を表示 |
| `process` | — | /project:process を実行 |

---

## Obsidian との併用パターン

kioku を「キャプチャ専用レイヤー」として使い、長期保管は Obsidian に委ねるパターンも有効です。

```
iPhone → Telegram → kioku/inbox/   ← キャプチャ
kioku/notes/        ← 整理済み短期ナレッジ
     ↓ 月次エクスポート or rsync
Obsidian Vault      ← 長期保管・ビジュアル探索
```

この場合、kioku の `notes/` を Obsidian Vault のサブフォルダに向けるか、  
月次の process で Obsidian 形式（wikilinks）に変換してエクスポートします。  
kioku 単体でも完結しますが、Obsidian を使いたい場合も排他的に選ぶ必要はありません。

---

## Gitコミット戦略

| フック | 動作 | コミットメッセージ |
|---|---|---|
| PostToolUse（Write/Edit）| `git add -A` のみ（コミットしない） | — |
| Stop（セッション終了）| `git commit` まで実行 | `auto: session HH:MM` |
| 明示的な `save` / `push` | `git commit && git push` | `save: HH:MM` |
| スケジュールスクリプト | `git commit && git push` | `auto: [スクリプト名] YYYY-MM-DD` |

---

## リポジトリ構造

```
kioku/
├── CLAUDE.md                    # システム全体の憲法
├── README.md                    # 英語 README（公開用）
├── README.ja.md                 # 日本語 README（公開用）
├── .gitignore
├── .claude/
│   ├── settings.json            # フック定義
│   └── commands/
├── inbox/                       # 未処理キャプチャ（唯一の入口）
├── daily/                       # YYYY-MM-DD.md（process 後）
├── notes/
│   ├── ideas/
│   ├── tasks/
│   ├── projects/
│   └── research/
├── reports/                     # 自動生成サマリー＋プロアクティブログ
├── scripts/
│   ├── daily-summary.sh
│   ├── weekly-review.sh
│   └── proactive-check.sh       # ガバナンス付き
├── .launchd/
├── logs/                        # スクリプトの stdout/stderr
└── docs/                        # セットアップ・設計・セキュリティ等（テンプレ本体と同様に公開）
```

---

## 月あたりのコスト概算

| 用途 | 頻度 | 上限/回 | 月あたり概算 |
|---|---|---|---|
| 日次サマリー | 30回/月 | $0.30 | 最大 $9.00 |
| 週次レビュー | 4回/月 | $1.00 | 最大 $4.00 |
| proactive-check | セッション終了ごと（推定15回/月） | $0.10 | 最大 $1.50 |
| **合計** | | | **最大 $14.50/月** |

実際はほとんどのスクリプトが上限に達しないため、$5〜8/月 程度が現実的な目安です。  
Claude Max プランに含まれる範囲内に収まることが多いです。

---

*ドキュメントバージョン：v1 — 2026-03-23*
