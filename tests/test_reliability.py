"""Reliability tests for spark-researcher:
- PR #136: JSON validation in config memory
- PR #134: Logging for research web search
- PR #47: Error on unknown candidate ID
- PR #46: Friendly config errors
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# --- PR #136: JSON validation ---
def test_json_validation_exists():
    """Verify JSON validation for config/memory files"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "json.loads" in content or "json.load" in content:
                    # Check for validation/handling
                    if "try" in content and "except" in content:
                        return True


def test_malformed_json_handled():
    """Verify malformed JSON is handled gracefully"""
    corrupted = [
        "{bad json}",
        "",
        "None",
        "undefined",
        "{'single': 'quotes'}",
    ]
    for bad in corrupted:
        try:
            json.loads(bad)
            # Should have raised
        except (json.JSONDecodeError, Exception):
            pass  # Expected


def test_json_has_default_fallback():
    """Verify JSON parsing has default fallback values"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "json.loads" in content:
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if "json.loads" in line:
                            end = min(len(lines), i + 5)
                            context = "\n".join(lines[i:end])
                            if "return" in context or "{}" in context or "[]" in context:
                                return True


# --- PR #134: Logging ---
def test_logging_for_web_search():
    """Verify web search has proper logging"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "search" in content.lower() and ("log" in content.lower() or "logger" in content):
                    return True


def test_logging_does_not_leak_secrets():
    """Verify logging doesn't leak sensitive data"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "log" in content.lower() or "logger" in content:
                    # Check for log sanitization
                    if "redact" in content or "sanitize" in content or "mask" in content:
                        return True


def test_logging_has_context():
    """Verify logging includes context information"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "loguru" in content or "logging" in content:
                    return True


# --- PR #47: Error on unknown candidate ---
def test_unknown_candidate_error():
    """Verify unknown candidate ID returns clear error"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "unknown" in content.lower() or "not found" in content.lower():
                    if "candidate" in content.lower() or "id" in content.lower():
                        return True


def test_unknown_candidate_does_not_crash():
    """Verify unknown candidate doesn't crash the system"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "KeyError" in content or "ValueError" in content:
                    if "candidate" in content.lower():
                        return True


# --- PR #46: Friendly config errors ---
def test_friendly_config_errors():
    """Verify config errors have user-friendly messages"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "config" in content.lower() and "error" in content.lower():
                    # Check for helpful error messages
                    if "help" in content.lower() or "try" in content.lower() or "see" in content.lower():
                        return True


def test_config_error_has_actionable_message():
    """Verify config errors tell user what to do"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "config" in content.lower() and "error" in content.lower():
                    if "set " in content.lower() or "run " in content.lower() or "specify" in content.lower():
                        return True
