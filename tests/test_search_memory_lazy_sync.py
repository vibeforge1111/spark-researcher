import pytest
from pathlib import Path


def test_sync_skipped_when_manifest_exists(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{\"entries\": []}", encoding="utf-8")
    sync_calls = []

    def fake_sync(*args, **kwargs):
        sync_calls.append(args)

    monkeypatch.setattr("spark_researcher.memory.sync_memory", fake_sync)
    monkeypatch.setattr("spark_researcher.memory._manifest_path", lambda rt: manifest)
    from spark_researcher.memory import search_memory
    try:
        search_memory(tmp_path, tmp_path, "test query")
    except Exception:
        pass
    assert len(sync_calls) == 0


def test_sync_called_when_manifest_missing(tmp_path, monkeypatch):
    sync_calls = []

    def fake_sync(*args, **kwargs):
        sync_calls.append(args)

    monkeypatch.setattr("spark_researcher.memory.sync_memory", fake_sync)
    monkeypatch.setattr("spark_researcher.memory._manifest_path", lambda rt: tmp_path / "no_manifest.json")
    from spark_researcher.memory import search_memory
    try:
        search_memory(tmp_path, tmp_path, "test query")
    except Exception:
        pass
    assert len(sync_calls) == 1


def test_force_sync_overrides_manifest_presence(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{\"entries\": []}", encoding="utf-8")
    sync_calls = []

    def fake_sync(*args, **kwargs):
        sync_calls.append(args)

    monkeypatch.setattr("spark_researcher.memory.sync_memory", fake_sync)
    monkeypatch.setattr("spark_researcher.memory._manifest_path", lambda rt: manifest)
    from spark_researcher.memory import search_memory
    try:
        search_memory(tmp_path, tmp_path, "test query", force_sync=True)
    except Exception:
        pass
    assert len(sync_calls) == 1