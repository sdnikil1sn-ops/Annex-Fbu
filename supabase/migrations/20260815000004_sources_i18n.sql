-- =====================================================================
-- ANNEX — Migration 20260815000004: sources UI translations
-- The source-registry chrome introduced in Phase 22 (tab title, search,
-- model score vs community labels, rating control). Keys follow the
-- typed registry in packages/shared_utils (ADR-0007): en is the
-- fallback root, pt defines a subset and everything else falls back to
-- en.
-- =====================================================================

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('sources', 'title', 'Sources', 'none'),
        ('sources', 'search_hint', 'Search publishers or domains…', 'none'),
        ('sources', 'search', 'Search', 'none'),
        ('sources', 'model_score', 'Model score', 'none'),
        ('sources', 'community', 'Community', 'none'),
        ('sources', 'rate', 'Rate this source', 'none'),
        ('sources', 'your_rating', 'Your rating', 'none'),
        ('sources', 'no_results', 'No sources found.', 'none'),
        ('sources', 'error', 'Could not load sources.', 'none'),
        ('sources', 'trust_signals', 'Trust signals', 'none'),
        ('sources', 'ratings_count', '{count} ratings', 'other'),
        ('sources', 'average', '{average} avg', 'other'),
        ('sources', 'score_label', 'Credibility score', 'none'),
        ('sources', 'community_empty', 'No community ratings yet.', 'none'),
        ('sources', 'open_profile', 'View profile', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'en'
on conflict (locale_id, namespace, key) do nothing;

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('sources', 'title', 'Fontes', 'none'),
        ('sources', 'search_hint', 'Pesquise publicadores ou domínios…', 'none'),
        ('sources', 'search', 'Pesquisar', 'none'),
        ('sources', 'model_score', 'Pontuação do modelo', 'none'),
        ('sources', 'community', 'Comunidade', 'none'),
        ('sources', 'rate', 'Avaliar esta fonte', 'none'),
        ('sources', 'your_rating', 'Sua avaliação', 'none'),
        ('sources', 'no_results', 'Nenhuma fonte encontrada.', 'none'),
        ('sources', 'error', 'Não foi possível carregar as fontes.', 'none'),
        ('sources', 'trust_signals', 'Sinais de confiança', 'none'),
        ('sources', 'ratings_count', '{count} avaliações', 'other'),
        ('sources', 'average', '{average} média', 'other'),
        ('sources', 'score_label', 'Pontuação de credibilidade', 'none'),
        ('sources', 'community_empty', 'Nenhuma avaliação da comunidade ainda.', 'none'),
        ('sources', 'open_profile', 'Ver perfil', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'pt'
on conflict (locale_id, namespace, key) do nothing;
