---
description: inbox/ の未処理アイテムをすべて分類・移動する
allowed-tools: Read, Write, Glob, Bash(mv:*), Bash(git:*)
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
5. git commit -m "process: YYYY-MM-DD"
