from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.request import Request

import pytest

from spark_researcher.safe_url import (
    _PinnedHTTPConnection,
    _PinnedHTTPSConnection,
    _SafeRedirectHandler,
    _validated_request_addresses,
    UnsafeURL,
)


class _Socket:
    def setsockopt(self, *_args: Any) -> None:
        return None


class _TLSContext:
    def __init__(self) -> None:
        self.server_hostname: str | None = None

    def wrap_socket(self, sock: _Socket, *, server_hostname: str) -> _Socket:
        self.server_hostname = server_hostname
        return sock


def test_http_connection_uses_only_prevalidated_addresses() -> None:
    attempts: list[tuple[str, int]] = []
    connection = _PinnedHTTPConnection(
        "research.example",
        pinned_addresses=(
            ipaddress.ip_address("93.184.216.34"),
            ipaddress.ip_address("1.1.1.1"),
        ),
        timeout=2,
    )

    def connect(address: tuple[str, int], *_args: Any) -> _Socket:
        attempts.append(address)
        if len(attempts) == 1:
            raise OSError("first public route unavailable")
        return _Socket()

    connection._create_connection = connect
    connection.connect()

    assert attempts == [("93.184.216.34", 80), ("1.1.1.1", 80)]
    assert all(host != "research.example" for host, _port in attempts)


def test_https_connection_keeps_origin_hostname_for_tls() -> None:
    context = _TLSContext()
    attempts: list[tuple[str, int]] = []
    connection = _PinnedHTTPSConnection(
        "research.example",
        pinned_addresses=(ipaddress.ip_address("93.184.216.34"),),
        timeout=2,
    )
    connection._context = context

    def connect(address: tuple[str, int], *_args: Any) -> _Socket:
        attempts.append(address)
        return _Socket()

    connection._create_connection = connect
    connection.connect()

    assert attempts == [("93.184.216.34", 443)]
    assert context.server_hostname == "research.example"


def test_pinned_connection_fails_closed_when_every_public_route_fails() -> None:
    connection = _PinnedHTTPConnection(
        "research.example",
        pinned_addresses=(ipaddress.ip_address("93.184.216.34"),),
        timeout=2,
    )

    def fail(_address: tuple[str, int], *_args: Any) -> _Socket:
        raise OSError("unreachable")

    connection._create_connection = fail
    with pytest.raises(OSError, match="unreachable"):
        connection.connect()


def test_authoritative_resolution_rejects_a_rebound_private_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(("93.184.216.34", "127.0.0.1"))

    def resolve(*_args: Any, **_kwargs: Any):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (next(answers), 80))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    with pytest.raises(UnsafeURL, match="non-public address"):
        _validated_request_addresses("http://research.example/report")


def test_redirect_handler_rejects_private_literal_even_when_dns_is_public(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80))
        ],
    )
    request = Request("http://research.example/report")
    with pytest.raises(UnsafeURL, match="non-public address"):
        _SafeRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "http://169.254.169.254/latest/meta-data",
        )
