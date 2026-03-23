"""kioku セマンティック記憶エンジン — 設定値"""

from pathlib import Path

# パス
KIOKU_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "data" / "kioku.db"
MODEL_NAME = "cl-nagoya/ruri-v3-130m"

# インデックス対象ディレクトリ（KIOKU_ROOT からの相対パス）
INDEX_DIRS = ["notes", "daily"]

# チャンク分割
CHUNK_MAX_CHARS = 1000  # 1チャンクの最大文字数
CHUNK_OVERLAP_CHARS = 100  # チャンク間のオーバーラップ

# 検索
DEFAULT_LIMIT = 10
FTS_CANDIDATE_LIMIT = 20  # FTS5 で取得する候補数
VEC_CANDIDATE_LIMIT = 20  # ベクトル検索で取得する候補数
RRF_K = 60  # RRF パラメータ

# 時間減衰
HALF_LIFE_DAYS = 30  # 半減期（日）

# プライバシー除外タグ
EXCLUDE_TAGS = {"#private", "#nopush", "#draft"}
