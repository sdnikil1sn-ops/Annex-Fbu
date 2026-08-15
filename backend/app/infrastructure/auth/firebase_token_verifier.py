"""Firebase ID-token verification via the Firebase Admin SDK (ADR-0005).

Verification is delegated to the Admin SDK (signature, issuer, audience,
and expiry checks). Failures are normalized to ``TokenVerificationError``
so callers never see Firebase-specific internals.

Firebase UIDs (``sub``) are opaque strings, not UUIDs, while the domain
model keys users by UUID (``users.id``). The verifier therefore maps every
UID deterministically: a UID that is already a UUID passes through, and
any other string becomes a stable UUID v5 under the Firebase namespace.
This keeps the auth contract valid for real Google/email accounts (and
tests) instead of raising on the first authenticated request.
"""

from __future__ import annotations

from uuid import NAMESPACE_DNS, UUID, uuid5

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin.credentials import Certificate
from google.auth.exceptions import DefaultCredentialsError

from app.application.ports.auth import TokenVerificationError, TokenVerifier, VerifiedIdentity
from app.core.exceptions import ConfigurationError

# Guard so repeated verifier construction (e.g. across test app builds)
# reuses the single process-wide Firebase app instead of erroring.
_APP_INITIALIZED = False

# Fixed namespace so the same Firebase UID always maps to the same UUID
# across processes (required for user rows to stay stable per account).
_FIREBASE_UID_NAMESPACE = NAMESPACE_DNS


def firebase_uid_to_uuid(firebase_uid: str) -> UUID:
    """Map a Firebase UID to the stable UUID used as the user primary key.

    Args:
        firebase_uid: The opaque ``sub`` claim from a verified ID token.

    Returns:
        The UID itself when it is already a UUID, otherwise a deterministic
        UUID v5 derived from the Firebase namespace + UID.
    """
    try:
        return UUID(firebase_uid)
    except (ValueError, AttributeError):
        return uuid5(_FIREBASE_UID_NAMESPACE, f"firebase:{firebase_uid}")


class FirebaseTokenVerifier(TokenVerifier):
    """Verifies Firebase ID tokens with the Admin SDK.

    Args:
        project_id: Firebase project ID (used for the audience check).
        service_account_path: Path to the service-account JSON. When None,
            Google Application Default Credentials are attempted.

    Raises:
        ConfigurationError: When the Admin SDK cannot initialize.
    """

    def __init__(self, project_id: str, service_account_path: str | None = None) -> None:
        global _APP_INITIALIZED
        if not _APP_INITIALIZED:
            try:
                if service_account_path:
                    firebase_admin.initialize_app(
                        Certificate(service_account_path),
                        options={"projectId": project_id},
                    )
                else:
                    firebase_admin.initialize_app(options={"projectId": project_id})
            except (OSError, ValueError, DefaultCredentialsError) as exc:
                raise ConfigurationError(f"firebase admin initialization failed: {exc}") from exc
            _APP_INITIALIZED = True
        self._project_id = project_id

    def verify(self, token: str) -> VerifiedIdentity:
        """Verify a Firebase ID token and extract the identity.

        Args:
            token: The raw Firebase ID token.

        Returns:
            The verified identity (uid, email, display name).

        Raises:
            TokenVerificationError: For expired, malformed, revoked, or
                otherwise unverifiable tokens.
        """
        try:
            decoded = firebase_auth.verify_id_token(token, check_revoked=False)
        except (
            firebase_auth.InvalidIdTokenError,
            firebase_auth.ExpiredIdTokenError,
            firebase_auth.RevokedIdTokenError,
            firebase_auth.CertificateFetchError,
            firebase_auth.UserDisabledError,
        ) as exc:
            raise TokenVerificationError(str(exc)) from exc
        return VerifiedIdentity(
            uid=firebase_uid_to_uuid(decoded["sub"]),
            email=decoded.get("email"),
            display_name=decoded.get("name"),
        )
