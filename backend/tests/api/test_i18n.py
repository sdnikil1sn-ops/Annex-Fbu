"""API tests: the i18n locale and bundle endpoints (ADR-0007).

The i18n endpoints are public (no auth). The ``i18n_client`` fixture wires
the seeded in-memory repository; the plain ``client`` fixture has no i18n
service and exercises the 503 path.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_locales_returns_enabled_locales(i18n_client: TestClient) -> None:
    """GET /i18n/locales returns the default locale and enabled set."""
    response = i18n_client.get("/api/v1/i18n/locales")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["default_locale"] == "en"
    by_code = {locale["code"]: locale["fallback_code"] for locale in data["locales"]}
    assert by_code == {"en": None, "pt": "en", "es": "en"}


def test_default_bundle_is_served(i18n_client: TestClient) -> None:
    """GET /i18n/bundles/en returns the full English bundle."""
    response = i18n_client.get("/api/v1/i18n/bundles/en")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["locale"] == "en"
    assert data["fallback_locale"] is None
    assert data["entries"]["common.cancel"] == {"value": "Cancel", "plural": "none"}
    assert data["entries"]["errors.generic"]["value"] == "Something went wrong. Please try again."


def test_bundle_resolves_fallback_chain(i18n_client: TestClient) -> None:
    """pt wins on its keys; missing keys fall back to en."""
    response = i18n_client.get("/api/v1/i18n/bundles/pt")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["locale"] == "pt"
    assert data["fallback_locale"] == "en"
    assert data["entries"]["common.cancel"]["value"] == "Cancelar"
    assert data["entries"]["errors.generic"]["value"] == "Something went wrong. Please try again."


def test_bundle_supports_version_param(i18n_client: TestClient) -> None:
    """Passing the current version yields 304; a stale one yields 200."""
    fresh = i18n_client.get("/api/v1/i18n/bundles/pt")
    version = fresh.json()["data"]["version"]

    cached = i18n_client.get(f"/api/v1/i18n/bundles/pt?version={version}")
    assert cached.status_code == 304

    stale = i18n_client.get(f"/api/v1/i18n/bundles/pt?version={version + 1}")
    assert stale.status_code == 200


def test_bundle_supports_if_none_match(i18n_client: TestClient) -> None:
    """The ETag header participates in conditional requests."""
    fresh = i18n_client.get("/api/v1/i18n/bundles/en")
    etag = fresh.headers["ETag"]

    cached = i18n_client.get("/api/v1/i18n/bundles/en", headers={"If-None-Match": etag})
    assert cached.status_code == 304


def test_bundle_sets_cache_headers(i18n_client: TestClient) -> None:
    """Bundle responses are cacheable with the configured TTL."""
    response = i18n_client.get("/api/v1/i18n/bundles/en")
    assert response.headers["Cache-Control"] == "public, max-age=300"
    assert response.headers["ETag"].startswith('"en:')


def test_unknown_locale_returns_404(i18n_client: TestClient) -> None:
    """A locale outside the enabled set answers the standard 404 envelope."""
    response = i18n_client.get("/api/v1/i18n/bundles/zz")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "i18n.locale_not_found"


def test_malformed_locale_returns_400(i18n_client: TestClient) -> None:
    """A malformed locale code is rejected as a validation error."""
    response = i18n_client.get("/api/v1/i18n/bundles/not a locale")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation.invalid_locale"


def test_i18n_not_configured_returns_503(client: TestClient) -> None:
    """Without an i18n service the endpoints answer 503 (like analysis)."""
    response = client.get("/api/v1/i18n/bundles/en")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "i18n.not_configured"
