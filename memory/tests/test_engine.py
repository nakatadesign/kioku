"""engine のユニットテスト。"""

import pytest

from memory.chunker import Chunk
from memory.engine import Engine


@pytest.fixture
def engine(tmp_path):
    """テスト用 Engine（一時 DB）。"""
    db_path = tmp_path / "test.db"
    eng = Engine(db_path=db_path)
    yield eng
    eng.close()


def _make_chunk(path="notes/ideas/test.md", index=0, text="テスト", title="テスト", **kw):
    return Chunk(source_path=path, index=index, text=text, title=title,
                 tags=kw.get("tags", []), date=kw.get("date", "2026-03-23"))


class TestIngest:
    def test_基本挿入(self, engine):
        chunks = [_make_chunk(index=0, text="チャンク0"), _make_chunk(index=1, text="チャンク1")]
        assert engine.ingest(chunks) == 2
        assert engine.stats()["total_chunks"] == 2
        assert engine.stats()["total_files"] == 1

    def test_重複はスキップ(self, engine):
        chunk = _make_chunk(text="同じ内容")
        assert engine.ingest([chunk]) == 1
        assert engine.ingest([chunk]) == 0

    def test_内容変更で更新(self, engine):
        engine.ingest([_make_chunk(text="バージョン1")])
        assert engine.ingest([_make_chunk(text="バージョン2")]) == 1
        assert engine.stats()["total_chunks"] == 1

    def test_余剰チャンク削除(self, engine):
        """3チャンク→1チャンクに縮小したとき余剰が消える。"""
        path = "notes/ideas/shrink.md"
        engine.ingest([
            _make_chunk(path=path, index=0, text="チャンク0あいう"),
            _make_chunk(path=path, index=1, text="チャンク1かきく"),
            _make_chunk(path=path, index=2, text="チャンク2さしす"),
        ])
        assert engine.stats()["total_chunks"] == 3

        # 1チャンクだけで再 ingest
        engine.ingest([_make_chunk(path=path, index=0, text="チャンク0あいう")])
        assert engine.stats()["total_chunks"] == 1

    def test_余剰チャンクがFTS検索に残らない(self, engine):
        """削除されたチャンクのテキストが検索結果の snippet に含まれない。"""
        path = "notes/ideas/fts-test.md"
        engine.ingest([
            _make_chunk(path=path, index=0, text="アルファベットの歴史について"),
            _make_chunk(path=path, index=1, text="量子コンピュータの最新動向"),
        ])

        # 1チャンクに縮小（量子コンピュータのチャンクが消える）
        engine.ingest([_make_chunk(path=path, index=0, text="アルファベットの歴史について")])

        # DB 上に余剰チャンクが残っていないことを確認
        stats = engine.stats()
        assert stats["total_chunks"] == 1


class TestDeleteByPath:
    def test_パス指定削除(self, engine):
        engine.ingest([_make_chunk(path="notes/ideas/del.md", text="削除テスト")])
        assert engine.stats()["total_chunks"] == 1
        assert engine.delete_by_path("notes/ideas/del.md") == 1
        assert engine.stats()["total_chunks"] == 0

    def test_削除後に検索にヒットしない(self, engine):
        engine.ingest([_make_chunk(path="notes/ideas/gone.md", text="消えるノートです")])
        engine.delete_by_path("notes/ideas/gone.md")
        results = engine.search("消えるノート")
        assert len(results) == 0


class TestGetIndexedPaths:
    def test_登録パス一覧(self, engine):
        engine.ingest([_make_chunk(path="notes/ideas/a.md", text="ファイルA")])
        engine.ingest([_make_chunk(path="notes/tasks/b.md", text="ファイルB")])
        paths = engine.get_indexed_paths()
        assert paths == {"notes/ideas/a.md", "notes/tasks/b.md"}

    def test_削除後はパスから消える(self, engine):
        engine.ingest([_make_chunk(path="notes/ideas/c.md", text="ファイルC")])
        engine.delete_by_path("notes/ideas/c.md")
        assert "notes/ideas/c.md" not in engine.get_indexed_paths()


class TestSearch:
    def test_FTS検索(self, engine):
        engine.ingest([
            _make_chunk(path="notes/ideas/a.md", text="自動化ツールの設計メモ", title="自動化"),
            _make_chunk(path="notes/research/b.md", text="天気予報のAPIについて", title="天気"),
        ])
        results = engine.search("自動化ツール")
        assert len(results) >= 1
        assert results[0].source_path == "notes/ideas/a.md"

    def test_private除外(self, engine):
        engine.ingest([
            _make_chunk(path="notes/ideas/secret.md", text="機密情報です", title="秘密", tags=["#private"]),
            _make_chunk(path="notes/ideas/public.md", text="公開情報です", title="公開"),
        ])
        results = engine.search("情報です")
        paths = [r.source_path for r in results]
        assert "notes/ideas/secret.md" not in paths


class TestStats:
    def test_動作モードが返る(self, engine):
        s = engine.stats()
        assert s["vector_search"] in (
            "enabled",
            "disabled (sqlite-vec unavailable in this Python build)",
        )
        assert s["fts_tokenizer"] in ("trigram", "unicode61 (fallback)")
        assert s["total_chunks"] == 0
        assert s["total_files"] == 0
