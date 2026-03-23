"""kioku セマンティック記憶エンジン — CLI エントリポイント。

使い方:
    uv run python -m memory.cli reindex
    uv run python -m memory.cli ingest <path>
    uv run python -m memory.cli search "クエリ"
    uv run python -m memory.cli stats
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from .chunker import chunk_file
from .config import DEFAULT_LIMIT, INDEX_DIRS, KIOKU_ROOT
from .engine import Engine

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_reindex(args: argparse.Namespace) -> None:
    """notes/ と daily/ の全ファイルをインデックスに登録する。"""
    engine = Engine()
    total_files = 0
    total_chunks = 0

    t0 = time.time()
    for dir_name in INDEX_DIRS:
        target_dir = KIOKU_ROOT / dir_name
        if not target_dir.exists():
            logger.info(f"{dir_name}/ が見つかりません。スキップします。")
            continue

        for md_file in sorted(target_dir.rglob("*.md")):
            if md_file.name == ".gitkeep":
                continue
            chunks = chunk_file(md_file, KIOKU_ROOT)
            if chunks:
                inserted = engine.ingest(chunks)
                total_files += 1
                total_chunks += inserted
                if inserted > 0:
                    logger.info(f"  {md_file.relative_to(KIOKU_ROOT)} → {inserted} チャンク")

    elapsed = time.time() - t0
    engine.close()
    print(f"\nreindex 完了: {total_files} ファイル, {total_chunks} チャンク ({elapsed:.1f}s)")


def cmd_ingest(args: argparse.Namespace) -> None:
    """指定ファイルをインデックスに追加/更新する。"""
    path = Path(args.path).resolve()
    if not path.exists():
        logger.error(f"ファイルが見つかりません: {path}")
        sys.exit(1)

    engine = Engine()
    chunks = chunk_file(path, KIOKU_ROOT)
    if not chunks:
        logger.info("チャンクが生成されませんでした。")
        engine.close()
        return

    inserted = engine.ingest(chunks)
    engine.close()
    print(f"ingest 完了: {path.name} → {inserted} チャンク")


def cmd_search(args: argparse.Namespace) -> None:
    """意味検索を実行する。"""
    engine = Engine()
    t0 = time.time()
    results = engine.search(args.query, limit=args.limit)
    elapsed = time.time() - t0

    if args.json:
        output = [
            {
                "source_path": r.source_path,
                "title": r.title,
                "score": round(r.score, 6),
                "snippet": r.snippet,
                "date": r.date,
            }
            for r in results
        ]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if not results:
            print("該当するノートが見つかりませんでした。")
        else:
            for i, r in enumerate(results, 1):
                print(f"\n{'─' * 60}")
                print(f"  [{i}] {r.title}")
                print(f"      パス: {r.source_path}")
                print(f"      日付: {r.date}  スコア: {r.score:.4f}")
                print(f"      {r.snippet[:120]}...")
            print(f"\n{'─' * 60}")
        print(f"検索時間: {elapsed:.3f}s  件数: {len(results)}")

    engine.close()


def cmd_stats(args: argparse.Namespace) -> None:
    """統計情報を表示する。"""
    engine = Engine()
    s = engine.stats()
    engine.close()

    print("=== kioku memory stats ===")
    print(f"  ファイル数:       {s['total_files']}")
    print(f"  チャンク数:       {s['total_chunks']}")
    print(f"  ベクトル検索:     {s['vector_search']}")
    print(f"  FTS tokenizer:   {s['fts_tokenizer']}")
    print(f"  DB パス:          {s['db_path']}")
    print(f"  DB サイズ:        {s['db_size_mb']} MB")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="memory",
        description="kioku セマンティック記憶エンジン CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # reindex
    sub.add_parser("reindex", help="notes/ と daily/ を全インデックス")

    # ingest
    p_ingest = sub.add_parser("ingest", help="個別ファイルをインデックスに追加/更新")
    p_ingest.add_argument("path", help="対象の Markdown ファイルパス")

    # search
    p_search = sub.add_parser("search", help="意味検索")
    p_search.add_argument("query", nargs="?", help="検索クエリ")
    p_search.add_argument("--query", dest="query_opt", help="検索クエリ（--query 形式）")
    p_search.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="結果件数上限")
    p_search.add_argument("--json", action="store_true", help="JSON 形式で出力")

    # stats
    sub.add_parser("stats", help="統計情報を表示")

    args = parser.parse_args()

    # search の --query と positional を統合
    if args.command == "search":
        if args.query_opt:
            args.query = args.query_opt
        if not args.query:
            parser.error("検索クエリを指定してください")

    commands = {
        "reindex": cmd_reindex,
        "ingest": cmd_ingest,
        "search": cmd_search,
        "stats": cmd_stats,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
