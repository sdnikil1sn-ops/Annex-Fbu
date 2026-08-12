-- =====================================================================
-- ANNEX — Migration 20260812000003: i18n seed data
-- Runtime translation delivery (ADR-0007): locales + translations that
-- make the bundle API usable out of the box. English is the fallback
-- root; the other locales define a subset so missing keys resolve
-- through the chain (pt -> en, es -> en, ...) — exactly the contract
-- clients rely on. Adding a language is a data change, never a rebuild.
-- =====================================================================

-- Enabled locales with their fallback chain. The default locale (en)
-- carries no fallback and terminates every chain.
insert into public.i18n_locales (code, enabled, fallback_code) values
    ('en', true, null),
    ('pt', true, 'en'),
    ('es', true, 'en'),
    ('fr', true, 'en'),
    ('de', true, 'en'),
    ('ar', true, 'en'),
    ('ja', true, 'en')
on conflict (code) do nothing;

-- ---------------------------------------------------------------------
-- English — base locale (the fallback root).
-- ---------------------------------------------------------------------
insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('common', 'cancel', 'Cancel', 'none'),
        ('common', 'save', 'Save', 'none'),
        ('common', 'retry', 'Retry', 'none'),
        ('common', 'loading', 'Loading…', 'none'),
        ('common', 'close', 'Close', 'none'),
        ('common', 'learn_before_you_believe', 'Learn before you believe.', 'none'),
        ('common', 'claims_count', '{count} claims', 'other'),
        ('analysis', 'submit', 'Analyze', 'none'),
        ('analysis', 'pending', 'Analysis in progress…', 'none'),
        ('analysis', 'completed', 'Analysis complete', 'none'),
        ('analysis', 'failed', 'Analysis failed', 'none'),
        ('analysis', 'summary', 'Summary', 'none'),
        ('analysis', 'credibility_score', 'Credibility score', 'none'),
        ('auth', 'sign_in', 'Sign in', 'none'),
        ('auth', 'sign_out', 'Sign out', 'none'),
        ('errors', 'generic', 'Something went wrong. Please try again.', 'none'),
        ('errors', 'not_found', 'Not found.', 'none'),
        ('errors', 'rate_limited', 'Too many requests. Try again shortly.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'en'
on conflict (locale_id, namespace, key) do nothing;

-- ---------------------------------------------------------------------
-- Portuguese — common and analysis keys; the rest fall back to en.
-- ---------------------------------------------------------------------
insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('common', 'cancel', 'Cancelar', 'none'),
        ('common', 'save', 'Salvar', 'none'),
        ('common', 'retry', 'Tentar novamente', 'none'),
        ('common', 'loading', 'Carregando…', 'none'),
        ('common', 'claims_count', '{count} alegações', 'other'),
        ('analysis', 'submit', 'Analisar', 'none'),
        ('analysis', 'pending', 'Análise em andamento…', 'none'),
        ('analysis', 'completed', 'Análise concluída', 'none'),
        ('analysis', 'failed', 'Falha na análise', 'none'),
        ('auth', 'sign_in', 'Entrar', 'none'),
        ('errors', 'generic', 'Algo deu errado. Tente novamente.', 'none'),
        ('errors', 'rate_limited', 'Muitas solicitações. Tente novamente em breve.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'pt'
on conflict (locale_id, namespace, key) do nothing;

-- ---------------------------------------------------------------------
-- Spanish.
-- ---------------------------------------------------------------------
insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('common', 'cancel', 'Cancelar', 'none'),
        ('common', 'save', 'Guardar', 'none'),
        ('common', 'retry', 'Reintentar', 'none'),
        ('common', 'loading', 'Cargando…', 'none'),
        ('common', 'claims_count', '{count} afirmaciones', 'other'),
        ('analysis', 'submit', 'Analizar', 'none'),
        ('analysis', 'pending', 'Análisis en curso…', 'none'),
        ('analysis', 'completed', 'Análisis completado', 'none'),
        ('analysis', 'failed', 'El análisis falló', 'none'),
        ('auth', 'sign_in', 'Iniciar sesión', 'none'),
        ('errors', 'generic', 'Algo salió mal. Inténtalo de nuevo.', 'none'),
        ('errors', 'rate_limited', 'Demasiadas solicitudes. Inténtalo más tarde.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'es'
on conflict (locale_id, namespace, key) do nothing;

-- ---------------------------------------------------------------------
-- French.
-- ---------------------------------------------------------------------
insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('common', 'cancel', 'Annuler', 'none'),
        ('common', 'save', 'Enregistrer', 'none'),
        ('common', 'retry', 'Réessayer', 'none'),
        ('common', 'loading', 'Chargement…', 'none'),
        ('common', 'claims_count', '{count} affirmations', 'other'),
        ('analysis', 'submit', 'Analyser', 'none'),
        ('analysis', 'pending', 'Analyse en cours…', 'none'),
        ('analysis', 'completed', 'Analyse terminée', 'none'),
        ('analysis', 'failed', 'L''analyse a échoué', 'none'),
        ('auth', 'sign_in', 'Se connecter', 'none'),
        ('errors', 'generic', 'Une erreur est survenue. Réessayez plus tard.', 'none'),
        ('errors', 'rate_limited', 'Trop de requêtes. Réessayez bientôt.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'fr'
on conflict (locale_id, namespace, key) do nothing;

-- ---------------------------------------------------------------------
-- German.
-- ---------------------------------------------------------------------
insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('common', 'cancel', 'Abbrechen', 'none'),
        ('common', 'save', 'Speichern', 'none'),
        ('common', 'retry', 'Erneut versuchen', 'none'),
        ('common', 'loading', 'Wird geladen…', 'none'),
        ('common', 'claims_count', '{count} Behauptungen', 'other'),
        ('analysis', 'submit', 'Analysieren', 'none'),
        ('analysis', 'pending', 'Analyse läuft…', 'none'),
        ('analysis', 'completed', 'Analyse abgeschlossen', 'none'),
        ('analysis', 'failed', 'Analyse fehlgeschlagen', 'none'),
        ('auth', 'sign_in', 'Anmelden', 'none'),
        ('errors', 'generic', 'Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.', 'none'),
        ('errors', 'rate_limited', 'Zu viele Anfragen. Versuchen Sie es später erneut.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'de'
on conflict (locale_id, namespace, key) do nothing;

-- ---------------------------------------------------------------------
-- Arabic — right-to-left locale (design system renders RTL when active).
-- ---------------------------------------------------------------------
insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('common', 'cancel', 'إلغاء', 'none'),
        ('common', 'save', 'حفظ', 'none'),
        ('common', 'retry', 'إعادة المحاولة', 'none'),
        ('common', 'loading', 'جارٍ التحميل…', 'none'),
        ('common', 'claims_count', '{count} ادعاءات', 'other'),
        ('analysis', 'submit', 'تحليل', 'none'),
        ('analysis', 'pending', 'التحليل قيد التنفيذ…', 'none'),
        ('analysis', 'completed', 'اكتمل التحليل', 'none'),
        ('analysis', 'failed', 'فشل التحليل', 'none'),
        ('auth', 'sign_in', 'تسجيل الدخول', 'none'),
        ('errors', 'generic', 'حدث خطأ ما. يرجى المحاولة مرة أخرى.', 'none'),
        ('errors', 'rate_limited', 'طلبات كثيرة جدًا. حاول مرة أخرى قريبًا.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'ar'
on conflict (locale_id, namespace, key) do nothing;

-- ---------------------------------------------------------------------
-- Japanese.
-- ---------------------------------------------------------------------
insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('common', 'cancel', 'キャンセル', 'none'),
        ('common', 'save', '保存', 'none'),
        ('common', 'retry', '再試行', 'none'),
        ('common', 'loading', '読み込み中…', 'none'),
        ('common', 'claims_count', '{count}件の主張', 'other'),
        ('analysis', 'submit', '分析', 'none'),
        ('analysis', 'pending', '分析中…', 'none'),
        ('analysis', 'completed', '分析完了', 'none'),
        ('analysis', 'failed', '分析に失敗しました', 'none'),
        ('auth', 'sign_in', 'サインイン', 'none'),
        ('errors', 'generic', 'エラーが発生しました。もう一度お試しください。', 'none'),
        ('errors', 'rate_limited', 'リクエストが多すぎます。しばらくしてからお試しください。', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'ja'
on conflict (locale_id, namespace, key) do nothing;
