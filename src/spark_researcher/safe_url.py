from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


logger = logging.getLogger(__name__)

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
        raise UnsafeURL(
            f"URL host {hostname!r} could not be resolved safely "
            f"(DNS lookup failed: {exc}). Check that the hostname is reachable from this "
            f"machine and that DNS is configured."
        ) from exc


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
        raise UnsafeURL(
            f"URL scheme {parsed.scheme!r} is not allowed. "
            f"Use http or https — spark-researcher refuses other schemes to prevent SSRF "
            f"into file://, ftp://, gopher:// and similar."
        )
    if not parsed.hostname:
        raise UnsafeURL(
            f"URL host is required (parsed url={url!r}). "
            f"Provide an absolute URL of the form https://example.com/path."
        )
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise UnsafeURL(
            f"URL host {hostname!r} is local. "
            f"spark-researcher refuses loopback hosts to prevent reaching local-only "
            f"services. Use a publicly-reachable URL."
        )
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        addresses = _host_ips(hostname, parsed.port)
    else:
        addresses = {literal}
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        resolved = ", ".join(str(a) for a in sorted(addresses, key=str)) or "<no addresses>"
        # Log the resolved address set server-side for diagnosis, but do NOT echo it in
        # the exception: surfacing the internal IP a public-looking host resolves to would
        # let an untrusted caller map internal network topology (SSRF reconnaissance).
        logger.debug(
            "safe_url: host %r resolved to non-public address(es): %s", hostname, resolved
        )
        raise UnsafeURL(
            f"URL host {hostname!r} resolves to a non-public address. "
            f"spark-researcher refuses private, loopback, link-local, multicast, or "
            f"reserved IPs to prevent SSRF. Use a publicly-reachable host."
        )


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
        return opener.open(request, timeout=timeout)
    except UnsafeURL:
        raise
    except URLError:
        raise
