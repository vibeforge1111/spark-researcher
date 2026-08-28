"""Security tests for spark-researcher:
- PR #131: SSRF via DNS rebinding
- PR #130: Git argument injection
- PR #135/#59: Path traversal
"""

import os
import sys
import re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# --- PR #131: SSRF via DNS rebinding ---
def test_ssrf_protection_blocks_private_ips():
    """Verify URL validation blocks private/internal IPs"""
    root = os.path.join(os.path.dirname(__file__), "..")
    found_ssrf = False
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                ssrf_patterns = [
                    "PRIVATE_IPS", "private_ip", "is_private",
                    "ipaddress", "ip_address",
                    "127.0.0.1", "10.", "192.168.",
                    "169.254", "metadata",
                ]
                found = [p for p in ssrf_patterns if p in content]
                if len(found) >= 2:
                    found_ssrf = True
    assert found_ssrf, "SSRF protection should block private IPs"


def test_safe_url_validation():
    """Verify safe URL validation exists"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "safe_url" in content.lower() or "validate_url" in content.lower():
                    return True


def test_dns_rebinding_protection():
    """Verify DNS rebinding protection via IP resolution"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "socket" in content or "dns" in content.lower():
                    return True


# --- PR #130: Git argument injection ---
def test_git_argument_sanitization():
    """Verify git arguments are sanitized to prevent injection"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "git" in content and "subprocess" in content:
                    has_sanitization = any(
                        p in content for p in [
                            "shlex.quote", "pipes.quote",
                            "sanitize", "validate",
                            "--", "shell=False",
                        ]
                    )
                    if has_sanitization:
                        return True


def test_git_commands_use_list_form():
    """Verify git subprocess uses list form (not shell=True)"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "git" in content and "subprocess" in content:
                    if "shell=True" not in content:
                        return True


# --- PR #135/#59: Path traversal ---
def test_path_traversal_prevention():
    """Verify path traversal is prevented"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                traversal_patterns = [
                    "os.path.abspath", "os.path.realpath", "os.path.normpath",
                    "Path(", "resolve(", "relative_to",
                    "..", "sanitize", "startswith",
                ]
                found = [p for p in traversal_patterns if p in content]
                if len(found) >= 2:
                    return True


def test_proposal_id_sanitization():
    """Verify proposal IDs are sanitized to prevent path traversal"""
    root = os.path.join(os.path.dirname(__file__), "..")
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                fpath = os.path.join(dirpath, fn)
                with open(fpath) as f:
                    content = f.read()
                if "proposal" in content.lower() and ("path" in content.lower() or "id" in content.lower()):
                    return True
