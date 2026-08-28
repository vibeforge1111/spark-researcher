from __future__ import annotations

from spark_researcher.research import _bounded_research_text, _research_task


def test_ampersand_passes_through_unescaped():
    result = _bounded_research_text("AT&T research findings", limit=200)
    assert "&amp;" not in result
    assert "AT&T" in result


def test_less_than_passes_through_unescaped():
    result = _bounded_research_text("value < threshold", limit=200)
    assert "&lt;" not in result
    assert "<" in result


def test_greater_than_passes_through_unescaped():
    result = _bounded_research_text("score > 90%", limit=200)
    assert "&gt;" not in result
    assert ">" in result


def test_all_html_special_chars_unescaped():
    text = "A&B <test> C>D"
    result = _bounded_research_text(text, limit=200)
    assert "&amp;" not in result
    assert "&lt;" not in result
    assert "&gt;" not in result
    assert "&" in result
    assert "<" in result
    assert ">" in result


def test_llm_prompt_content_contains_original_text():
    item = {
        "note_id": "note-1",
        "title": "AT&T Research <2024>",
        "snippet": "Growth > 10% & rising",
        "domain": "research.com",
        "url": "https://research.com/at&t",
    }
    research = {
        "query": "AT&T research",
        "collected_at": "2026-06-02T00:00:00+00:00",
        "citations": [item],
    }
    prompt = _research_task("find AT&T data", research)
    assert "&amp;" not in prompt
    assert "&lt;" not in prompt
    assert "&gt;" not in prompt


def test_limit_still_applied():
    long_text = "A" * 300
    result = _bounded_research_text(long_text, limit=50)
    assert len(result) <= 50
    assert result.endswith("...")


def test_clean_text_unchanged():
    text = "normal research text without special characters"
    result = _bounded_research_text(text, limit=200)
    assert result == text
