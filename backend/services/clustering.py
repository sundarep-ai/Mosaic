"""
Shared embedding and clustering service for description similarity.

Used by:
- routes/expenses.py (similar-descriptions endpoint, description merge UI)
- routes/insights.py (recurring payment detection)
"""

import threading

import numpy as np

_embedding_model = None
_embedding_lock = threading.Lock()

# Descriptions are immutable strings, so a description -> embedding mapping
# never goes stale. Re-embedding every unique description on every call was
# the single biggest cost of the insights page (see
# review_order/09-insights-recurring-forecast.md, item 1).
_embedding_cache: dict[str, "np.ndarray"] = {}
_embedding_cache_lock = threading.Lock()


def get_embedding_model():
    """Lazy singleton for TextEmbedding model. Thread-safe initialization."""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                from fastembed import TextEmbedding
                _embedding_model = TextEmbedding()
    return _embedding_model


def _get_embeddings(descriptions: list[str]) -> list:
    """Return one embedding per description, computing (and caching) only
    the ones not already cached."""
    missing = [d for d in descriptions if d not in _embedding_cache]
    if missing:
        model = get_embedding_model()
        computed = list(model.embed(missing))
        with _embedding_cache_lock:
            for desc, emb in zip(missing, computed):
                _embedding_cache[desc] = emb
    return [_embedding_cache[d] for d in descriptions]


def _run_clustering(descriptions: list[str], threshold: float) -> list[list[int]]:
    """Core greedy embedding clustering. Returns all clusters including singletons.

    Each candidate j must be similar to ALL current cluster members (not just
    the seed) before it is admitted, preventing incoherent transitive groupings.
    """
    embeddings = _get_embeddings(descriptions)
    emb_matrix = np.array(embeddings)

    # Cosine similarity matrix
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = emb_matrix / norms
    sim_matrix = normalized @ normalized.T

    # Greedy clustering — j must be similar to every current member
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
            if all(sim_matrix[m][j] >= threshold for m in cluster):
                cluster.append(j)
                visited.add(j)
        clusters.append(cluster)

    return clusters


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
    return [c for c in _run_clustering(descriptions, threshold) if len(c) >= 2]


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
    return _run_clustering(descriptions, threshold)
