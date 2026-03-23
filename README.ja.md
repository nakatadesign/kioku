# kioku

> Claude Code のための個人ナレッジ管理テンプレート。
> 蓄積 → 整理 → 引き出す。能動的に、安全に。

## kioku とは

**kioku（記憶）** は Git ベースの個人ナレッジリポジトリテンプレートです。
3つの入力口を単一の情報源に集約し、必要になる前に関連する知識をプッシュ通知します。

## 入力口

| 入力口 | 方法 | セッション |
|---|---|---|
| Mac ターミナル | Claude Code 直接操作 | メインセッション |
| iPhone | Telegram → Claude Code Channels | 同じメインセッション |
| Claude Desktop | GitHub コネクター | 別セッション・同じリポジトリ |

## セットアップ

`docs/setup-v1.md` を参照してください。

## 内部ドキュメント

- `docs/setup-v1.md` — セットアップガイド
- `docs/architecture-v1.md` — アーキテクチャ・フック定義
- `docs/security-v1.md` — セキュリティルール
- `docs/notification-policy-v1.md` — 通知ポリシー
- `docs/overview-v1.md` — 詳細概要・他ツールとの比較

## テンプレートと個人インスタンスの違い

このリポジトリは**オープンソースの配布用テンプレート**です。fork または clone して自分用の kioku インスタンスを作成してください。個人インスタンスにはプライベートなメモ・タスク・アイデアが蓄積されるため、**GitHub 上では Private リポジトリにすることを強く推奨**します。

## ライセンス

MIT License。詳細は [LICENSE](LICENSE) を参照してください。
