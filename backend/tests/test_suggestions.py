"""Tests for category suggestion and description management."""

from conftest import make_expense


def test_suggest_category_no_history(auth_client_a):
    resp = auth_client_a.get("/api/suggest-category?description=random stuff")
    assert resp.status_code == 200
    assert resp.json()["category"] is None


def test_suggest_category_short_keywords_ignored(auth_client_a):
    """Keywords shorter than 3 chars are ignored, so no match."""
    resp = auth_client_a.get("/api/suggest-category?description=ab cd")
    assert resp.json()["category"] is None


def test_suggest_category_with_history(auth_client_a):
    for _ in range(3):
        auth_client_a.post("/api/expenses", json=make_expense(
            description="Walmart groceries", category="Groceries",
        ))
    resp = auth_client_a.get("/api/suggest-category?description=Walmart shopping")
    assert resp.json()["category"] == "Groceries"


def test_suggest_category_frequency_weighted(auth_client_a):
    """The more frequent category wins when keyword matches multiple categories."""
    for _ in range(3):
        auth_client_a.post("/api/expenses", json=make_expense(
            description="Walmart groceries", category="Groceries",
        ))
    auth_client_a.post("/api/expenses", json=make_expense(
        description="Walmart electronics", category="Shopping",
    ))
    resp = auth_client_a.get("/api/suggest-category?description=Walmart")
    assert resp.json()["category"] == "Groceries"


def test_unique_descriptions(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Tim Hortons", category="Dining"))

    data = auth_client_a.get("/api/unique-descriptions").json()
    descs = {d["description"]: d["count"] for d in data}
    assert descs["Walmart"] == 2
    assert descs["Tim Hortons"] == 1


def test_merge_descriptions(auth_client_a):
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Wal-Mart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="WalMart", category="Groceries"))

    resp = auth_client_a.post("/api/merge-descriptions", json={
        "merges": [{
            "target": "Walmart",
            "sources": ["Wal-Mart", "WalMart"],
            "category": "Groceries",
        }],
    })
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2

    # Verify all are now "Walmart"
    expenses = auth_client_a.get("/api/expenses").json()
    assert all(e["description"] == "Walmart" for e in expenses)


def test_dismiss_merge(auth_client_a):
    """Dismissing a merge suggestion persists and returns count."""
    resp = auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{
            "category": "Groceries",
            "canonical": "Walmart",
            "variants": ["Wal-Mart", "WalMart"],
        }],
    })
    assert resp.status_code == 200
    assert resp.json()["dismissed"] == 2


def test_dismiss_merge_idempotent(auth_client_a):
    """Dismissing the same pair twice doesn't create duplicates."""
    payload = {
        "dismissals": [{
            "category": "Groceries",
            "canonical": "Walmart",
            "variants": ["Wal-Mart"],
        }],
    }
    auth_client_a.post("/api/dismiss-merge", json=payload)
    resp = auth_client_a.post("/api/dismiss-merge", json=payload)
    assert resp.json()["dismissed"] == 0  # already exists


def test_list_dismissed_merges(auth_client_a):
    """Dismissed merges appear in the listing endpoint."""
    auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{
            "category": "Groceries",
            "canonical": "Walmart",
            "variants": ["Wal-Mart"],
        }],
    })
    resp = auth_client_a.get("/api/dismissed-merges")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["category"] == "Groceries"
    assert len(data[0]["pairs"]) == 1


def test_undismiss_merge(auth_client_a):
    """Undismissing restores the pair for future suggestions."""
    auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{
            "category": "Groceries",
            "canonical": "Walmart",
            "variants": ["Wal-Mart"],
        }],
    })
    dismissed = auth_client_a.get("/api/dismissed-merges").json()
    pair_id = dismissed[0]["pairs"][0]["id"]

    resp = auth_client_a.post("/api/undismiss-merge", json={"ids": [pair_id]})
    assert resp.status_code == 200
    assert resp.json()["undismissed"] == 1

    # Verify it's gone from the list
    dismissed_after = auth_client_a.get("/api/dismissed-merges").json()
    assert len(dismissed_after) == 0


def test_dismiss_merge_pair_order_independent(auth_client_a):
    """Dismissing (A, B) and (B, A) should be treated as the same pair."""
    auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{
            "category": "Groceries",
            "canonical": "Walmart",
            "variants": ["Wal-Mart"],
        }],
    })
    # Dismiss with reversed order
    resp = auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{
            "category": "Groceries",
            "canonical": "Wal-Mart",
            "variants": ["Walmart"],
        }],
    })
    assert resp.json()["dismissed"] == 0  # same pair, already dismissed


# ── similar-descriptions suppression (bucket 08, item 8) ─────────────────
# Every test above verifies dismissals *persist* (create/list/undismiss),
# but none of them verify a dismissal actually does its one job: keeping
# the pair out of /api/similar-descriptions' suggestions. cluster_descriptions
# is monkeypatched to a fixed grouping so these don't depend on the real
# embedding model's exact similarity scores — only on the suppression logic
# in routes/expenses.py's similar_descriptions().


def _force_one_cluster(monkeypatch, size):
    import routes.expenses as expenses_mod
    monkeypatch.setattr(expenses_mod, "cluster_descriptions", lambda descriptions, threshold: [list(range(size))])


def _flat_groups(response_json):
    """/api/similar-descriptions nests groups per category:
    [{"category": ..., "groups": [{"canonical": ..., "variants": [...]}]}]."""
    return [g for cat in response_json for g in cat["groups"]]


def test_similar_descriptions_suggests_when_not_dismissed(auth_client_a, monkeypatch):
    _force_one_cluster(monkeypatch, 2)
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Wal-Mart", category="Groceries"))

    groups = _flat_groups(auth_client_a.get("/api/similar-descriptions").json())
    walmart_group = next(g for g in groups if g["canonical"] == "Walmart")
    assert "Wal-Mart" in walmart_group["variants"]


def test_similar_descriptions_suppresses_dismissed_pair(auth_client_a, monkeypatch):
    """The one thing a dismissal exists to do: once dismissed, the exact
    same clustering must stop offering that pair as a suggestion."""
    _force_one_cluster(monkeypatch, 2)
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Wal-Mart", category="Groceries"))

    auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{"category": "Groceries", "canonical": "Walmart", "variants": ["Wal-Mart"]}],
    })

    groups = _flat_groups(auth_client_a.get("/api/similar-descriptions").json())
    assert not any(
        g["canonical"] == "Walmart" and "Wal-Mart" in g["variants"] for g in groups
    )


def test_similar_descriptions_suppresses_only_the_dismissed_variant(auth_client_a, monkeypatch):
    """Dismissing one variant of a 3-way cluster must not suppress the
    others — only the specific dismissed pair is excluded."""
    _force_one_cluster(monkeypatch, 3)
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Wal-Mart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="WalMart Inc", category="Groceries"))

    auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{"category": "Groceries", "canonical": "Walmart", "variants": ["Wal-Mart"]}],
    })

    groups = _flat_groups(auth_client_a.get("/api/similar-descriptions").json())
    walmart_group = next(g for g in groups if g["canonical"] == "Walmart")
    assert "Wal-Mart" not in walmart_group["variants"]
    assert "WalMart Inc" in walmart_group["variants"]


def test_similar_descriptions_drops_group_entirely_once_all_variants_dismissed(auth_client_a, monkeypatch):
    """If every variant in a cluster has been dismissed, the group must not
    appear at all (an empty-variants suggestion is meaningless noise)."""
    _force_one_cluster(monkeypatch, 2)
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Walmart", category="Groceries"))
    auth_client_a.post("/api/expenses", json=make_expense(description="Wal-Mart", category="Groceries"))

    auth_client_a.post("/api/dismiss-merge", json={
        "dismissals": [{"category": "Groceries", "canonical": "Walmart", "variants": ["Wal-Mart"]}],
    })

    groups = _flat_groups(auth_client_a.get("/api/similar-descriptions").json())
    assert not any(g["canonical"] == "Walmart" for g in groups)
