"""Unit tests for the description-clustering algorithm (bucket 08, item 6).

_run_clustering had no test of its own — every "recurring detection" test
elsewhere in the suite uses a single unique description per merchant, which
short-circuits before more than one description ever needs to cluster
together, so the actual join rule was never exercised. These tests replace
the real embedding model with hand-built 2D unit vectors (cosine similarity
between two unit vectors at angle theta is exactly cos(theta)), giving full
control over which descriptions are "similar" without downloading or running
the real ONNX model.
"""

import math

import numpy as np

import services.clustering as clustering_mod
from services.clustering import _run_clustering, cluster_descriptions, cluster_descriptions_all


class _FakeModel:
    def __init__(self, vectors):
        self._vectors = vectors

    def embed(self, descriptions):
        assert len(descriptions) == len(self._vectors), (
            "test wiring bug: fake model given a different number of "
            "descriptions than it has vectors for"
        )
        return self._vectors


def _unit_vector(angle_degrees: float) -> np.ndarray:
    theta = math.radians(angle_degrees)
    return np.array([math.cos(theta), math.sin(theta)])


def _patch_model(monkeypatch, vectors):
    monkeypatch.setattr(clustering_mod, "get_embedding_model", lambda: _FakeModel(vectors))


def test_run_clustering_requires_similarity_to_every_member(monkeypatch):
    """The join rule is "similar to every current cluster member", not a
    chain join through the most-recently-added one. A(0°) and B(20°) are
    mutually similar (cos 20° ≈ 0.94); B(20°) and C(40°) are also mutually
    similar (cos 20° again) — but A and C are 40° apart (cos 40° ≈ 0.77),
    below threshold. A naive chain-join (only checking the seed or the last
    member) would pull C into [A, B]; the real "must match every member"
    rule must instead leave C on its own."""
    vectors = [_unit_vector(0), _unit_vector(20), _unit_vector(40), _unit_vector(95)]
    _patch_model(monkeypatch, vectors)

    clusters = _run_clustering(["Alpha", "Beta", "Gamma", "Delta"], threshold=0.9)

    assert clusters == [[0, 1], [2], [3]]


def test_run_clustering_forms_one_cluster_when_all_pairs_agree(monkeypatch):
    """When every pair genuinely is similar (three descriptions within a
    tight 10° arc), all three must join a single cluster, not fragment."""
    vectors = [_unit_vector(0), _unit_vector(5), _unit_vector(10)]
    _patch_model(monkeypatch, vectors)

    clusters = _run_clustering(["Costco", "Costco Wholesale", "Costco #452"], threshold=0.9)

    assert clusters == [[0, 1, 2]]


def test_run_clustering_all_dissimilar_are_singletons(monkeypatch):
    vectors = [_unit_vector(0), _unit_vector(90), _unit_vector(180)]
    _patch_model(monkeypatch, vectors)

    clusters = _run_clustering(["Rent", "Netflix", "Gas Station"], threshold=0.9)

    assert clusters == [[0], [1], [2]]


def test_run_clustering_boundary_similarity_counts_as_a_match(monkeypatch):
    """Similarity exactly equal to the threshold must join (>=, not >)."""
    theta_deg = math.degrees(math.acos(0.9))
    vectors = [_unit_vector(0), _unit_vector(theta_deg)]
    _patch_model(monkeypatch, vectors)

    clusters = _run_clustering(["A", "B"], threshold=0.9)

    assert clusters == [[0, 1]]


def test_cluster_descriptions_drops_singletons(monkeypatch):
    """cluster_descriptions (used by the merge-suggestion UI) only wants
    groups of 2+ — singletons aren't actionable merge suggestions."""
    vectors = [_unit_vector(0), _unit_vector(20), _unit_vector(95)]
    _patch_model(monkeypatch, vectors)

    clusters = cluster_descriptions(["Costco run", "Costco trip", "Netflix"], threshold=0.9)

    assert clusters == [[0, 1]]


def test_cluster_descriptions_all_keeps_singletons(monkeypatch):
    """cluster_descriptions_all (used by insights' recurring detection) must
    still assign every description to a group, including groups of one."""
    vectors = [_unit_vector(0), _unit_vector(20), _unit_vector(95)]
    _patch_model(monkeypatch, vectors)

    clusters = cluster_descriptions_all(["Costco run", "Costco trip", "Netflix"], threshold=0.9)

    assert clusters == [[0, 1], [2]]
