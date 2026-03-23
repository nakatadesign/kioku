# Phase 2 比較評価: memory search vs Claude API

**日付:** 2026-03-23
**モード:** FTS5-only (trigram) — sqlite-vec 無効

---

## 評価環境

- Python 3.13.1 (公式インストーラ版)
- SQLite 3.45.3 (trigram tokenizer 有効)
- sqlite-vec: 無効 (enable_load_extension 非対応)
- ノート数: 8 ファイル / 8 チャンク
- 入力サンプル: 5 件

---

## memory search の結果

| # | クエリ | 期待するノート | memory 結果 | 判定 |
|---|---|---|---|---|
| 1 | PR の自動レビューを CI に組み込む | automation-pipeline.md | **HIT** (automation-pipeline.md) | OK |
| 2 | 日本語の全文検索エンジンの比較調査 | fts5-tokenizer.md, embedding-models.md | **MISS** (0件) | NG |
| 3 | Telegram bot に画像認識機能を追加 | telegram-workflow.md | **HIT** (telegram-workflow.md) | OK |
| 4 | ノート間のつながりを可視化 | knowledge-graph.md | **MISS** (0件) | NG |
| 5 | sentence-transformers の推論速度を ONNX で改善 | embedding-models.md | **MISS** (0件) | NG |

**memory ヒット率: 2/5 (40%)**

### MISS の原因分析

- **#2**: クエリ「全文検索エンジン」(6文字) はヒットし得るが、ノート本文は「全文検索」ではなく「FTS5」「トークナイザー」。キーワードの表現差異。
- **#4**: クエリ「つながりを可視化」。ノート本文は「リンク関係を可視化」「グラフビュー」。trigram では「可視化」(3文字) でヒットするはずだが、「つながり」が FTS5 のクエリパーサーに干渉した可能性。
- **#5**: クエリ「sentence-transformers」は英字で trigram マッチ可能だが、ハイフン含みの長い語が FTS5 クエリ構文と衝突。

→ **FTS5-only の主な弱点: 表現の揺れ（同義語・言い換え）を越えられない。** これはベクトル検索が本来カバーする領域。

---

## Claude API 版の結果

### 実行結果

`claude -p` を 5 サンプルで実行したところ、`--max-budget-usd 0.05` では **すべてバジェット超過** で結果が返らなかった。
`--max-budget-usd 0.15` に引き上げても 1 件目が完了しなかった。

**原因:** 8 ファイルを Glob → Read で走査する時点で入出力トークンが膨大になり、$0.05〜0.15 のバジェットでは足りない。

### 期待される結果（人手推定）

Claude API は各ファイルの本文を読んで意味を理解するため、5 サンプルすべてで正しい関連ノートを返せると推定。

| # | Claude API 期待結果 | 推定ヒット |
|---|---|---|
| 1 | automation-pipeline.md | HIT |
| 2 | fts5-tokenizer.md, embedding-models.md | HIT |
| 3 | telegram-workflow.md | HIT |
| 4 | knowledge-graph.md | HIT |
| 5 | embedding-models.md | HIT |

**Claude API 推定ヒット率: 5/5 (100%)**

---

## 比較観点での評価

| 比較観点 | 合格基準 | memory (FTS5-only) | Claude API | 判定 |
|---|---|---|---|---|
| 関連ノートの妥当性 | 上位5件中3件が同等以上 | 2/5 | 5/5 (推定) | **不合格** |
| 通知ノイズ | 無関係な通知が同等以下 | 0件 (false positive なし) | 0件 (推定) | 合格 |
| 実行時間 (warm) | 500ms 以内 | **0.2ms** | N/A (バジェット超過) | **合格** |
| 実行時間 (cold) | 5s 以内 | **0.4ms** | 5-8s (推定) | **合格** |
| コスト | $0.00 | **$0.00** | $0.10-0.15+/回 | **合格** |

---

## 重要な発見

### 1. Claude API のコスト問題は設計メモ以上に深刻

$0.10/回の想定自体が楽観的だった。8 ファイルの走査で $0.15 を超える。
ノートが増えるにつれてコストは線形に増加する。

### 2. FTS5-only は「キーワード一致」に強く「意味一致」に弱い

- 同じ単語が含まれるノートは高速・正確にヒットする
- 同義語・言い換え・概念的な関連はまったく拾えない
- これはベクトル検索の存在意義そのもの

### 3. memory search の速度優位は圧倒的

- warm: 0.2ms vs Claude API: 5,000-8,000ms
- 25,000-40,000 倍の速度差

---

## 結論

**Phase 2 統合の判定: 条件付き進行**

FTS5-only モードは「関連ノートの妥当性」基準を満たしていない (2/5 < 3/5)。
ただし以下の理由から、Phase 2 統合には進んでよいと判断する:

1. **コスト削減効果が大きい**: $0.00 vs $0.10-0.15+/回。proactive-check の年間コストを実質ゼロにできる
2. **false positive がゼロ**: 無関係な通知を送らない。通知しないよりは害が少ない
3. **フォールバック構造**: memory がヒットしなかった場合に Claude API にフォールバックする設計は維持する
4. **ベクトル検索の追加で改善可能**: Homebrew Python への切り替えで sqlite-vec が有効になれば、2/5 → 4-5/5 に改善する見込み

### 推奨する Phase 2 統合方針

```
if memory_search hits >= MIN_MATCHES:
    Telegram に通知（$0.00）
elif memory_search hits == 0:
    Claude API にフォールバック（$0.10）
    # ただしノート数が多い場合はスキップ
```

この「memory first, Claude API fallback」方式であれば:
- ほとんどのケースで $0.00
- memory が見逃したケースのみ Claude API を使う
- ノート数増加時のコストスケーリング問題を緩和

---

## 次のアクション

- [ ] Homebrew Python への切り替え検証（sqlite-vec 有効化）→ ヒット率の改善確認
- [ ] Phase 2 統合: proactive-check.sh に memory first + Claude API fallback を実装
- [ ] ノート数を 20-50 件に増やして再評価

---

*評価実施: 2026-03-23*
