"""Runtime i18n domain model (ADR-0007).

Pure value objects and fallback-chain logic for versioned translation
bundles. No infrastructure here: repositories load raw rows, the service
orchestrates resolution, and clients consume the resolved bundles served
by the API.

Fallback chain (requested → parent → … → default):

    requested locale → its declared fallback → … → the default locale

A bundle for ``pt`` whose chain is ``[pt, en]`` contains the Portuguese
entries plus every key the Portuguese set does not define, filled from
``en``. The requested locale always wins over its fallbacks.

Phase 18 adds community contribution: ``TranslationSuggestion`` (a
proposed value for a key) and ``MissingKey`` (a key the default locale
defines that a target locale has not translated yet). Approved
suggestions are published into ``i18n_translations`` with a version
bump so bundles refresh over the air.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

# Suggestion lifecycle states (Phase 18).
SUGGESTION_PENDING = "pending"
SUGGESTION_APPROVED = "approved"
SUGGESTION_REJECTED = "rejected"
SUGGESTION_STATUSES = (SUGGESTION_PENDING, SUGGESTION_APPROVED, SUGGESTION_REJECTED)


@dataclass(frozen=True)
class I18nLocale:
    """An enabled locale with its parent for the fallback chain.

    Attributes:
        code: BCP-47-style tag, lower-cased (e.g. ``en``, ``pt-BR``).
        fallback_code: Parent locale code, or None for the default locale.
    """

    code: str
    fallback_code: str | None = None


@dataclass(frozen=True)
class TranslationEntry:
    """One translated string for a locale/namespace/key.

    Attributes:
        namespace: Feature/domain namespace (e.g. ``common``, ``analysis``).
        key: Stable, typed key within the namespace (ADR-0007).
        value: The translated string.
        plural_rule: ICU plural category of the stored form (``none`` when
            the value is plural-invariant); plural expansion is client-side.
        version: Monotonic revision; bumping it invalidates client caches.
    """

    namespace: str
    key: str
    value: str
    plural_rule: str = "none"
    version: int = 1

    @property
    def full_key(self) -> str:
        """The dotted ``namespace.key`` identifier clients reference."""
        return f"{self.namespace}.{self.key}"


@dataclass(frozen=True)
class MissingKey:
    """A key the default locale defines that a target locale lacks.

    Attributes:
        namespace: Feature/domain namespace (e.g. ``common``).
        key: Stable, typed key within the namespace.
        english_value: The default-locale source text contributors
            translate from.
    """

    namespace: str
    key: str
    english_value: str

    @property
    def full_key(self) -> str:
        """The dotted ``namespace.key`` identifier clients reference."""
        return f"{self.namespace}.{self.key}"


@dataclass(frozen=True)
class TranslationSuggestion:
    """A community-proposed translation awaiting (or after) review.

    Attributes:
        id: Primary key of the ``translation_suggestions`` row.
        locale_code: The target locale the value translates into.
        namespace: Feature/domain namespace of the key.
        key: Stable, typed key within the namespace.
        value: The proposed translation.
        plural_rule: ICU plural category of the proposed form.
        suggested_by: The contributor's user id.
        status: ``pending`` | ``approved`` | ``rejected``.
        created_at: When the suggestion was submitted.
        reviewed_by: The moderator who reviewed it, when reviewed.
        reviewed_at: When the review happened, when reviewed.
    """

    locale_code: str
    namespace: str
    key: str
    value: str
    id: UUID = field(default_factory=uuid4)
    plural_rule: str = "none"
    suggested_by: UUID | None = None
    status: str = SUGGESTION_PENDING
    created_at: datetime | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None

    @property
    def full_key(self) -> str:
        """The dotted ``namespace.key`` identifier clients reference."""
        return f"{self.namespace}.{self.key}"


@dataclass(frozen=True)
class ResolvedBundle:
    """A fully resolved bundle for one locale (fallbacks merged).

    Attributes:
        locale: The requested locale code.
        fallback_locale: Immediate parent in the chain, or None when the
            requested locale is the default.
        version: Max entry version in the merged bundle — the cache key
            clients use for conditional requests.
        entries: Merged translations keyed by full key; the requested
            locale's values win over fallbacks.
    """

    locale: str
    fallback_locale: str | None
    version: int
    entries: dict[str, TranslationEntry]


def resolve_fallback_chain(
    locale: str,
    locales: dict[str, I18nLocale],
    default_locale: str,
) -> list[str]:
    """Return the ordered fallback chain for a locale.

    Args:
        locale: The requested locale code (must exist in ``locales``).
        locales: All enabled locales keyed by code.
        default_locale: The chain root — always appended last.

    Returns:
        The chain from ``locale`` to ``default_locale`` inclusive, e.g.
        ``["pt", "en"]``. Cycles in fallback declarations are broken by
        visiting each locale at most once; a fallback pointing at an
        unknown locale simply terminates the chain there.
    """
    chain: list[str] = []
    seen: set[str] = set()
    current: str | None = locale
    while current is not None and current not in seen:
        seen.add(current)
        chain.append(current)
        node = locales.get(current)
        current = node.fallback_code if node else None
    if chain[-1] != default_locale:
        chain.append(default_locale)
    return chain


def merge_entries(
    entries_by_locale: dict[str, list[TranslationEntry]],
) -> dict[str, TranslationEntry]:
    """Merge per-locale entries so earlier locales in the chain win.

    Args:
        entries_by_locale: Translations keyed by locale code, ordered from
            the requested locale down to the default.

    Returns:
        A merged map keyed by full key; the first occurrence (the most
        specific locale) is kept.
    """
    merged: dict[str, TranslationEntry] = {}
    for entries in entries_by_locale.values():
        for entry in entries:
            merged.setdefault(entry.full_key, entry)
    return merged
