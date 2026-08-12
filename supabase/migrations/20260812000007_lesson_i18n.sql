-- =====================================================================
-- ANNEX — Migration 20260812000007: lessons UI translations
-- The curriculum UI chrome introduced in Phase 16 (tab title, completion
-- labels, difficulty names, minutes template). Keys follow the typed
-- registry in packages/shared_utils (ADR-0007): en is the fallback root,
-- pt defines a subset and everything else falls back to en.
-- =====================================================================

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('lessons', 'title', 'Lessons', 'none'),
        ('lessons', 'complete', 'Mark complete', 'none'),
        ('lessons', 'completed', 'Completed', 'none'),
        ('lessons', 'minutes', '{minutes} min', 'other'),
        ('lessons', 'difficulty', 'Difficulty', 'none'),
        ('lessons', 'difficulty_beginner', 'Beginner', 'none'),
        ('lessons', 'difficulty_intermediate', 'Intermediate', 'none'),
        ('lessons', 'difficulty_advanced', 'Advanced', 'none'),
        ('lessons', 'empty', 'No lessons available yet.', 'none'),
        ('lessons', 'error', 'Could not load lessons.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'en'
on conflict (locale_id, namespace, key) do nothing;

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('lessons', 'title', 'Lições', 'none'),
        ('lessons', 'complete', 'Concluir', 'none'),
        ('lessons', 'completed', 'Concluído', 'none'),
        ('lessons', 'difficulty_beginner', 'Iniciante', 'none'),
        ('lessons', 'difficulty_intermediate', 'Intermediário', 'none'),
        ('lessons', 'difficulty_advanced', 'Avançado', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'pt'
on conflict (locale_id, namespace, key) do nothing;
