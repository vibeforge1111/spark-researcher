from __future__ import annotations

import errno
from http.client import HTTPConnection, HTTPSConnection
import ipaddress
import socket
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import (
    HTTPHandler,
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)


_ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURL(ValueError):
    """Raised when an outbound URL can target local or non-public networks."""


class ResponseTooLarge(ValueError):
    """Raised when a guarded response exceeds its bounded read budget."""


def read_bounded_response(response: Any, *, max_bytes: int = 2 * 1024 * 1024) -> bytes:
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ResponseTooLarge("Web response exceeded the safe size limit")
    return payload


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
        raise UnsafeURL(
            "URL host could not be resolved safely; use a publicly reachable host"
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


def _resolve_safe_addresses(
    hostname: str, port: int | None,
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
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
        raise UnsafeURL(
            "URL host resolves to a non-public address; use a publicly reachable host"
        )
    return addresses


def assert_safe_url(url: str) -> None:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURL("URL scheme is not allowed; use http or https")
    if not parsed.hostname:
        raise UnsafeURL("URL host is required; use an absolute http or https URL")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise UnsafeURL("URL host is local; use a publicly reachable host")
    _resolve_safe_addresses(hostname, parsed.port)


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


class _PinnedConnectionMixin:
    _pinned_addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]

    def __init__(
        self,
        host: str,
        *,
        pinned_addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...],
        **kwargs: Any,
    ) -> None:
        if not pinned_addresses:
            raise UnsafeURL("URL host has no validated public address")
        self._pinned_addresses = pinned_addresses
        super().__init__(host, **kwargs)

    def _connect_pinned_socket(self) -> None:
        if self._tunnel_host:
            raise UnsafeURL("Proxy tunnels are not allowed for guarded requests")
        last_error: OSError | None = None
        for address in self._pinned_addresses:
            try:
                self.sock = self._create_connection(
                    (str(address), self.port),
                    self.timeout,
                    self.source_address,
                )
            except OSError as exc:
                last_error = exc
                continue
            break
        else:
            if last_error is not None:
                raise last_error
            raise UnsafeURL("URL host has no reachable validated public address")

        try:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError as exc:
            if exc.errno != errno.ENOPROTOOPT:
                self.sock.close()
                self.sock = None
                raise


class _PinnedHTTPConnection(_PinnedConnectionMixin, HTTPConnection):
    def connect(self) -> None:
        self._connect_pinned_socket()


class _PinnedHTTPSConnection(_PinnedConnectionMixin, HTTPSConnection):
    def connect(self) -> None:
        self._connect_pinned_socket()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def _validated_request_addresses(
    url: str,
) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
    assert_safe_url(url)
    parsed = urlparse(str(url or "").strip())
    hostname = (parsed.hostname or "").rstrip(".").lower()
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        addresses = _host_ips(hostname, parsed.port)
    else:
        addresses = {literal}
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise UnsafeURL(
            "URL host resolves to a non-public address; use a publicly reachable host"
        )
    return tuple(sorted(addresses, key=lambda address: (address.version, int(address))))


class _PinnedHTTPHandler(HTTPHandler):
    def http_open(self, request: Request):
        addresses = _validated_request_addresses(request.full_url)

        def connection(host: str, **kwargs: Any) -> _PinnedHTTPConnection:
            return _PinnedHTTPConnection(host, pinned_addresses=addresses, **kwargs)

        return self.do_open(connection, request)


class _PinnedHTTPSHandler(HTTPSHandler):
    def https_open(self, request: Request):
        addresses = _validated_request_addresses(request.full_url)

        def connection(host: str, **kwargs: Any) -> _PinnedHTTPSConnection:
            return _PinnedHTTPSConnection(host, pinned_addresses=addresses, **kwargs)

        return self.do_open(connection, request, context=self._context)


def safe_urlopen(request: Request | str, *, timeout: float):
    url = request.full_url if isinstance(request, Request) else str(request)
    assert_safe_url(url)
    opener = build_opener(
        ProxyHandler({}),
        _SafeRedirectHandler,
        _PinnedHTTPHandler,
        _PinnedHTTPSHandler,
    )
    try:
        return opener.open(request, timeout=timeout)
    except UnsafeURL:
        raise
    except URLError:
        raise
