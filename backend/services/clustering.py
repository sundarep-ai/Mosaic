"""
Shared embedding and clustering service for description similarity.

Used by:
- routes/expenses.py (similar-descriptions endpoint, description merge UI)
- routes/insights.py (recurring payment detection)
"""

import threading
from typing import Optional

import numpy as np

_embedding_model = None
_embedding_lock = threading.Lock()


def get_embedding_model():
    """Lazy singleton for TextEmbedding model. Thread-safe initialization."""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                from fastembed import TextEmbedding
                _embedding_model = TextEmbedding()
    return _embedding_model


def cluster_descriptions(
    descriptions: list[str],
    threshold: float = 0.85,
) -> list[list[int]]:
    """Cluster descriptions by embedding cosine similarity.

    Args:
        descriptions: List of description strings to cluster.
        threshold: Minimum cosine similarity to group together (0.5-1.0).

    Returns:
        List of clusters, where each cluster is a list of indices into
        the input descriptions list. Only clusters with 2+ members are
        returned. Singletons are omitted.
    """
    if len(descriptions) < 2:
        return []

    model = get_embedding_model()
    embeddings = list(model.embed(descriptions))
    emb_matrix = np.array(embeddings)

    # Cosine similarity matrix
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = emb_matrix / norms
    sim_matrix = normalized @ normalized.T

    # Greedy clustering
    visited: set[int] = set()
    clusters: list[list[int]] = []
    for i in range(len(descriptions)):
        if i in visited:
            continue
        cluster = [i]
        visited.add(i)
        for j in range(i + 1, len(descriptions)):
            if j in visited:
                continue
            if sim_matrix[i][j] >= threshold:
                cluster.append(j)
                visited.add(j)
        if len(cluster) >= 2:
            clusters.append(cluster)

    return clusters


def cluster_descriptions_all(
    descriptions: list[str],
    threshold: float = 0.85,
) -> list[list[int]]:
    """Like cluster_descriptions but also returns singleton clusters.

    Useful for insights where every description needs to be assigned
    to a group (including groups of one).
    """
    if not descriptions:
        return []
    if len(descriptions) == 1:
        return [[0]]

    model = get_embedding_model()
    embeddings = list(model.embed(descriptions))
    emb_matrix = np.array(embeddings)

    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = emb_matrix / norms
    sim_matrix = normalized @ normalized.T

    visited: set[int] = set()
    clusters: list[list[int]] = []
    for i in range(len(descriptions)):
        if i in visited:
            continue
        cluster = [i]
        visited.add(i)
        for j in range(i + 1, len(descriptions)):
            if j in visited:
                continue
            if sim_matrix[i][j] >= threshold:
                cluster.append(j)
                visited.add(j)
        clusters.append(cluster)

    return clusters
