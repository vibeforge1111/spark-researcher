from __future__ import annotations

import socket
from urllib.request import Request

import pytest

from spark_researcher.safe_url import UnsafeURL, assert_safe_url, safe_urlopen


def test_assert_safe_url_rejects_non_http_schemes() -> None:
    with pytest.raises(UnsafeURL):
        assert_safe_url("file:///etc/passwd")
    with pytest.raises(UnsafeURL):
        assert_safe_url("gopher://example.com")


def test_assert_safe_url_rejects_private_ip_literals() -> None:
    for url in [
        "http://127.0.0.1/status",
        "http://10.0.0.1/status",
        "http://172.16.1.2/status",
        "http://192.168.1.1/status",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/status",
    ]:
        with pytest.raises(UnsafeURL):
            assert_safe_url(url)


def test_assert_safe_url_rejects_dns_that_resolves_private(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.8", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(UnsafeURL):
        assert_safe_url("https://example.com/search")


def test_assert_safe_url_rejects_scoped_ipv6_as_non_public(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("fe80::1%eth0", 443, 0, 2))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(UnsafeURL, match="non-public address"):
        assert_safe_url("https://example.com/search")


def test_assert_safe_url_accepts_public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    assert_safe_url("https://example.com/search")


def test_safe_urlopen_validates_before_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_open(*args, **kwargs):
        raise AssertionError("unsafe URL should fail before opener.open")

    monkeypatch.setattr("spark_researcher.safe_url.build_opener", lambda *args, **kwargs: type("Opener", (), {"open": fail_open})())

    with pytest.raises(UnsafeURL):
        safe_urlopen(Request("http://127.0.0.1/status"), timeout=1)
