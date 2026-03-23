---
title: セマンティック検索の設計調査
date: 2026-03-21
tags: research, memory, search
---
sui-memory の設計を参考にしたセマンティック検索の実装方針。
FTS5 trigram + sqlite-vec + RRF による統合検索。
日本語特化の Ruri v3 モデルを使用する。
