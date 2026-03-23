"""Markdown → チャンク分割。YAML フロントマター抽出付き。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import CHUNK_MAX_CHARS, CHUNK_OVERLAP_CHARS


@dataclass
class Chunk:
    """1チャンクの情報を保持する。"""
    source_path: str  # KIOKU_ROOT からの相対パス
    index: int  # 同一ファイル内のチャンク番号（0始まり）
    text: str  # チャンクのテキスト
    title: str = ""
    tags: list[str] = field(default_factory=list)
    date: str = ""  # YAML の date、またはファイル名から推定


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """YAML フロントマターをパースして (metadata, body) を返す。

    簡易実装: key: value の単純な行のみ対応。
    ネスト構造やリスト記法は非対応（kioku のノートは単純構造を前提）。
    """
    metadata: dict[str, str] = {}
    body = content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if match:
        raw = match.group(1)
        for line in raw.splitlines():
            m = re.match(r"^(\w[\w-]*)\s*:\s*(.+)$", line.strip())
            if m:
                metadata[m.group(1)] = m.group(2).strip()
        body = content[match.end():]

    return metadata, body


def _extract_date_from_path(path: str) -> str:
    """ファイル名から YYYY-MM-DD を推定する。"""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path)
    return m.group(1) if m else ""


def _split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """テキストをチャンクに分割する。段落境界を優先する。"""
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks: list[str] = []
    paragraphs = re.split(r"\n{2,}", text)
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # 段落自体が max_chars を超える場合は強制分割
            if len(para) > max_chars:
                start = 0
                while start < len(para):
                    chunks.append(para[start:start + max_chars])
                    start += max_chars - overlap
            else:
                current = para
                continue
            current = ""

    if current.strip():
        chunks.append(current)

    return chunks


def chunk_file(path: Path, kioku_root: Path) -> list[Chunk]:
    """Markdown ファイルを読んでチャンクのリストを返す。"""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    relative = str(path.relative_to(kioku_root))
    metadata, body = _parse_frontmatter(content)

    title = metadata.get("title", path.stem)
    tags_raw = metadata.get("tags", "")
    tags = [t.strip() for t in re.split(r"[,\s]+", tags_raw) if t.strip()]
    date = metadata.get("date", _extract_date_from_path(relative))

    text_chunks = _split_text(body, CHUNK_MAX_CHARS, CHUNK_OVERLAP_CHARS)

    return [
        Chunk(
            source_path=relative,
            index=i,
            text=text,
            title=title,
            tags=tags,
            date=date,
        )
        for i, text in enumerate(text_chunks)
    ]
