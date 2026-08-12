-- =====================================================================
-- ANNEX — Migration 20260812000006: lesson seed data
-- Baseline media-literacy curriculum (Phase 15): four lessons with full
-- English content plus a Portuguese variant for the first lesson so the
-- localization path is exercised (missing locales fall back to en).
-- Sections are a JSON array of {heading, body, bullets?} objects.
-- =====================================================================

insert into public.lessons (slug, difficulty, category, estimated_minutes, order_index, published) values
    ('spotting-misinformation', 'beginner', 'media_literacy', 5, 1, true),
    ('understanding-credibility-scores', 'intermediate', 'source_credibility', 7, 2, true),
    ('verifying-images', 'intermediate', 'media_literacy', 8, 3, true),
    ('analyzing-claims', 'advanced', 'critical_thinking', 10, 4, true)
on conflict (slug) do nothing;

-- ---------------------------------------------------------------------
-- English — the fallback root for every lesson.
-- ---------------------------------------------------------------------
insert into public.lesson_contents (lesson_id, locale_id, title, summary, sections)
select l.id, loc.id, t.title, t.summary, t.sections::jsonb
from public.lessons l,
     public.i18n_locales loc,
     (values
        ('spotting-misinformation',
         'Spotting Misinformation',
         'Learn to recognize the common patterns behind misleading content.',
         '[{"heading": "Why misinformation spreads", "body": "Misinformation spreads faster than corrections because it is designed to be shared: strong emotions, simple messages, and confirmation bias all help it travel.", "bullets": ["Emotional headlines are a red flag", "Check before you share", "Slow reading beats skim reading"]}, {"heading": "The five-question check", "body": "Before trusting a post, ask five questions: Who published it? What is the evidence? When was it written? Why does it exist? How does it make you feel?", "bullets": ["Who", "What", "When", "Why", "How"]}]'),
        ('understanding-credibility-scores',
         'Understanding Credibility Scores',
         'How ANNEX scores sources and what the numbers mean.',
         '[{"heading": "What a credibility score is", "body": "A credibility score is a 0 to 1 estimate of how trustworthy a publisher or domain is, built from editorial standards, fact-checking history, and correction behavior."}, {"heading": "Reading the range", "body": "Scores above 0.7 reflect strong editorial practices; scores below 0.4 indicate consistent problems with accuracy or transparency.", "bullets": ["0.7–1.0: strong", "0.4–0.7: mixed", "0.0–0.4: weak"]}]'),
        ('verifying-images',
         'Verifying Images',
         'Use OCR, forensics, and reverse search to test an image before believing it.',
         '[{"heading": "Why images need verification", "body": "Images are easy to take out of context: an old photo can be attached to a new claim, and edits can change meaning without leaving obvious traces."}, {"heading": "ANNEX image tools", "body": "ANNEX runs OCR to read embedded text and forensics to detect tampering signals, giving you a head start on verification.", "bullets": ["Read the text with OCR", "Check forensics signals", "Search the image source"]}]'),
        ('analyzing-claims',
         'Analyzing Claims',
         'Break any statement into verifiable parts and weigh the evidence.',
         '[{"heading": "Claims are decomposable", "body": "A single statement usually contains several checkable claims. Splitting them lets you verify each part instead of accepting or rejecting the whole."}, {"heading": "Weighing evidence", "body": "Evidence is stronger when it is recent, sourced, and independently corroborated. Verdicts reflect how well the evidence supports the claim.", "bullets": ["Split the claim", "Find the evidence", "Judge the verdict"]}]')
     ) as t (slug, title, summary, sections)
where l.slug = t.slug and loc.code = 'en'
on conflict (lesson_id, locale_id) do nothing;

-- ---------------------------------------------------------------------
-- Portuguese — only the first lesson; the rest fall back to en.
-- ---------------------------------------------------------------------
insert into public.lesson_contents (lesson_id, locale_id, title, summary, sections)
select l.id, loc.id, t.title, t.summary, t.sections::jsonb
from public.lessons l,
     public.i18n_locales loc,
     (values
        ('spotting-misinformation',
         'Como Detectar Desinformação',
         'Aprenda a reconhecer os padrões comuns por trás de conteúdos enganosos.',
         '[{"heading": "Por que a desinformação se espalha", "body": "A desinformação se espalha mais rápido que correções porque é feita para ser compartilhada: emoções fortes, mensagens simples e viés de confirmação ajudam a viajar.", "bullets": ["Títulos emocionais são um sinal de alerta", "Verifique antes de compartilhar", "Ler devagar vence a leitura superficial"]}, {"heading": "A checagem das cinco perguntas", "body": "Antes de confiar em uma publicação, faça cinco perguntas: Quem publicou? Qual é a evidência? Quando foi escrita? Por que existe? Como ela faz você se sentir?", "bullets": ["Quem", "O quê", "Quando", "Por quê", "Como"]}]')
     ) as t (slug, title, summary, sections)
where l.slug = t.slug and loc.code = 'pt'
on conflict (lesson_id, locale_id) do nothing;
