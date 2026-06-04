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


def _assert_final_response_url_safe(response_url: str) -> None:
    """Re-validate the final resolved URL after all redirects are followed.

    Catches DNS rebinding attacks and any escape from the per-redirect check
    where the URL checked by assert_safe_url resolved to a public IP at check
    time but the actual TCP connection reached a private address.
    """
    try:
        parsed = urlparse(str(response_url or "").strip())
        hostname = (parsed.hostname or "").rstrip(".").lower()
        if not hostname:
            return
        # For IP literals, check directly without DNS resolution.
        try:
            literal = ipaddress.ip_address(hostname)
            if not _is_public_ip(literal):
                raise UnsafeURL(
                    f"Final response URL {response_url!r} resolved to a non-public address"
                )
            return
        except ValueError:
            pass
        # For hostnames, re-resolve and validate every returned address.
        addresses = _host_ips(hostname, parsed.port)
        if not addresses or any(not _is_public_ip(addr) for addr in addresses):
            raise UnsafeURL(
                f"Final response URL {response_url!r} resolved to a non-public address"
            )
    except UnsafeURL:
        raise
    except Exception as exc:
        raise UnsafeURL("Final response URL could not be validated safely") from exc


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

    # Re-validate the final URL after all redirects are fully resolved.
    # This catches DNS rebinding and any redirect path that escapes per-hop checks.
    final_url = response.geturl()
    if final_url and final_url != url:
        _assert_final_response_url_safe(final_url)

    return response
