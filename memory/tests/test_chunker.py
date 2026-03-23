"""chunker のユニットテスト。"""

from pathlib import Path
from textwrap import dedent

import pytest

from memory.chunker import Chunk, _parse_frontmatter, _split_text, chunk_file


class TestParseFrontmatter:
    def test_フロントマターあり(self):
        content = dedent("""\
            ---
            title: テストノート
            date: 2026-03-23
            tags: idea, automation
            ---
            本文です。
        """)
        meta, body = _parse_frontmatter(content)
        assert meta["title"] == "テストノート"
        assert meta["date"] == "2026-03-23"
        assert meta["tags"] == "idea, automation"
        assert body.strip() == "本文です。"

    def test_フロントマターなし(self):
        content = "単なるテキスト\n次の行"
        meta, body = _parse_frontmatter(content)
        assert meta == {}
        assert body == content


class TestSplitText:
    def test_短いテキストは分割しない(self):
        result = _split_text("短いテキスト", max_chars=1000, overlap=100)
        assert len(result) == 1
        assert result[0] == "短いテキスト"

    def test_空テキストは空リスト(self):
        result = _split_text("", max_chars=1000, overlap=100)
        assert result == []

    def test_段落境界で分割(self):
        text = "段落1\n\n段落2\n\n段落3"
        result = _split_text(text, max_chars=10, overlap=2)
        assert len(result) >= 2


class TestChunkFile:
    def test_存在しないファイル(self, tmp_path):
        result = chunk_file(tmp_path / "nonexistent.md", tmp_path)
        assert result == []

    def test_正常なファイル(self, tmp_path):
        md = tmp_path / "notes" / "ideas" / "2026-03-23-test.md"
        md.parent.mkdir(parents=True)
        md.write_text(dedent("""\
            ---
            title: テストアイデア
            tags: idea
            ---
            これはテストのアイデアです。

            詳細な説明がここに入ります。
        """), encoding="utf-8")

        chunks = chunk_file(md, tmp_path)
        assert len(chunks) >= 1
        assert chunks[0].title == "テストアイデア"
        assert chunks[0].date == "2026-03-23"
        assert "idea" in chunks[0].tags
