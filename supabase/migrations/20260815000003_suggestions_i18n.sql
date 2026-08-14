-- =====================================================================
-- ANNEX — Migration 20260815000003: translation-suggestion UI strings
-- The contributor chrome introduced in Phase 21 (tab title, propose
-- dialog, status labels). Keys follow the typed registry in
-- packages/shared_utils (ADR-0007): en is the fallback root, pt defines
-- a subset and everything else falls back to en.
-- =====================================================================

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('suggestions', 'title', 'Contribute', 'none'),
        ('suggestions', 'missing', 'Untranslated keys', 'none'),
        ('suggestions', 'propose', 'Propose translation', 'none'),
        ('suggestions', 'your_submissions', 'Your submissions', 'none'),
        ('suggestions', 'empty', 'No untranslated keys — this language is complete.', 'none'),
        ('suggestions', 'error', 'Could not load translation suggestions.', 'none'),
        ('suggestions', 'no_submissions', 'You have not submitted any translations yet.', 'none'),
        ('suggestions', 'value', 'Your translation', 'none'),
        ('suggestions', 'english', 'English', 'none'),
        ('suggestions', 'status_pending', 'Pending review', 'none'),
        ('suggestions', 'status_approved', 'Approved', 'none'),
        ('suggestions', 'status_rejected', 'Rejected', 'none'),
        ('suggestions', 'submitted', 'Submitted for review.', 'none'),
        ('suggestions', 'locale', 'Language', 'none'),
        ('suggestions', 'contributor_note', 'Help translate ANNEX into your language.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'en'
on conflict (locale_id, namespace, key) do nothing;

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('suggestions', 'title', 'Contribuir', 'none'),
        ('suggestions', 'missing', 'Chaves não traduzidas', 'none'),
        ('suggestions', 'propose', 'Propor tradução', 'none'),
        ('suggestions', 'your_submissions', 'Suas contribuições', 'none'),
        ('suggestions', 'empty', 'Nenhuma chave não traduzida — este idioma está completo.', 'none'),
        ('suggestions', 'error', 'Não foi possível carregar as sugestões de tradução.', 'none'),
        ('suggestions', 'no_submissions', 'Você ainda não enviou traduções.', 'none'),
        ('suggestions', 'value', 'Sua tradução', 'none'),
        ('suggestions', 'english', 'Inglês', 'none'),
        ('suggestions', 'status_pending', 'Em análise', 'none'),
        ('suggestions', 'status_approved', 'Aprovada', 'none'),
        ('suggestions', 'status_rejected', 'Rejeitada', 'none'),
        ('suggestions', 'submitted', 'Enviada para revisão.', 'none'),
        ('suggestions', 'locale', 'Idioma', 'none'),
        ('suggestions', 'contributor_note', 'Ajude a traduzir o ANNEX para o seu idioma.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'pt'
on conflict (locale_id, namespace, key) do nothing;
