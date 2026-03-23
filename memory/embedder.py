"""Ruri v3-130m ラッパー。ベクトル検索無効時はロードしない。"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from .config import MODEL_NAME

logger = logging.getLogger(__name__)

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model

    from sentence_transformers import SentenceTransformer
    logger.info("Ruri v3-130m をロード中...")
    _model = SentenceTransformer(MODEL_NAME)
    logger.info("Ruri v3-130m ロード完了")
    return _model


def embed_documents(texts: list[str]) -> Optional[np.ndarray]:
    """ドキュメントテキストを埋め込みベクトルに変換する。"""
    if not texts:
        return None
    model = _load_model()
    return model.encode(texts, prompt_name="document", normalize_embeddings=True)


def embed_query(query: str) -> Optional[np.ndarray]:
    """クエリテキストを埋め込みベクトルに変換する。"""
    model = _load_model()
    result = model.encode([query], prompt_name="query", normalize_embeddings=True)
    return result[0]


def get_dimension() -> int:
    """埋め込みベクトルの次元数を返す。"""
    return 512  # Ruri v3-130m は固定512次元
