---
description: inbox/ の未処理アイテムをすべて分類・移動する
allowed-tools: Read, Write, Glob, Bash(mv:*), Bash(git:*), Bash(python:*)
---
inbox/ 内の全 .md ファイルを処理する:
1. 各ファイルの内容を読んで種別を判定（ideas / tasks / research / log）
2. YAML フロントマターを付与（title, date, tags, type）
3. 適切なディレクトリに移動:
   - ideas → notes/ideas/YYYY-MM-DD-slug.md
   - tasks → notes/tasks/YYYY-MM-DD-slug.md
   - research → notes/research/YYYY-MM-DD-slug.md
   - log → daily/YYYY-MM-DD.md にマージ
4. 処理済みの inbox ファイルを削除
5. memory インデックス更新（オプショナル）:
   - memory/data/kioku.db が存在する場合のみ実行
   - 移動した各ファイルに対して以下を実行:
     ```
     memory/.venv/bin/python -m memory.cli ingest <移動先パス>
     ```
   - memory 未セットアップ（kioku.db なし）の場合はこのステップを丸ごとスキップ（警告なし）
   - ingest がエラーになっても process は正常に続行する（エラーはログに残す）
6. git commit -m "process: YYYY-MM-DD"
