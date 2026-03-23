"""kioku セマンティック記憶エンジン — コア。

FTS5 trigram + sqlite-vec ベクトル検索 + RRF + 時間減衰。
sqlite-vec が利用不可の場合は FTS5-only 縮退モードで動作する。
"""

from __future__ import annotations

import hashlib
import logging
import math
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .chunker import Chunk
from .config import (
    DB_PATH,
    EXCLUDE_TAGS,
    FTS_CANDIDATE_LIMIT,
    HALF_LIFE_DAYS,
    RRF_K,
    VEC_CANDIDATE_LIMIT,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """検索結果1件。"""
    source_path: str
    title: str
    score: float
    snippet: str  # マッチしたチャンクの先頭部分
    date: str


def _serialize_f32(vec) -> bytes:
    """float32 配列を bytes に変換する（sqlite-vec 用）。"""
    return struct.pack(f"{len(vec)}f", *vec)


class Engine:
    """セマンティック記憶エンジン。"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._vector_enabled = False
        self._trigram_enabled = True  # フォールバック判定は _init_db で行う

    @property
    def vector_enabled(self) -> bool:
        return self._vector_enabled

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._init_db()
        return self._conn

    def _try_load_sqlite_vec(self, conn: sqlite3.Connection) -> bool:
        """sqlite-vec のロードを試みる。成功すれば True。"""
        try:
            conn.enable_load_extension(True)
        except AttributeError:
            logger.info(
                "sqlite-vec 無効: この Python は enable_load_extension をサポートしていません。"
                " FTS5-only モードで動作します。"
            )
            return False

        try:
            import sqlite_vec
            sqlite_vec.load(conn)
            return True
        except ImportError:
            logger.info("sqlite-vec 無効: sqlite-vec パッケージが見つかりません。")
            return False
        except Exception as e:
            logger.info(f"sqlite-vec 無効: ロード失敗 ({e})。FTS5-only モードで動作します。")
            return False

    def _init_db(self) -> None:
        """スキーマを初期化する。"""
        conn = self._conn
        assert conn is not None

        self._vector_enabled = self._try_load_sqlite_vec(conn)

        # チャンクテーブル
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                date TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_path, chunk_index)
            )
        """)

        # FTS5 インデックス（trigram を試み、失敗なら unicode61）
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(
                    title, text, tags,
                    content='chunks',
                    content_rowid='id',
                    tokenize='trigram'
                )
            """)
            self._trigram_enabled = True
        except sqlite3.OperationalError:
            logger.info("trigram tokenizer 不可。unicode61 にフォールバックします。")
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(
                    title, text, tags,
                    content='chunks',
                    content_rowid='id',
                    tokenize='unicode61'
                )
            """)
            self._trigram_enabled = False

        # ベクトルテーブル（sqlite-vec 有効時のみ）
        if self._vector_enabled:
            from .embedder import get_dimension
            dim = get_dimension()
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec
                USING vec0(embedding float[{dim}])
            """)

        # トリガー: chunks 更新時に FTS を同期
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, title, text, tags)
                VALUES (new.id, new.title, new.text, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, title, text, tags)
                VALUES ('delete', old.id, old.title, old.text, old.tags);
            END;
        """)

        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def ingest(self, chunks: list[Chunk]) -> int:
        """チャンクを DB に挿入・更新する。挿入件数を返す。

        同一 source_path で chunk_index が減った場合、余剰チャンクを削除する。
        """
        if not chunks:
            return 0

        conn = self._get_conn()
        inserted = 0
        source_path = chunks[0].source_path
        new_max_index = max(c.index for c in chunks)

        # ベクトル埋め込み（有効時のみ）
        embeddings = None
        if self._vector_enabled:
            from .embedder import embed_documents
            texts = [c.text for c in chunks]
            embeddings = embed_documents(texts)

        for i, chunk in enumerate(chunks):
            content_hash = hashlib.md5(chunk.text.encode()).hexdigest()
            tags_str = " ".join(chunk.tags)

            # 既存チャンクとハッシュ比較
            existing = conn.execute(
                "SELECT id, content_hash FROM chunks WHERE source_path = ? AND chunk_index = ?",
                (chunk.source_path, chunk.index),
            ).fetchone()

            if existing and existing["content_hash"] == content_hash:
                continue  # 変更なし

            if existing:
                # 既存を削除（FTS トリガーが発火）
                row_id = existing["id"]
                conn.execute("DELETE FROM chunks WHERE id = ?", (row_id,))
                if self._vector_enabled:
                    conn.execute("DELETE FROM chunks_vec WHERE rowid = ?", (row_id,))

            # 新規挿入
            cur = conn.execute(
                """INSERT INTO chunks (source_path, chunk_index, title, tags, date, text, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (chunk.source_path, chunk.index, chunk.title, tags_str, chunk.date, chunk.text, content_hash),
            )
            new_id = cur.lastrowid

            # ベクトル挿入
            if self._vector_enabled and embeddings is not None:
                vec_bytes = _serialize_f32(embeddings[i])
                conn.execute(
                    "INSERT INTO chunks_vec(rowid, embedding) VALUES (?, ?)",
                    (new_id, vec_bytes),
                )

            inserted += 1

        # 余剰チャンク削除: 以前より chunk_index が減った場合
        stale = conn.execute(
            "SELECT id FROM chunks WHERE source_path = ? AND chunk_index > ?",
            (source_path, new_max_index),
        ).fetchall()
        for row in stale:
            conn.execute("DELETE FROM chunks WHERE id = ?", (row["id"],))
            if self._vector_enabled:
                conn.execute("DELETE FROM chunks_vec WHERE rowid = ?", (row["id"],))

        conn.commit()
        return inserted

    def delete_by_path(self, source_path: str) -> int:
        """指定パスのチャンクをすべて削除する。削除件数を返す。"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id FROM chunks WHERE source_path = ?", (source_path,)
        ).fetchall()

        for row in rows:
            conn.execute("DELETE FROM chunks WHERE id = ?", (row["id"],))
            if self._vector_enabled:
                conn.execute("DELETE FROM chunks_vec WHERE rowid = ?", (row["id"],))

        conn.commit()
        return len(rows)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """ハイブリッド検索（FTS5 + ベクトル + RRF + 時間減衰）。"""
        conn = self._get_conn()
        now = datetime.now()

        # FTS5 検索
        fts_results = self._search_fts(conn, query)

        # ベクトル検索（有効時のみ）
        vec_results = {}
        if self._vector_enabled:
            vec_results = self._search_vec(conn, query)

        # スコア統合
        all_ids = set(fts_results.keys()) | set(vec_results.keys())
        if not all_ids:
            return []

        scored: list[tuple[int, float]] = []
        for chunk_id in all_ids:
            if self._vector_enabled and vec_results:
                # RRF
                fts_rank = fts_results.get(chunk_id, FTS_CANDIDATE_LIMIT + 1)
                vec_rank = vec_results.get(chunk_id, VEC_CANDIDATE_LIMIT + 1)
                rrf_score = 1.0 / (RRF_K + fts_rank) + 1.0 / (RRF_K + vec_rank)
            else:
                # FTS-only: ランクの逆数をスコアにする
                fts_rank = fts_results.get(chunk_id, FTS_CANDIDATE_LIMIT + 1)
                rrf_score = 1.0 / (RRF_K + fts_rank)

            scored.append((chunk_id, rrf_score))

        # 時間減衰を適用してファイル単位で集約
        path_scores: dict[str, tuple[float, dict]] = {}  # path -> (best_score, row_data)
        for chunk_id, rrf_score in scored:
            row = conn.execute(
                "SELECT source_path, title, date, text, tags FROM chunks WHERE id = ?",
                (chunk_id,),
            ).fetchone()
            if not row:
                continue

            # 除外タグチェック
            chunk_tags = set(row["tags"].split())
            if chunk_tags & EXCLUDE_TAGS:
                continue

            # 時間減衰
            decay = self._time_decay(row["date"], now)
            final_score = rrf_score * decay

            path = row["source_path"]
            if path not in path_scores or final_score > path_scores[path][0]:
                path_scores[path] = (final_score, dict(row))

        # ソートして返す
        results = []
        for path, (score, data) in sorted(path_scores.items(), key=lambda x: -x[1][0]):
            results.append(SearchResult(
                source_path=data["source_path"],
                title=data["title"],
                score=score,
                snippet=data["text"][:200],
                date=data["date"],
            ))
            if len(results) >= limit:
                break

        return results

    def _build_fts_query(self, query: str) -> str:
        """FTS5 クエリを構築する。

        trigram tokenizer は3文字以上の部分文字列マッチが必要。
        クエリを空白で分割し、3文字以上の語はそのまま、
        3文字未満の語は除外して OR 結合する。
        """
        import re
        # 空白・句読点で分割
        tokens = re.split(r'[\s、。,.\-/]+', query.strip())
        # 3文字以上のトークンのみ（trigram の最小単位）
        valid = [t for t in tokens if len(t) >= 3]

        if not valid and tokens:
            # 全トークンが3文字未満の場合、元のクエリをそのまま試す（unicode61フォールバック時用）
            if not self._trigram_enabled:
                return " OR ".join(f'"{t}"' for t in tokens if t)
            # trigram モードでは3文字未満はマッチしない。
            # クエリ全体を連結して3文字以上にする
            combined = "".join(tokens)
            if len(combined) >= 3:
                return f'"{combined}"'
            return ""

        return " OR ".join(f'"{t}"' for t in valid)

    def _search_fts(self, conn: sqlite3.Connection, query: str) -> dict[int, int]:
        """FTS5 検索。{chunk_id: rank} を返す。"""
        fts_query = self._build_fts_query(query)
        if not fts_query:
            return {}

        try:
            rows = conn.execute(
                """SELECT rowid, rank FROM chunks_fts
                   WHERE chunks_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts_query, FTS_CANDIDATE_LIMIT),
            ).fetchall()
        except sqlite3.OperationalError:
            # クエリに FTS5 で扱えない文字が含まれる場合
            return {}

        return {row["rowid"]: i + 1 for i, row in enumerate(rows)}

    def _search_vec(self, conn: sqlite3.Connection, query: str) -> dict[int, int]:
        """ベクトル検索。{chunk_id: rank} を返す。"""
        from .embedder import embed_query
        vec = embed_query(query)
        if vec is None:
            return {}

        vec_bytes = _serialize_f32(vec)
        rows = conn.execute(
            """SELECT rowid, distance FROM chunks_vec
               WHERE embedding MATCH ? AND k = ?
               ORDER BY distance""",
            (vec_bytes, VEC_CANDIDATE_LIMIT),
        ).fetchall()

        return {row["rowid"]: i + 1 for i, row in enumerate(rows)}

    def _time_decay(self, date_str: str, now: datetime) -> float:
        """時間減衰係数を計算する。2^(-age_days / half_life)"""
        if not date_str:
            return 0.5  # 日付不明は半減期経過相当

        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            age_days = (now - dt).days
            if age_days < 0:
                age_days = 0
            return math.pow(2, -age_days / HALF_LIFE_DAYS)
        except ValueError:
            return 0.5

    def get_indexed_paths(self) -> set[str]:
        """DB に登録されている source_path の集合を返す。"""
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT source_path FROM chunks").fetchall()
        return {row["source_path"] for row in rows}

    def stats(self) -> dict:
        """統計情報を返す。"""
        conn = self._get_conn()

        total_chunks = conn.execute("SELECT COUNT(*) as c FROM chunks").fetchone()["c"]
        total_files = conn.execute(
            "SELECT COUNT(DISTINCT source_path) as c FROM chunks"
        ).fetchone()["c"]

        return {
            "total_chunks": total_chunks,
            "total_files": total_files,
            "vector_search": "enabled" if self._vector_enabled else "disabled (sqlite-vec unavailable in this Python build)",
            "fts_tokenizer": "trigram" if self._trigram_enabled else "unicode61 (fallback)",
            "db_path": str(self.db_path),
            "db_size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2) if self.db_path.exists() else 0,
        }
