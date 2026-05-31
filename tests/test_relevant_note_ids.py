"""Regression: _relevant_note_ids must return note IDs with score >= 1 (not >= 2)."""

from __future__ import annotations

from spark_researcher.verifier import _overlap_tokens, _relevant_note_ids


def _make_advisory(citations: list[dict]) -> dict:
    return {"research_context": {"citations": citations}}


# ---------------------------------------------------------------------------
# Threshold inclusion tests
# ---------------------------------------------------------------------------


def test_score_1_note_is_returned():
    """A note with exactly 1 overlapping content token must be returned (the fix)."""
    advisory = _make_advisory([
        {"note_id": "note-1", "title": "Spark Runtime", "snippet": "zeta deployment"}
    ])
    draft = "zeta was used in the deployment pipeline."
    result = _relevant_note_ids(advisory, draft)
    assert "note-1" in result, f"score-1 note must be returned, got {result}"


def test_score_2_note_is_returned():
    """A note with score=2 must also be returned — higher scores are included."""
    advisory = _make_advisory([
        {"note_id": "note-2", "title": "Spark Runtime Engine", "snippet": "runtime"}
    ])
    draft = "the spark runtime engine is the core component."
    result = _relevant_note_ids(advisory, draft)
    assert "note-2" in result, f"score-2 note must be returned, got {result}"


def test_score_0_note_is_excluded():
    """A note with zero overlapping tokens must NOT be returned."""
    advisory = _make_advisory([
        {"note_id": "note-zero", "title": "Alpha Beta", "snippet": "alpha beta gamma"}
    ])
    draft = "completely different content with none of those terms."
    result = _relevant_note_ids(advisory, draft)
    assert "note-zero" not in result, f"zero-overlap note must be excluded, got {result}"


def test_higher_overlap_note_preferred():
    """Notes with higher overlap scores must appear before lower-score notes."""
    advisory = _make_advisory([
        {"note_id": "low", "title": "Delta", "snippet": "delta"},
        {"note_id": "high", "title": "Alpha Beta Gamma Delta", "snippet": "alpha beta gamma delta"},
    ])
    draft = "alpha beta gamma delta are all mentioned here."
    result = _relevant_note_ids(advisory, draft, limit=2)
    assert result.index("high") < result.index("low"), f"high-overlap note must rank first, got {result}"


# ---------------------------------------------------------------------------
# Unsafe / malformed note exclusion tests (hostile input)
# ---------------------------------------------------------------------------


def test_non_dict_citation_is_excluded():
    """Hostile: a citation that is not a dict must be silently skipped — no crash, no inclusion."""
    advisory = {"research_context": {"citations": ["not-a-dict", 42, None]}}
    draft = "some relevant content about deployment"
    result = _relevant_note_ids(advisory, draft)
    assert result == [], f"non-dict citations must be excluded, got {result}"


def test_missing_note_id_citation_is_excluded():
    """Hostile: a dict citation with empty or missing note_id must not appear in results."""
    advisory = _make_advisory([
        {"note_id": "", "title": "Spark Runtime", "snippet": "deployment pipeline"},
        {"title": "Engine Notes", "snippet": "deployment pipeline"},
    ])
    draft = "the deployment pipeline runs on the engine."
    result = _relevant_note_ids(advisory, draft)
    assert result == [], f"citations with missing note_id must be excluded, got {result}"


def test_empty_draft_returns_no_results():
    """Hostile: an empty draft text must return an empty list (no tokens to match)."""
    advisory = _make_advisory([
        {"note_id": "note-x", "title": "Spark Engine", "snippet": "runtime deployment"}
    ])
    result = _relevant_note_ids(advisory, "")
    assert result == [], f"empty draft must return empty list, got {result}"


def test_result_contains_only_note_ids_not_body_content():
    """Results must be a list of note ID strings only — no note title, snippet, or body content."""
    advisory = _make_advisory([
        {"note_id": "safe-id-001", "title": "Spark Runtime Engine", "snippet": "deployment runtime"}
    ])
    draft = "the spark runtime engine handles deployment."
    result = _relevant_note_ids(advisory, draft)
    assert "safe-id-001" in result
    for item in result:
        assert isinstance(item, str), f"result items must be strings, got {type(item)}"
        assert "Spark Runtime Engine" not in item, "note title must not appear in result"
        assert "deployment runtime" not in item, "note snippet must not appear in result"


def test_limit_caps_output():
    """Results must be capped at the limit parameter even when more notes are relevant."""
    citations = [
        {"note_id": f"note-{i}", "title": f"Spark Engine Module {i}", "snippet": f"runtime deployment engine module {i}"}
        for i in range(5)
    ]
    advisory = _make_advisory(citations)
    draft = "spark engine runtime deployment module for all five items."
    result = _relevant_note_ids(advisory, draft, limit=2)
    assert len(result) <= 2, f"result must respect limit=2, got {len(result)} items: {result}"


# ---------------------------------------------------------------------------
# Token filter tests
# ---------------------------------------------------------------------------


def test_overlap_tokens_filters_short_tokens():
    """_overlap_tokens must exclude tokens shorter than 4 characters."""
    tokens = _overlap_tokens("the cat sat")
    assert not any(len(t) < 4 for t in tokens), f"short tokens leaked: {tokens}"


def test_overlap_tokens_filters_stopwords():
    """_overlap_tokens must exclude known stopword tokens."""
    tokens = _overlap_tokens("about after before from with")
    assert len(tokens) == 0, f"stopwords should be filtered out, got {tokens}"
