-- =====================================================================
-- ANNEX — Migration 20260812000004: source registry seed (Phase 14)
-- Baseline publishers/domains with explainable credibility scores so the
-- v1 /sources endpoints return real data. The model is 'seed-v1': a
-- curated baseline, superseded by computed scores as background scoring
-- lands. Fictional low-trust domains demonstrate the score range.
-- =====================================================================

insert into public.sources (domain, name, country, language, category)
values
    ('reuters.com', 'Reuters', 'US', 'en', 'news'),
    ('apnews.com', 'AP News', 'US', 'en', 'news'),
    ('bbc.com', 'BBC', 'GB', 'en', 'news'),
    ('theguardian.com', 'The Guardian', 'GB', 'en', 'news'),
    ('snopes.com', 'Snopes', 'US', 'en', 'fact_check'),
    ('conspiracy-news.net', 'Conspiracy News', 'US', 'en', 'blog'),
    ('fakeheadlines.xyz', 'Fake Headlines', null, 'en', 'satire')
on conflict (domain) do nothing;

insert into public.source_scores (source_id, score, signals, model)
select s.id, v.score, v.signals::jsonb, 'seed-v1'
from (
    values
        ('reuters.com', 0.92, '{"editorial_standards": "high", "fact_checking": "strong"}'),
        ('apnews.com', 0.91, '{"editorial_standards": "high", "fact_checking": "strong"}'),
        ('bbc.com', 0.89, '{"editorial_standards": "high", "fact_checking": "strong"}'),
        ('theguardian.com', 0.84, '{"editorial_standards": "medium", "fact_checking": "strong"}'),
        ('snopes.com', 0.95, '{"editorial_standards": "high", "fact_checking": "dedicated"}'),
        ('conspiracy-news.net', 0.18, '{"editorial_standards": "low", "fact_checking": "none"}'),
        ('fakeheadlines.xyz', 0.05, '{"editorial_standards": "low", "fact_checking": "none", "satire": true}')
) as v(domain, score, signals)
join public.sources s on s.domain = v.domain;
