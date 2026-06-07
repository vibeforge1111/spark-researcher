from __future__ import annotations

import http.client
import ipaddress
import socket
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, HTTPHandler, HTTPSHandler, Request, build_opener


_ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURL(ValueError):
    """Raised when an outbound URL can target local or non-public networks."""


def _host_ips(hostname: str, port: int | None) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
        for info in socket.getaddrinfo(hostname, port or 443, type=socket.SOCK_STREAM):
            raw_address = info[4][0]
            if ":" in raw_address and "%" in raw_address:
                raw_address = raw_address.split("%", 1)[0]
            addresses.add(ipaddress.ip_address(raw_address))
        return addresses
    except (OSError, ValueError) as exc:
        raise UnsafeURL("URL host could not be resolved safely") from exc


def _is_public_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return address.is_global and not (
        address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_private
        or address.is_reserved
        or address.is_unspecified
    )


def assert_safe_url(url: str) -> None:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURL("URL scheme is not allowed")
    if not parsed.hostname:
        raise UnsafeURL("URL host is required")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise UnsafeURL("URL host is local")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        addresses = _host_ips(hostname, parsed.port)
    else:
        addresses = {literal}
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise UnsafeURL("URL host resolves to a non-public address")


def _validate_connection_ip(hostname: str, port: int | None) -> None:
    """Re-validate resolved IP at connection time to prevent DNS rebinding.

    This addresses the TOCTOU race where ``assert_safe_url`` resolves DNS,
    then the actual ``open()`` call connects. Between resolution and
    connection an attacker could rebind DNS to a private address.
    """
    hostname_clean = hostname.rstrip(".").lower()
    try:
        literal = ipaddress.ip_address(hostname_clean)
    except ValueError:
        addresses = _host_ips(hostname_clean, port)
    else:
        addresses = {literal}
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise UnsafeURL(
            f"URL host {hostname_clean} resolved to non-public address at connection time"
        )


class _SafeHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that validates IP at connect time (prevents DNS rebinding)."""

    def connect(self) -> None:
        _validate_connection_ip(self.host, self.port)
        super().connect()


class _SafeHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection that validates IP at connect time (prevents DNS rebinding)."""

    def connect(self) -> None:
        _validate_connection_ip(self.host, self.port)
        super().connect()


class _SafeHTTPHandler(HTTPHandler):
    """HTTP handler that uses IP-validating connections."""

    def http_open(self, req: Request) -> Any:
        return self.do_open(_SafeHTTPConnection, req)


class _SafeHTTPSHandler(HTTPSHandler):
    """HTTPS handler that uses IP-validating connections."""

    def https_open(self, req: Request) -> Any:
        return self.do_open(_SafeHTTPSConnection, req)


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        assert_safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_urlopen(request: Request | str, *, timeout: float):
    url = request.full_url if isinstance(request, Request) else str(request)
    assert_safe_url(url)
    opener = build_opener(
        _SafeRedirectHandler,
        _SafeHTTPHandler,
        _SafeHTTPSHandler,
    )
    try:
        return opener.open(request, timeout=timeout)
    except UnsafeURL:
        raise
    except URLError:
        raise
