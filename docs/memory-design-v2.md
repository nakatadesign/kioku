# kioku memory — 設計方針 v2

> Phase 1 PoC 完了後の設計調査メモを整理した公開版。

---

## 基本方針: Claude API 不使用・検索処理はローカル完結

kioku v2 のセマンティック記憶エンジンは **Claude API を使わず、検索処理をローカルで完結** させることを原則とする。Telegram への通知送信には Telegram Bot API を直接呼び出す。

**理由:**
- コスト予測不能: ノート走査のコストがノート数に比例して増加する
- 外部依存排除: API の可用性・レート制限・料金変更に左右されない
- プライバシー: ノート本文を外部サービスに送信しない

---

## 検索アーキテクチャ

### 本線: FTS5 + sqlite-vec ハイブリッド検索

1. FTS5 trigram キーワード検索 → 上位20件
2. sqlite-vec ベクトル類似度検索 → 上位20件（Ruri v3-130m, 512次元）
3. RRF (k=60) で統合
4. 時間減衰: `final_score = rrf_score × 2^(-age_days / 30)`
5. `#private` 除外 → 上位N件返却

### 縮退モード: FTS5-only

sqlite-vec が利用不可な環境（`enable_load_extension` 非対応の Python ビルド）では、
FTS5 trigram + 時間減衰のみで動作する。

**縮退モードの制約（Phase 1 評価で確認済み）:**
- 同義語・言い換え・概念的な関連を検出できない（ヒット率 2/5）
- キーワードが一致するノートのみヒットする
- 意味検索の本線ではない

### sqlite-vec 有効化の推奨環境

sqlite-vec を使うには `enable_load_extension` が有効な Python ビルドが必要。

**条件:** Python の sqlite3 モジュールで `conn.enable_load_extension(True)` が成功すること。

確認方法:
```python
import sqlite3
conn = sqlite3.connect(':memory:')
conn.enable_load_extension(True)  # AttributeError が出なければ OK
```

既知の対応ビルド:
- Homebrew Python (`brew install python@3.13`)
- pyenv でソースビルド（`--enable-loadable-sqlite-extensions` オプション付き）
- 公式インストーラ版は **非対応**（macOS）

---

## フェーズ計画（更新版）

### Phase 1: CLI コアエンジン — **完了**

- FTS5 + sqlite-vec ハイブリッド検索エンジン
- FTS5-only 縮退モード対応
- CLI: `reindex`, `ingest`, `search`, `stats`
- テスト: 19 件合格

### Phase 2: ローカルベクトル検索の検証 — **次の一手**

**ゴール:** sqlite-vec 有効環境で同じ評価サンプルを再検証し、ヒット率 3/5 以上を確認する。

**手順:**
1. sqlite-vec 有効な Python 環境を用意する
2. Phase 1 と同じ 5 サンプルで比較評価を実施する
3. 合格基準を満たしたら proactive-check.sh に統合する

**proactive-check.sh 統合の条件:**
- ヒット率 3/5 以上（上位5件中、期待ノートが3件以上含まれる）
- warm 検索 500ms 以内
- cold 検索（Python起動 + モデルロード + 検索）5s 以内
- **Claude API は使用しない** — 検索はローカル完結、Telegram 通知は Bot API 直接呼び出し

**Telegram 通知:**
proactive-check.sh の Telegram 通知は `curl + Telegram Bot API` 直接呼び出しで実装済み。
Claude API 依存はない。

### Phase 3: process.md 統合 — **完了**

- `/project:process` で notes/ に移動したファイルを自動 ingest
- 失敗耐性: memory エラーで process 全体を止めない
- memory 未セットアップ時はスキップ

**既知の性能課題: 複数ファイル時の cold start 重複**

現状は `memory.cli ingest <path>` をファイルごとに呼ぶため、Python プロセス起動 + モデルロード（約 8.7s）が毎回発生する。1回の process で 3 件以上のファイルを処理するケースが増えたら、以下の最適化を実装する:

- `memory.cli ingest-many <path1> <path2> ...` コマンドを追加
- 1 プロセスでモデルを 1 回だけロードし、複数ファイルを順次 ingest する
- process.md からの呼び出しを `ingest` × N 回 → `ingest-many` × 1 回に切り替える

### Phase 4: MCP サーバー化（Phase 2-3 の価値確認後）

- Claude Code セッション内から `memory_search` を直接呼べるようにする
- Phase 2-3 の価値が確認できてから着手する

---

## proactive-check.sh の将来形（ローカル検索 + Telegram Bot API 直接通知）

```bash
# memory セットアップ済み → ローカル検索 + Bot API 直接通知
if [ -f "$KIOKU/memory/data/kioku.db" ]; then
  QUERY=$(sed '/^---$/,/^---$/d' "$NEW_FILE" | head -c 500)
  RELATED=$("$KIOKU/memory/.venv/bin/python" -m memory.cli search --query "$QUERY" --limit 5 --json)
  # 関連ノートがあれば Bot API で通知
  if [ "$(echo "$RELATED" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')" -ge 2 ]; then
    # curl で Telegram Bot API 直接送信
    source ~/.claude/channels/telegram/.env
    MSG="[kioku] 新しいメモに関連: $(echo "$RELATED" | python3 -c 'import sys,json; [print(r["title"]) for r in json.load(sys.stdin)[:3]]')"
    curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" -d "text=${MSG}" > /dev/null
  fi
else
  echo "$(date): memory 未セットアップ、スキップ" >> "$LOG"
fi
```

---

*更新: 2026-03-23 — Phase 1 PoC 完了後、API 不使用方針に変更*
