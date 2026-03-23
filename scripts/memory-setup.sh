#!/bin/bash
# kioku セマンティック記憶エンジン セットアップスクリプト
# 使い方: bash scripts/memory-setup.sh
set -euo pipefail

KIOKU=$(cd "$(dirname "$0")/.." && pwd)
MEMORY_DIR="$KIOKU/memory"

echo "=== kioku memory セットアップ ==="
echo "KIOKU_ROOT: $KIOKU"

# uv の確認
if ! command -v uv &> /dev/null; then
    echo "エラー: uv がインストールされていません。"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# venv 作成
cd "$MEMORY_DIR"
if [ ! -d ".venv" ]; then
    echo ">>> venv を作成中..."
    uv venv
fi

# 依存インストール
echo ">>> 依存パッケージをインストール中..."
uv pip install -e ".[dev]" 2>&1 | tail -3

# データディレクトリ
mkdir -p "$MEMORY_DIR/data"

# sqlite-vec の動作確認
echo ""
echo ">>> 環境チェック..."
.venv/bin/python -c "
import sqlite3
print(f'  SQLite: {sqlite3.sqlite_version}')

# FTS5
try:
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE VIRTUAL TABLE _t USING fts5(c, tokenize=\"trigram\")')
    print('  FTS5 trigram: OK')
    conn.close()
except Exception:
    print('  FTS5 trigram: 不可（unicode61 にフォールバック）')

# sqlite-vec
try:
    conn = sqlite3.connect(':memory:')
    conn.enable_load_extension(True)
    import sqlite_vec
    sqlite_vec.load(conn)
    print('  sqlite-vec: OK（ベクトル検索有効）')
    conn.close()
except (AttributeError, ImportError, Exception) as e:
    print(f'  sqlite-vec: 無効（FTS5-only モードで動作）')
    print(f'    理由: {e}')
    print(f'    ヒント: Homebrew Python に切り替えると sqlite-vec が利用可能になります')
"

# Ruri v3 モデルのプリロード
echo ""
echo ">>> Ruri v3-130m モデルをダウンロード中（初回のみ）..."
.venv/bin/python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('cl-nagoya/ruri-v3-130m')
print('  Ruri v3-130m: OK')
" 2>&1 | grep -v Warning | grep -v deprecated | grep -v Loading

# reindex
echo ""
echo ">>> 初回 reindex を実行中..."
cd "$KIOKU"
"$MEMORY_DIR/.venv/bin/python" -m memory.cli reindex

# stats
echo ""
"$MEMORY_DIR/.venv/bin/python" -m memory.cli stats

echo ""
echo "=== セットアップ完了 ==="
