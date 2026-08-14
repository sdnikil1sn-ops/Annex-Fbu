-- =====================================================================
-- ANNEX — Migration 20260815000005: moderator review queue UI strings
-- The reviewer chrome introduced in Phase 23 (queue heading, approve /
-- reject actions, empty state). Keys follow the typed registry in
-- packages/shared_utils (ADR-0007): en is the fallback root, pt defines
-- a subset and everything else falls back to en.
-- =====================================================================

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('suggestions', 'review_queue', 'Review queue', 'none'),
        ('suggestions', 'approve', 'Approve', 'none'),
        ('suggestions', 'reject', 'Reject', 'none'),
        ('suggestions', 'no_pending', 'No suggestions waiting for review.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'en'
on conflict (locale_id, namespace, key) do nothing;

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('suggestions', 'review_queue', 'Fila de revisão', 'none'),
        ('suggestions', 'approve', 'Aprovar', 'none'),
        ('suggestions', 'reject', 'Rejeitar', 'none'),
        ('suggestions', 'no_pending', 'Nenhuma sugestão aguardando revisão.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'pt'
on conflict (locale_id, namespace, key) do nothing;
