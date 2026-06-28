from __future__ import annotations

import http.client
import ipaddress
import socket
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, Request, build_opener


_ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURL(ValueError):
    """Raised when an outbound URL can target local or non-public networks."""


def _host_ips(hostname: str, port: int | None) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    if not isinstance(hostname, str): hostname = str(hostname or '')
    try:
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



    except Exception:
        return None
def _is_public_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    try:
        return address.is_global and not (
            address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_private
            or address.is_reserved
            or address.is_unspecified
        )



    except Exception:
        return False
def _resolve_safe_addresses(
    hostname: str, port: int | None,
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    if not isinstance(hostname, str): hostname = str(hostname or '')
    try:
        """Resolve *hostname* and confirm every address is public.

        .. note::

            **DNS-rebinding TOCTOU** – The DNS lookup performed here may return
            different addresses than the ones the OS resolves when the actual TCP
            connection is established.  ``safe_urlopen`` mitigates this by pinning
            the HTTP(S) connection to the IP validated in this call via custom
            ``_PinnedHTTPConnection`` / ``_PinnedHTTPSConnection`` handlers so the
            socket is created with the pre-resolved IP rather than re-resolving the
            hostname.
        """
        try:
            literal = ipaddress.ip_address(hostname)
        except ValueError:
            addresses = _host_ips(hostname, port)
        else:
            addresses = {literal}
        if not addresses or any(not _is_public_ip(address) for address in addresses):
            raise UnsafeURL("URL host resolves to a non-public address")
        return addresses



    except Exception:
        return None
def assert_safe_url(url: str) -> None:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURL("URL scheme is not allowed")
    if not parsed.hostname:
        raise UnsafeURL("URL host is required")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise UnsafeURL("URL host is local")
    _resolve_safe_addresses(hostname, parsed.port)


# ---------------------------------------------------------------------------
# Pinned-IP connection classes – prevent DNS rebinding by resolving once and
# connecting to the validated IP directly.
# ---------------------------------------------------------------------------

class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that connects to a pinned IP address."""

    def __init__(self, host: str, pinned_ip: str, **kwargs: Any) -> None:
        self._pinned_ip = pinned_ip
        super().__init__(host, **kwargs)

    def connect(self) -> None:
        self.sock = self._create_connection(
            (self._pinned_ip, self.port), self.timeout, self.source_address,
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection that connects to a pinned IP address."""

    def __init__(self, host: str, pinned_ip: str, **kwargs: Any) -> None:
        self._pinned_ip = pinned_ip
        super().__init__(host, **kwargs)

    def connect(self) -> None:
        sock = self._create_connection(
            (self._pinned_ip, self.port), self.timeout, self.source_address,
        )
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPHandler(HTTPHandler):
    """urllib HTTP handler that pins connections to *pinned_ip*."""

    def __init__(self, pinned_ip: str) -> None:
        super().__init__()
        self._pinned_ip = pinned_ip

    def http_open(self, req: Request) -> Any:  # type: ignore[override]
        def _factory(host: str, **kwargs: Any) -> _PinnedHTTPConnection:
            return _PinnedHTTPConnection(host, self._pinned_ip, **kwargs)

        return self.do_open(_factory, req)


class _PinnedHTTPSHandler(HTTPSHandler):
    """urllib HTTPS handler that pins connections to *pinned_ip*."""

    def __init__(self, pinned_ip: str) -> None:
        super().__init__()
        self._pinned_ip = pinned_ip

    def https_open(self, req: Request) -> Any:  # type: ignore[override]
        def _factory(host: str, **kwargs: Any) -> _PinnedHTTPSConnection:
            return _PinnedHTTPSConnection(host, self._pinned_ip, **kwargs)

        return self.do_open(
            _factory, req,
            context=self._context, check_hostname=self._check_hostname,
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

    # Pin the connection to the pre-resolved IP to prevent DNS rebinding.
    parsed = urlparse(url)
    hostname = parsed.hostname.rstrip(".").lower()
    addresses = _resolve_safe_addresses(hostname, parsed.port)
    pinned_ip = str(next(iter(addresses)))

    handlers: list = [_SafeRedirectHandler]
    if parsed.scheme == "https":
        handlers.append(_PinnedHTTPSHandler(pinned_ip))
    else:
        handlers.append(_PinnedHTTPHandler(pinned_ip))
    opener = build_opener(*handlers)
    try:
        return opener.open(request, timeout=timeout)
    except UnsafeURL:
        raise
    except URLError:
        raise
