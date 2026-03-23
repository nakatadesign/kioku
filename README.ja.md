# kioku（記憶）

**Claude Code のための個人ナレッジ管理テンプレート。**  
蓄積 → 整理 → 引き出す。能動的に、安全に。

[English](./README.md) | __日本語版 README はこちら__

---

## なぜ kioku が必要か

Claude Code を使い込んでいくと、ある壁にぶつかります。

あのセッションで見つけた解決策が、今日また必要になっている。スマホで思いついたアイデアは、PCを開いた瞬間にどこかへ消えている。3ヶ月前に調べたことを、今また一から調べ直している。

Claude Code はその場その場では優秀です。しかし**セッションをまたいで知識を持続させる仕組み**は、自分で作らなければなりません。

kioku はそのための Git リポジトリテンプレートです。

ツールではありません。**Claude Code が住むワーキングディレクトリ**です。

---

## kioku が解決すること

| 問題 | kioku の答え |
|---|---|
| セッションが終わると知識が消える | Git で永続化。すべてのセッションが同じリポジトリを参照する |
| スマホのメモがワークフローに入ってこない | Telegram から直接 Claude Code セッションにキャプチャできる |
| 過去の関連思考が埋もれている | プロアクティブ通知が「このメモ、3ヶ月前のアレと繋がってます」と教えてくれる |
| 自動化が怖い（何をされるかわからない） | 4層のセキュリティ設計と全操作のログで、事後追跡を保証する |

---

## PC とスマートフォンから使う

kioku は PC とスマートフォンを**単一の Git リポジトリ**に束ねます。どちらからでもナレッジを追加でき、同じリポジトリを見ています。

```
PC（Mac ターミナル）────────────────┐
                                     ▼
スマートフォン（Telegram Channels）► Claude Code セッション
                                     ▼
                         your-username/kioku（Private）
                         ─────────────────────────────
                         inbox/ → notes/ → reports/
```

**Git が唯一の真実です。** どのデバイスから書いても、どのクライアントから読んでも、同じリポジトリを見ています。

---

## ナレッジの流れ

すべての入力は、まず `inbox/` に着地します。

```
① 入力（どのデバイスからでも）
       │
       ▼
  inbox/YYYY-MM-DD-[種別].md に追記   ← トリガーワードで自動ルーティング
       │
       ▼
  Claude Code セッション終了
  → Stop フック：git commit（1セッション = 1コミット）
  → proactive-check：新着と既存ノートの関連を検出
       │
       ▼
  /project:process（手動 or スケジュール）
  → inbox/ を読んで分類・タグ付け
  → notes/[種別]/ に整理・移動
```

トリガーワードで種別を指定するだけで、あとは Claude Code が分類します。

| 送るメッセージ | 動作 |
|---|---|
| `idea: 新しい機能のアイデア` | `inbox/YYYY-MM-DD-ideas.md` に追記 |
| `task: 明日までにドキュメント更新` | `inbox/YYYY-MM-DD-tasks.md` に追記 |
| `log: 今日のセッションで判明したこと` | `inbox/YYYY-MM-DD-log.md` に追記 |
| `research: この論文の要点` | `inbox/YYYY-MM-DD-research.md` に追記 |
| `save` | git commit + push |
| `status` | 今日の inbox と git 状況を表示 |

---

## リポジトリ構造

```
kioku/
├── CLAUDE.md                 # システムの憲法。エージェントの振る舞いを定義
├── .gitignore
│
├── .claude/
│   ├── settings.json         # フック定義（PostToolUse / Stop / SessionStart）
│   └── commands/
│       ├── capture.md        # /project:capture
│       ├── process.md        # /project:process（inbox を notes/ に整理）
│       ├── daily.md          # /project:daily
│       └── push-related.md   # /project:push-related
│
├── inbox/                    # 📥 すべての入力の着地点（唯一の入口）
│   └── YYYY-MM-DD-[種別].md
│
├── daily/                    # 📅 日次ノート（process 後に生成）
│   └── YYYY-MM-DD.md
│
├── notes/                    # 📚 整理済みナレッジ
│   ├── ideas/
│   ├── tasks/
│   ├── projects/
│   └── research/
│
├── reports/                  # 📊 自動生成サマリー＋プロアクティブ通知ログ
│   ├── weekly-YYYY-WNN.md
│   └── proactive-YYYY-MM-DD.md
│
├── scripts/                  # 🔧 自動化スクリプト
│   ├── daily-summary.sh      # 毎日 09:00 に Telegram へ朝のブリーフ
│   ├── weekly-review.sh      # 毎週日曜 10:00 にナレッジ品質評価
│   └── proactive-check.sh    # セッション終了ごとに関連ノートを検出
│
├── .launchd/                 # macOS 定期実行設定（tmux 不要）
│   ├── daily.plist
│   └── weekly.plist
│
├── logs/                     # 📋 全スクリプトの実行ログ
│
└── docs/                     # 参照ドキュメント（リポジトリと同じ公開範囲・一覧は下記「ドキュメント」）
```

> **注意:** 自動ステージ・自動コミットは `.claude/settings.json` のフックによる動作であり、kioku リポジトリ自体を Claude Code の作業ディレクトリとして開いたセッションでのみ有効です。別のプロジェクトをルートにしたセッションでは kioku のフックは動作しません。他セッションから kioku のナレッジを参照するには `--add-dir` を使用してください。

---

## プロアクティブ通知 — kioku の核心

一般的な PKM は「呼んだら答える」設計です。kioku は**向こうから来ます**。

### 2種類のトリガー

**定期トリガー（launchd）**
- 毎日 09:00：今日の inbox・関連ノート・タスクを Telegram にブリーフ
- 毎週日曜 10:00：ナレッジ品質スコアリング（HIGH/MEDIUM/LOW）＋ 週次レポート

**文脈トリガー（Stop フック）**
- セッション終了のたびに、新着 inbox と既存 notes/ を照合
- 関連があれば Telegram にメンション：「このアイデア、2ヶ月前のアレと繋がってます」

### 通知は「うるさい」にならない設計

通知が多すぎるシステムは使われなくなります。kioku には最初からガバナンスが組み込まれています。

```bash
MAX_DAILY=3          # 1日の最大通知件数
MIN_MATCHES=2        # 通知する最小関連ノート件数
QUIET_START=22       # 静音開始（22:00〜07:00 は送らない）
QUIET_END=7
NOTIFY_COOLDOWN=86400  # 同じノートは24時間以内に再通知しない
EXCLUDE_TAGS="#private #nopush #draft"  # 通知対象外タグ
```

1箇所を変えるだけで挙動が変わります。送った通知の根拠は `reports/proactive-YYYY-MM-DD.md` に記録されるため、誤通知のチューニングも追跡可能です。

---

## 他の PKM テンプレートとの違い

| | COG-second-brain | Claudsidian | brainqub3 | **kioku** |
|---|---|---|---|---|
| Obsidian 依存 | あり（推奨） | Vault が中心 UI（必須） | なし | **なし** |
| スマホ入力口 | なし | なし | なし | **Telegram Channels** |
| 自動コミット | 手動実行 | 手動推奨 | なし | **Stop フック自動** |
| 定期サマリー | 手動コマンド | 手動 | なし | **launchd 完全自動** |
| プロアクティブ通知 | なし | なし | なし | **定期 ＋ 文脈トリガー** |
| 通知ガバナンス | — | — | — | **上限・静音・冷却・除外タグ** |
| 通知ログ | — | — | — | **reports/proactive-*.md** |
| tmux 不要 | — | — | — | **✅ launchd のみ** |

> Claudsidian：[heyitsnoah/claudesidian](https://github.com/heyitsnoah/claudesidian)（★1,800）  
> COG-second-brain：[huytieu/COG-second-brain](https://github.com/huytieu/COG-second-brain)（★258）  
> Claude Code Channels：2026年3月20日 Research Preview として公開

Channels 対応は他テンプレートが追随できる機能です。kioku が長く差別化を維持するのは「**安全に無人で回す設計**」と「**通知の品質制御**」にあります。

---

## セキュリティ設計

`--dangerously-skip-permissions` を使いながら安全に運用するため、4層の防御を組み合わせています。

```
[allowlist]          自分の Telegram ID だけが操作できる
    ↓
[WorkingDirectory]   launchd が kioku/ の外を触らないよう制限
    ↓
[CLAUDE.md 禁止事項] rm -rf / git push --force などを明示的に禁止
    ↓
[ログ]               全スクリプトの stdout/stderr を logs/ に保存
                     → 何が起きたか、いつでも確認できる
```

また、Telegram はサードパーティサービスです。通知メッセージにはノートのタイトルとパスのみを含め、本文・クライアント名・金額は絶対に送りません。`#private` タグを付けたノートは通知対象から自動除外されます。

---

## 月あたりのコスト概算

| 用途 | 頻度 | 上限/回 | 月あたり最大 |
|---|---|---|---|
| 日次サマリー | 30回 | $0.30 | $9.00 |
| 週次レビュー | 4回 | $1.00 | $4.00 |
| proactive-check | 約15回 | $0.10 | $1.50 |
| **合計** | | | **最大 $14.50** |

実際はスクリプトが上限に達することはほぼなく、**$5〜8/月程度**が現実的な目安です。Claude Max プランの範囲内に収まることが多いです。

---

## セットアップ概要

詳細は [`docs/setup-v1.md`](./docs/setup-v1.md) を参照してください。

**前提条件**
- Claude Code v2.1.80+
- Bun（Telegram Channels プラグインの実行環境として必要）
- Git / GitHub CLI
- Telegram アカウント

**5つのフェーズ**

```
Phase 1（Day 1・15分）   GitHub リポジトリ作成 + ディレクトリ初期化
Phase 2（Day 1・20分）   CLAUDE.md 作成（エージェントへの指示書）
Phase 3（Day 1・15分）   フック設定（.claude/settings.json）
Phase 4（Day 1・10分）   Telegram Channels セットアップ＋ペアリング
Phase 5（Day 2・30分）   自動化スクリプト作成＋launchd 登録
```

Phase 1〜4 は初日に完了できます。翌日から自動化が動き始めます。

---

## Obsidian との共存

kioku は Obsidian と対立しません。**キャプチャ専用レイヤー**として使い、長期保管は Obsidian に委ねるパターンも有効です。

```
iPhone → Telegram → kioku/inbox/    ← 日々のキャプチャ
kioku/notes/                         ← 整理済み・短期ナレッジ
      ↓ 月次エクスポート
Obsidian Vault                       ← 長期保管・グラフ探索
```

---

## オプション: セマンティック記憶エンジン (v2)

kioku には、オプションのローカルセマンティック検索エンジン（`memory/`）が含まれています。セットアップすると以下が有効になります:

- **意味ベースのノート発見** — キーワードが一致しなくても関連ノートを検出（ローカル埋め込みモデル [Ruri v3-130m](https://huggingface.co/cl-nagoya/ruri-v3-130m) を使用）
- **コストゼロのプロアクティブ通知** — `proactive-check.sh` の Claude API 呼び出しをローカルの FTS5 + ベクトル検索に置換
- **外部 API 不使用** — 検索はすべてローカル完結。Telegram 通知は Bot API を直接呼び出し

v2 はオプションです。なくても kioku v1 は grep/glob 検索で動作します。有効にするには:

```bash
bash scripts/memory-setup.sh
```

`enable_load_extension` 対応の Python 3.10+ が必要です（例: Homebrew Python）。詳細は [`docs/memory-design-v2.md`](./docs/memory-design-v2.md) を参照してください。

---

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [概要](./docs/overview-v1.md) | 設計思想・競合比較・ナレッジフロー |
| [アーキテクチャ](./docs/architecture-v1.md) | フック定義・スクリプト全文・Desktop 整合ルール |
| [セキュリティ](./docs/security-v1.md) | 4層防御・プライバシーポリシー・チェックリスト |
| [セットアップ](./docs/setup-v1.md) | Phase 1〜5 の手順・動作確認チェックリスト |
| [通知ポリシー](./docs/notification-policy-v1.md) | ガバナンス設定・パラメータ調整・ログ運用 |
| [Memory 設計 v2](./docs/memory-design-v2.md) | セマンティック検索エンジンの設計・ローカルファースト方針 |

---

## ライセンス

MIT

---

*kioku — 2026-03-23*
