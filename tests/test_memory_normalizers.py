from __future__ import annotations

from pathlib import Path

import pytest

from spark_researcher.memory import (
    MAX_DOCUMENT_STEM_LENGTH,
    MAX_QUERY_LENGTH,
    MAX_RESULTS_LIMIT,
    _bounded_document_stem,
    _normalize_limit,
    _normalize_query,
    _safe_slug,
    _trim_document_stem,
    _unique_document_path,
)


def test_safe_slug_replaces_punctuation_with_hyphens() -> None:
    assert _safe_slug("hello world / now") == "hello-world-now"


def test_safe_slug_falls_back_to_item_when_empty() -> None:
    assert _safe_slug("!!!") == "item"
    assert _safe_slug("   ") == "item"


def test_bounded_document_stem_returns_raw_when_under_limit() -> None:
    assert _bounded_document_stem("short-name") == "short-name"


def test_bounded_document_stem_truncates_and_hashes_long_names() -> None:
    long_value = "x" * 200
    stem = _bounded_document_stem(long_value)
    assert len(stem) <= MAX_DOCUMENT_STEM_LENGTH
    # the suffix is a 12-char sha1 prefix joined by a hyphen
    assert stem.startswith("x")
    assert "-" in stem
    head, _, digest = stem.rpartition("-")
    assert len(digest) == 12
    assert head.startswith("x")


def test_trim_document_stem_clamps_to_minimum_one() -> None:
    assert _trim_document_stem("name", limit=0) == "name"[:1]


def test_trim_document_stem_strips_trailing_punctuation() -> None:
    assert _trim_document_stem("abcd---", limit=6) == "abcd"


def test_unique_document_path_appends_index_when_taken(tmp_path: Path) -> None:
    used: set[str] = set()
    first = _unique_document_path(tmp_path, "doc", used)
    second = _unique_document_path(tmp_path, "doc", used)
    third = _unique_document_path(tmp_path, "doc", used)
    assert first.name == "doc.md"
    assert second.name == "doc-2.md"
    assert third.name == "doc-3.md"


def test_normalize_query_collapses_whitespace() -> None:
    assert _normalize_query("  hello   world  ") == "hello world"


def test_normalize_query_rejects_empty_input() -> None:
    with pytest.raises(RuntimeError):
        _normalize_query("   ")


def test_normalize_query_rejects_overly_long_input() -> None:
    with pytest.raises(RuntimeError, match="too long"):
        _normalize_query("a" * (MAX_QUERY_LENGTH + 1))


def test_normalize_limit_clamps_low_and_high() -> None:
    assert _normalize_limit(0) == 1
    assert _normalize_limit(-5) == 1
    assert _normalize_limit(MAX_RESULTS_LIMIT + 50) == MAX_RESULTS_LIMIT
    assert _normalize_limit(5) == 5
