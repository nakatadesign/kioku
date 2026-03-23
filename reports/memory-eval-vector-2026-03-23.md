# Phase 2 評価: FTS5 + sqlite-vec ハイブリッド検索

**日付:** 2026-03-23
**モード:** FTS5 trigram + sqlite-vec (Ruri v3-130m, 512次元) + RRF + 時間減衰

---

## 評価環境

- Python 3.13.12 (Homebrew)
- SQLite 3.51.3
- sqlite-vec: **有効**
- Ruri v3-130m: MPS (Apple Silicon GPU) バックエンド
- ノート数: 8 ファイル / 8 チャンク
- 入力サンプル: 5 件（FTS5-only 評価と同一）

---

## 結果

| # | クエリ | 期待するノート | 上位5件に含まれるか | 判定 |
|---|---|---|---|---|
| 1 | PR の自動レビューを CI に組み込む | automation-pipeline.md | **1位** | HIT |
| 2 | 日本語の全文検索エンジンの比較調査 | fts5-tokenizer.md / embedding-models.md | **5位** (embedding-models) | HIT |
| 3 | Telegram bot に画像認識機能を追加 | telegram-workflow.md | **4位** | HIT |
| 4 | ノート間のつながりを可視化 | knowledge-graph.md | 上位5件外 | MISS |
| 5 | sentence-transformers の推論速度を ONNX で改善 | embedding-models.md | **5位** | HIT |

**ヒット率: 4/5 (80%)**

---

## FTS5-only との比較

| 指標 | FTS5-only | FTS5 + sqlite-vec | 変化 |
|---|---|---|---|
| ヒット率 | 2/5 (40%) | **4/5 (80%)** | +40pt |
| false positive | 0 | 0 | 同等 |
| warm 検索 | 0.2ms | **16-28ms** | +100倍（十分高速） |
| cold 検索 | 0.4ms | **21ms** | +50倍（十分高速） |
| コスト | $0.00 | **$0.00** | 同等 |

---

## 合格基準の判定

| 比較観点 | 合格基準 | 結果 | 判定 |
|---|---|---|---|
| 関連ノートの妥当性 | 上位5件中3件が期待と一致 | **4/5** | **合格** |
| 通知ノイズ | 無関係な通知が同等以下 | 0件 | **合格** |
| 実行時間 (warm) | 500ms 以内 | **28ms (最大)** | **合格** |
| 実行時間 (cold) | 5s 以内 | **21ms** | **合格** |
| コスト | $0.00 | $0.00 | **合格** |

**全基準合格。proactive-check.sh への統合条件を満たす。**

---

## MISS の分析

**#4: 「ノート間のつながりを可視化するダッシュボード」**

期待: knowledge-graph.md（「notes/ 間のリンク関係を可視化」「グラフビュー」）

knowledge-graph.md は上位5件に入らず、代わりに daily ログや他のノートが優先された。
原因: ノート数が 8 件と少なく、daily ログの時間減衰スコアが高い（直近なので減衰が小さい）。
knowledge-graph.md は 2026-03-05 と最も古く、時間減衰で不利。

**対策（将来）:**
- ノート数が増えれば daily ログの相対スコアは下がる
- 種別ごとの時間減衰係数（Phase 3 で検討: ideas=60日 vs daily=14日）で改善可能

---

## reindex 性能

| 指標 | 値 |
|---|---|
| ファイル数 | 8 |
| チャンク数 | 8 |
| reindex 所要時間 | 10.1s（モデル初回ロード含む） |
| モデルロード | ~5s |
| 埋め込み/チャンク | ~0.3s |

cold start（モデルロード含む）は 10s 程度。warm 状態（モデルロード済み）の ingest は 1 チャンクあたり 0.3s。
proactive-check.sh からの呼び出しは cold start になるが、検索のみなら 21ms で完了するため問題ない。

---

## 結論

**FTS5 + sqlite-vec ハイブリッド検索は Phase 2 統合の条件を満たす。**

次のステップ（※ 評価時点の計画。現在はすべて実装済み）:
- [x] proactive-check.sh にローカル検索を統合（Claude API 不使用）
- [x] Telegram 通知を Bot API 直接呼び出しに切り替え
- [x] サンプルノートを削除してテンプレをクリーンに戻す

---

*評価実施: 2026-03-23*
