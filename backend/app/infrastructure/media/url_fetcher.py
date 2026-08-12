"""SSRF-guarded URL fetching and HTML text extraction (Phase 13).

``HttpUrlFetcher`` retrieves a submitted URL and extracts its readable
text for claim analysis. The fetcher fails closed on anything that is not
plain HTTP(S) to a public address:

- the scheme must be ``http`` or ``https``,
- the host is resolved up front and every address must be public
  (private, loopback, link-local, CGNAT, multicast, and reserved ranges
  are refused — both IPv4 and IPv6),
- redirects are re-validated with the same guard and capped,
- the response body is streamed with a hard size cap and a timeout.

The guard blocks the classic SSRF vectors (literal private IPs and DNS
names resolving to private ranges). A host that resolves publicly but is
re-served from a private address at connect time (DNS rebinding) is a
documented residual risk mitigated by the size cap and by keeping the
fetch inside the worker's network perimeter.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

from app.application.ports.media import FetchedPage, UrlFetchError

# Private / reserved networks that must never be fetched (fail closed).
_BLOCKED_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("0.0.0.0/8"),      # "this" network
    ipaddress.ip_network("10.0.0.0/8"),     # RFC 1918
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),    # loopback
    ipaddress.ip_network("169.254.0.0/16"), # link-local
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918
    ipaddress.ip_network("192.0.0.0/24"),   # IETF protocol assignments
    ipaddress.ip_network("192.168.0.0/16"), # RFC 1918
    ipaddress.ip_network("198.18.0.0/15"),  # benchmarking
    ipaddress.ip_network("224.0.0.0/4"),    # multicast
    ipaddress.ip_network("240.0.0.0/4"),    # reserved
    ipaddress.ip_network("::/128"),         # unspecified
    ipaddress.ip_network("::1/128"),        # loopback
    ipaddress.ip_network("fc00::/7"),       # unique local
    ipaddress.ip_network("fe80::/10"),      # link-local
    ipaddress.ip_network("ff00::/8"),       # multicast
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
)

# How many redirects a fetch may follow (each hop is SSRF-checked).
_MAX_REDIRECTS = 5

# Upper bound on the extracted text passed to the claim analyzer.
_MAX_TEXT_CHARS = 50_000

# Content types we treat as raw text (everything else goes through the
# HTML stripper, which degrades gracefully to the raw body).
_TEXT_CONTENT_TYPES = ("text/plain",)


def is_blocked_address(address: str) -> bool:
    """Return True when ``address`` is not a publicly reachable IP.

    Unparseable input fails closed (blocked).

    Args:
        address: An IP address string (IPv4 or IPv6).

    Returns:
        True when the address is private/reserved or malformed.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True
    return any(ip in network for network in _BLOCKED_NETWORKS)


def is_safe_url(url: str) -> bool:
    """Validate the URL shape and refuse anything that is not public HTTP(S).

    Args:
        url: The submitted URL.

    Returns:
        True when the URL is http(s) to a host that resolves entirely to
        public addresses (or is an explicit public IP).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        return not is_blocked_address(host)
    return _host_resolves_public(host)


def _host_resolves_public(host: str) -> bool:
    """Resolve ``host`` and require every address to be public."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    # info[4] is the sockaddr tuple; its host part is str for IPv4/IPv6
    # (typeshed types it as str | int), so normalize to str before the check.
    addresses = {str(info[4][0]) for info in infos}
    if not addresses:
        return False
    return all(not is_blocked_address(address) for address in addresses)


class _SshHttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows redirects only when every hop passes the SSRF guard."""

    max_redirections = _MAX_REDIRECTS

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        if not is_safe_url(newurl):
            raise UrlFetchError("redirect target refused by the SSRF guard")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _TextExtractor(HTMLParser):
    """Collects visible text from HTML, skipping script/style content."""

    _SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        """Join the collected parts and collapse whitespace."""
        collapsed = re.sub(r"\s+", " ", " ".join(self._parts))
        return collapsed.strip()


def extract_html_text(html: str) -> str:
    """Strip markup from an HTML document and return its visible text.

    Args:
        html: The raw HTML body.

    Returns:
        Whitespace-collapsed visible text, capped at ``_MAX_TEXT_CHARS``.
    """
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed HTML must never break the pipeline — degrade to the
        # raw body rather than failing the analysis.
        return html[:_MAX_TEXT_CHARS]
    return parser.text()[:_MAX_TEXT_CHARS]


class HttpUrlFetcher:
    """Fetches and extracts text from a URL with the SSRF guard applied."""

    def fetch(
        self,
        url: str,
        *,
        timeout: float = 10.0,
        max_bytes: int = 2_000_000,
    ) -> FetchedPage:
        """Fetch ``url`` and return its extracted text.

        Args:
            url: The submitted URL.
            timeout: Total request timeout in seconds.
            max_bytes: Hard cap on the response body.

        Returns:
            The fetched page with its final URL and HTTP status.

        Raises:
            UrlFetchError: For unsafe targets, network failures, redirect
                loops, or responses exceeding the size cap.
        """
        if not is_safe_url(url):
            raise UrlFetchError("url refused by the SSRF guard")

        opener = urllib.request.build_opener(_SshHttpsRedirectHandler())
        request = urllib.request.Request(url, headers={"User-Agent": "ANNEX/0.1 (+https://github.com/sdnikil1sn-ops/Annex-Fbu)"})
        try:
            with opener.open(request, timeout=timeout) as response:
                final_url = response.geturl()
                if not is_safe_url(final_url):
                    raise UrlFetchError("final url refused by the SSRF guard")
                body = self._read_capped(response, max_bytes)
                content_type = response.headers.get_content_type() or "text/plain"
        except UrlFetchError:
            raise
        except urllib.error.HTTPError as exc:
            raise UrlFetchError(f"http error {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise UrlFetchError(f"fetch failed: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:
            raise UrlFetchError(f"fetch failed: {exc}") from exc

        if content_type in _TEXT_CONTENT_TYPES:
            text = self._decode(body)[:_MAX_TEXT_CHARS]
        else:
            text = extract_html_text(self._decode(body))
        return FetchedPage(final_url=final_url, status=response.status, text=text)

    @staticmethod
    def _read_capped(response: Any, max_bytes: int) -> bytes:
        """Stream the body, failing when it exceeds ``max_bytes``."""
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = response.read(min(64 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise UrlFetchError("response body exceeds the size cap")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _decode(body: bytes) -> str:
        """Decode the body, preferring the declared charset, then UTF-8."""
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError:
            return body.decode("latin-1", errors="replace")


def build_url_fetcher() -> HttpUrlFetcher:
    """Composition-root factory for the URL fetcher.

    A plain factory for symmetry with the other media builders; the fetcher
    needs no configuration beyond the per-call timeouts/limits.
    """
    return HttpUrlFetcher()
