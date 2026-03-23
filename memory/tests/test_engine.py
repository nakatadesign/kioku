"""engine のユニットテスト。"""

import pytest

from memory.chunker import Chunk
from memory.engine import Engine


@pytest.fixture
def engine(tmp_path):
    """テスト用のインメモリ風 Engine。"""
    db_path = tmp_path / "test.db"
    eng = Engine(db_path=db_path)
    yield eng
    eng.close()


class TestEngine:
    def test_ingest_と_stats(self, engine):
        chunks = [
            Chunk(
                source_path="notes/ideas/test.md",
                index=0,
                text="eBay 自動出品ツールの設計メモ",
                title="eBay自動化",
                tags=["idea"],
                date="2026-03-23",
            ),
            Chunk(
                source_path="notes/ideas/test.md",
                index=1,
                text="Claude Code のフック設計について詳しく書く",
                title="eBay自動化",
                tags=["idea"],
                date="2026-03-23",
            ),
        ]
        inserted = engine.ingest(chunks)
        assert inserted == 2

        stats = engine.stats()
        assert stats["total_chunks"] == 2
        assert stats["total_files"] == 1

    def test_重複ingestはスキップ(self, engine):
        chunk = Chunk(
            source_path="notes/ideas/test.md",
            index=0,
            text="同じ内容",
            title="テスト",
            date="2026-03-23",
        )
        assert engine.ingest([chunk]) == 1
        assert engine.ingest([chunk]) == 0  # 変更なし

    def test_FTS検索(self, engine):
        chunks = [
            Chunk(source_path="notes/ideas/a.md", index=0,
                  text="自動化ツールの設計", title="自動化", date="2026-03-23"),
            Chunk(source_path="notes/research/b.md", index=0,
                  text="天気予報のAPIについて", title="天気", date="2026-03-23"),
        ]
        engine.ingest(chunks)

        results = engine.search("自動化")
        assert len(results) >= 1
        assert results[0].source_path == "notes/ideas/a.md"

    def test_private除外(self, engine):
        chunks = [
            Chunk(source_path="notes/ideas/secret.md", index=0,
                  text="機密情報", title="秘密", tags=["#private"], date="2026-03-23"),
            Chunk(source_path="notes/ideas/public.md", index=0,
                  text="公開情報", title="公開", date="2026-03-23"),
        ]
        engine.ingest(chunks)

        results = engine.search("情報")
        paths = [r.source_path for r in results]
        assert "notes/ideas/secret.md" not in paths

    def test_delete_by_path(self, engine):
        chunks = [
            Chunk(source_path="notes/ideas/del.md", index=0,
                  text="削除テスト", title="削除", date="2026-03-23"),
        ]
        engine.ingest(chunks)
        assert engine.stats()["total_chunks"] == 1

        deleted = engine.delete_by_path("notes/ideas/del.md")
        assert deleted == 1
        assert engine.stats()["total_chunks"] == 0

    def test_vector_search_disabled(self, engine):
        """FTS-only モードでベクトル検索が無効であることを確認。"""
        assert engine.vector_enabled is False
        stats = engine.stats()
        assert "disabled" in stats["vector_search"]
