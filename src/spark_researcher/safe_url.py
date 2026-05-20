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
        return {
            ipaddress.ip_address(info[4][0])
            for info in socket.getaddrinfo(hostname, port or 443, type=socket.SOCK_STREAM)
        }
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


def safe_urlopen(request: Request | str, *, timeout: float):
    url = request.full_url if isinstance(request, Request) else str(request)
    assert_safe_url(url)
    opener = build_opener(_SafeRedirectHandler)
    try:
        response = opener.open(request, timeout=timeout)
    except UnsafeURL:
        raise
    except URLError:
        raise
    # Re-validate the resolved IP after connection to mitigate DNS rebinding.
    # The socket may have connected to a different IP than the pre-flight check.
    peer = getattr(response.fp, "raw", None)
    if peer is None:
        peer = response
    sock = getattr(getattr(peer, "_sock", None), "getpeername", None)
    if sock is None:
        sock = getattr(getattr(getattr(peer, "fp", None), "raw", None), "_sock", None)
        if sock is not None:
            sock = sock.getpeername
    if sock is not None:
        try:
            peer_ip = ipaddress.ip_address(sock()[0])
            if not _is_public_ip(peer_ip):
                response.close()
                raise UnsafeURL(
                    f"DNS rebinding detected: connected to non-public IP {peer_ip}"
                )
        except (OSError, TypeError, IndexError):
            pass  # Best-effort; socket may already be closed
    return response
