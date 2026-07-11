from __future__ import annotations

import io
import socket
from unittest.mock import MagicMock, patch
from urllib.request import Request

import pytest

from spark_researcher.safe_url import UnsafeURL, _assert_final_response_url_safe, safe_urlopen


class TestAssertFinalResponseUrlSafe:
    def test_private_class_c_ip_blocked(self) -> None:
        with pytest.raises(UnsafeURL):
            _assert_final_response_url_safe("http://192.168.1.1/")

    def test_metadata_endpoint_blocked(self) -> None:
        with pytest.raises(UnsafeURL):
            _assert_final_response_url_safe("http://169.254.169.254/latest/meta-data/")

    def test_loopback_ip_blocked(self) -> None:
        with pytest.raises(UnsafeURL):
            _assert_final_response_url_safe("http://127.0.0.1/admin")

    def test_ipv6_loopback_blocked(self) -> None:
        with pytest.raises(UnsafeURL):
            _assert_final_response_url_safe("http://[::1]/admin")

    def test_private_class_a_blocked(self) -> None:
        with pytest.raises(UnsafeURL):
            _assert_final_response_url_safe("http://10.0.0.1/")

    def test_private_class_b_blocked(self) -> None:
        with pytest.raises(UnsafeURL):
            _assert_final_response_url_safe("http://172.16.0.1/")

    def test_public_ip_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_getaddrinfo(*args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 443))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        _assert_final_response_url_safe("https://one.one.one.one/")  # must not raise

    def test_hostname_resolving_to_private_ip_blocked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_getaddrinfo(*args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.100.1", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(UnsafeURL):
            _assert_final_response_url_safe("http://seemingly-public.example.com/secret")


class TestSafeUrlopenRedirectValidation:
    def _make_response(self, final_url: str) -> MagicMock:
        resp = MagicMock()
        resp.geturl.return_value = final_url
        resp.read.return_value = b"data"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_redirect_to_private_ip_is_blocked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Public initial URL that eventually resolves to a private IP must be blocked."""
        def fake_getaddrinfo(host, *args, **kwargs):
            if host == "public.example.com":
                return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80))]
            raise socket.gaierror("no address")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        fake_resp = self._make_response("http://192.168.1.10/internal")

        with patch("spark_researcher.safe_url.build_opener") as mock_opener_factory:
            mock_opener = MagicMock()
            mock_opener.open.return_value = fake_resp
            mock_opener_factory.return_value = mock_opener

            with pytest.raises(UnsafeURL):
                safe_urlopen("http://public.example.com/path", timeout=5)

    def test_redirect_to_metadata_endpoint_is_blocked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_getaddrinfo(host, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        fake_resp = self._make_response("http://169.254.169.254/latest/meta-data/iam/security-credentials/")

        with patch("spark_researcher.safe_url.build_opener") as mock_opener_factory:
            mock_opener = MagicMock()
            mock_opener.open.return_value = fake_resp
            mock_opener_factory.return_value = mock_opener

            with pytest.raises(UnsafeURL):
                safe_urlopen("http://public.example.com/", timeout=5)

    def test_redirect_to_localhost_is_blocked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_getaddrinfo(host, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        fake_resp = self._make_response("http://127.0.0.1:8080/admin")

        with patch("spark_researcher.safe_url.build_opener") as mock_opener_factory:
            mock_opener = MagicMock()
            mock_opener.open.return_value = fake_resp
            mock_opener_factory.return_value = mock_opener

            with pytest.raises(UnsafeURL):
                safe_urlopen("http://public.example.com/", timeout=5)

    def test_legitimate_redirect_to_public_url_allowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_getaddrinfo(host, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        fake_resp = self._make_response("https://www.example.com/final-page")

        with patch("spark_researcher.safe_url.build_opener") as mock_opener_factory:
            mock_opener = MagicMock()
            mock_opener.open.return_value = fake_resp
            mock_opener_factory.return_value = mock_opener

            result = safe_urlopen("https://example.com/", timeout=5)
            assert result is fake_resp

    def test_final_url_check_not_just_initial(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify the fix is in the final URL check, not just the initial check."""
        def fake_getaddrinfo(host, *args, **kwargs):
            # Initial URL passes; final URL resolves to private (simulated by final_url being a literal private IP)
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        fake_resp = self._make_response("http://10.0.0.250/secret-api")

        with patch("spark_researcher.safe_url.build_opener") as mock_opener_factory:
            mock_opener = MagicMock()
            mock_opener.open.return_value = fake_resp
            mock_opener_factory.return_value = mock_opener

            # Without the final-URL check this would succeed; with it, it must raise
            with pytest.raises(UnsafeURL):
                safe_urlopen("https://public.example.com/", timeout=5)
