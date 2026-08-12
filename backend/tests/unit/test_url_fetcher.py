"""Tests for the SSRF-guarded URL fetcher and HTML text extraction (Phase 13).

The guard rules (``is_blocked_address`` / ``is_safe_url``) are tested against
literal IPs and a monkeypatched resolver so no DNS is touched. The full
``fetch`` path is exercised against a real in-process HTTP server on
loopback, with the guard bypassed — the bypass keeps the test hermetic while
the redirect/stream/size-cap logic is genuinely exercised.
"""

from __future__ import annotations

import http.server
import threading

import pytest
from app.application.ports.media import FetchedPage, UrlFetchError
from app.infrastructure.media import url_fetcher

# ----------------------------------------------------------------------
# SSRF guard rules
# ----------------------------------------------------------------------


def test_is_blocked_address_refuses_private_and_reserved_ranges() -> None:
    """Every private/reserved range — IPv4 and IPv6 — must be blocked."""
    for address in (
        "127.0.0.1",
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.1.1",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:127.0.0.1",
    ):
        assert url_fetcher.is_blocked_address(address), address


def test_is_blocked_address_allows_public_addresses() -> None:
    """Public addresses — IPv4 and IPv6 — must pass."""
    assert url_fetcher.is_blocked_address("8.8.8.8") is False
    assert url_fetcher.is_blocked_address("2606:4700:4700::1111") is False


def test_is_blocked_address_fails_closed_on_garbage() -> None:
    """Unparseable input must be blocked (fail closed), not allowed."""
    assert url_fetcher.is_blocked_address("not-an-ip")


def test_is_safe_url_rejects_bad_shapes() -> None:
    """Non-http(s) schemes, credentials, and missing hosts are refused."""
    assert not url_fetcher.is_safe_url("ftp://8.8.8.8/")
    assert not url_fetcher.is_safe_url("http://user:pass@8.8.8.8/")
    assert not url_fetcher.is_safe_url("not a url")
    assert not url_fetcher.is_safe_url("http:///missing-host")


def test_is_safe_url_accepts_public_ip_and_rejects_private() -> None:
    """Literal IPs short-circuit the resolver."""
    assert url_fetcher.is_safe_url("https://8.8.8.8/")
    assert not url_fetcher.is_safe_url("http://127.0.0.1/")


def test_is_safe_url_requires_public_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hostname must resolve to at least one public address, never private."""
    monkeypatch.setattr(
        url_fetcher.socket,
        "getaddrinfo",
        lambda host, port, type: [(2, 1, 6, "", ("8.8.8.8", 0))],
    )
    assert url_fetcher.is_safe_url("http://example.test/")

    monkeypatch.setattr(
        url_fetcher.socket,
        "getaddrinfo",
        lambda host, port, type: [(2, 1, 6, "", ("127.0.0.1", 0))],
    )
    assert not url_fetcher.is_safe_url("http://example.test/")

    monkeypatch.setattr(url_fetcher.socket, "getaddrinfo", lambda *args, **kwargs: [])
    assert not url_fetcher.is_safe_url("http://example.test/")


# ----------------------------------------------------------------------
# HTML text extraction
# ----------------------------------------------------------------------


def test_extract_html_text_strips_markup_and_skips_hidden_content() -> None:
    """Script/style blocks are dropped; visible text is whitespace-collapsed."""
    html = (
        "<html><head><title>T</title></head><body>"
        "<script>var x = 1;</script><style>.a {}</style>"
        "<p>Hello   world</p><p>Second.</p></body></html>"
    )
    assert url_fetcher.extract_html_text(html) == "T Hello world Second."


def test_extract_html_text_handles_malformed_html() -> None:
    """Malformed markup degrades to the raw body instead of raising."""
    text = url_fetcher.extract_html_text("<p>unclosed")
    assert "unclosed" in text


def test_extract_html_text_caps_output() -> None:
    """The extracted text is capped so the analyzer never sees a wall."""
    text = url_fetcher.extract_html_text("<p>" + "a" * 60_000 + "</p>")
    assert len(text) <= url_fetcher._MAX_TEXT_CHARS


# ----------------------------------------------------------------------
# Full fetch path against a local HTTP server
# ----------------------------------------------------------------------


class _PageHandler(http.server.BaseHTTPRequestHandler):
    """Serves the tiny fixtures the fetch tests need."""

    def do_GET(self) -> None:  # noqa: N802 (stdlib casing)
        if self.path == "/page":
            body = b"<html><body><p>Hello from the page.</p></body></html>"
            self._respond(200, body, "text/html")
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/page")
            self.end_headers()
        elif self.path == "/big":
            self._respond(200, b"x" * 4_000, "text/plain")
        elif self.path == "/raw":
            self._respond(200, b"plain raw text", "text/plain")
        else:
            self.send_response(404)
            self.end_headers()

    def _respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture()
def local_server() -> http.server.ThreadingHTTPServer:
    """An in-process HTTP server on loopback (random port)."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _PageHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture()
def allow_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the SSRF guard so tests can hit the local server."""
    monkeypatch.setattr(url_fetcher, "is_safe_url", lambda url: True)


def test_fetch_extracts_html_text(
    local_server: http.server.ThreadingHTTPServer, allow_loopback: None
) -> None:
    """A plain HTML page is fetched and its visible text extracted."""
    fetcher = url_fetcher.HttpUrlFetcher()
    page = fetcher.fetch(f"http://127.0.0.1:{local_server.server_port}/page")
    assert isinstance(page, FetchedPage)
    assert page.status == 200
    assert page.text == "Hello from the page."
    assert page.final_url == f"http://127.0.0.1:{local_server.server_port}/page"


def test_fetch_passes_raw_text_through(
    local_server: http.server.ThreadingHTTPServer, allow_loopback: None
) -> None:
    """text/plain bodies are not HTML-stripped."""
    page = url_fetcher.HttpUrlFetcher().fetch(
        f"http://127.0.0.1:{local_server.server_port}/raw"
    )
    assert page.text == "plain raw text"


def test_fetch_follows_redirects(
    local_server: http.server.ThreadingHTTPServer, allow_loopback: None
) -> None:
    """Redirects are followed, and the final URL/status are reported."""
    page = url_fetcher.HttpUrlFetcher().fetch(
        f"http://127.0.0.1:{local_server.server_port}/redirect"
    )
    assert page.status == 200
    assert page.final_url.endswith("/page")
    assert page.text == "Hello from the page."


def test_fetch_enforces_size_cap(
    local_server: http.server.ThreadingHTTPServer, allow_loopback: None
) -> None:
    """Oversized responses fail with UrlFetchError instead of being read."""
    with pytest.raises(UrlFetchError, match="size cap"):
        url_fetcher.HttpUrlFetcher().fetch(
            f"http://127.0.0.1:{local_server.server_port}/big", max_bytes=100
        )


def test_fetch_surfaces_http_errors(
    local_server: http.server.ThreadingHTTPServer, allow_loopback: None
) -> None:
    """4xx/5xx responses surface as UrlFetchError with the status code."""
    with pytest.raises(UrlFetchError, match="404"):
        url_fetcher.HttpUrlFetcher().fetch(
            f"http://127.0.0.1:{local_server.server_port}/missing"
        )


def test_fetch_refuses_private_target(
    local_server: http.server.ThreadingHTTPServer,
) -> None:
    """With the guard active, a loopback target is refused before any fetch."""
    with pytest.raises(UrlFetchError, match="SSRF"):
        url_fetcher.HttpUrlFetcher().fetch(
            f"http://127.0.0.1:{local_server.server_port}/page"
        )


def test_build_url_fetcher_returns_configured_instance() -> None:
    """The composition-root builder returns a working fetcher."""
    assert isinstance(url_fetcher.build_url_fetcher(), url_fetcher.HttpUrlFetcher)
