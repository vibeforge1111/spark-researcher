from __future__ import annotations

import socket
from urllib.request import Request

import pytest

from spark_researcher.safe_url import ResponseTooLarge, UnsafeURL, assert_safe_url, read_bounded_response, safe_urlopen


def test_assert_safe_url_rejects_non_http_schemes() -> None:
    with pytest.raises(UnsafeURL):
        assert_safe_url("file:///etc/passwd")
    with pytest.raises(UnsafeURL):
        assert_safe_url("gopher://example.com")


def test_unsafe_url_errors_give_safe_recovery_guidance_without_echoing_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_resolution(*args, **kwargs):
        raise OSError("resolver leaked internal detail")

    monkeypatch.setattr(socket, "getaddrinfo", fail_resolution)

    cases = [
        ("ftp://secret-scheme.internal/private-token", "use http or https"),
        ("https:///private-token", "use an absolute http or https URL"),
        ("http://secret-host.localhost/private-token", "use a publicly reachable host"),
        ("https://secret-host.internal/private-token", "use a publicly reachable host"),
    ]
    for url, guidance in cases:
        with pytest.raises(UnsafeURL) as raised:
            assert_safe_url(url)

        message = str(raised.value)
        assert guidance in message
        assert "secret" not in message
        assert "private-token" not in message
        assert "resolver leaked internal detail" not in message


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


def test_read_bounded_response_uses_a_sentinel_byte() -> None:
    class Response:
        requested_size = 0

        def read(self, size: int) -> bytes:
            self.requested_size = size
            return b"x" * size

    response = Response()

    with pytest.raises(ResponseTooLarge, match="safe size limit"):
        read_bounded_response(response, max_bytes=8)

    assert response.requested_size == 9
