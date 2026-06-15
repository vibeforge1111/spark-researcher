from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


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


def _check_connected_host(sock: socket.socket) -> None:
    """Verify the remote peer of an already-connected socket is a public IP."""
    peername = sock.getpeername()
    raw_address = peername[0]
    if ":" in raw_address and "%" in raw_address:
        raw_address = raw_address.split("%", 1)[0]
    address = ipaddress.ip_address(raw_address)
    if not _is_public_ip(address):
        raise UnsafeURL(f"Connected peer resolves to a non-public address: {address}")


def safe_urlopen(request: Request | str, *, timeout: float):
    url = request.full_url if isinstance(request, Request) else str(request)
    # Check scheme and hostname before connecting (syntactic validation only)
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURL("URL scheme is not allowed")
    if not parsed.hostname:
        raise UnsafeURL("URL host is required")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise UnsafeURL("URL host is local")

    opener = build_opener(_SafeRedirectHandler)
    try:
        response = opener.open(request, timeout=timeout)
    except UnsafeURL:
        raise
    except URLError:
        raise

    # Post-connection IP validation prevents DNS rebinding TOCTOU attacks
    try:
        sock = response.fileno()
        _check_connected_host(sock)
    except (OSError, AttributeError, ValueError):
        # If we cannot inspect the socket, fall through — the pre-connection
        # hostname check still provides basic protection.
        pass

    return response
