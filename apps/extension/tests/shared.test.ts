import { describe, expect, it } from 'vitest';
import { StringKeys, resolveFallbackChain, translate, TranslationBundle } from '../src/shared/i18n';
import { AnalysisReport, credibilityScore, isTerminal } from '../src/shared/analysis';

const en: TranslationBundle = {
  locale: 'en',
  fallback_locale: null,
  version: 1,
  entries: {
    'analysis.submit': { value: 'Analyze', plural: 'none' },
    'common.retry': { value: 'Retry', plural: 'none' },
  },
};

const ptBR: TranslationBundle = {
  locale: 'pt-BR',
  fallback_locale: 'pt',
  version: 1,
  entries: {
    'analysis.submit': { value: 'Analisar', plural: 'none' },
  },
};

describe('resolveFallbackChain', () => {
  it('walks parent fallbacks then the default', () => {
    const locales = new Map<string, string | null>([
      ['pt-BR', 'pt'],
      ['pt', 'en'],
      ['en', null],
    ]);
    expect(resolveFallbackChain('pt-BR', locales, 'en')).toEqual(['pt-BR', 'pt', 'en']);
  });

  it('avoids cycles and always terminates at the default', () => {
    const locales = new Map<string, string | null>([
      ['a', 'b'],
      ['b', 'a'],
    ]);
    const chain = resolveFallbackChain('a', locales, 'en');
    expect(chain[chain.length - 1]).toBe('en');
    expect(new Set(chain).size).toBe(chain.length);
  });

  it('treats a missing locale as falling straight to the default', () => {
    expect(resolveFallbackChain('de', new Map(), 'en')).toEqual(['de', 'en']);
  });
});

describe('translate', () => {
  it('resolves a typed key from the bundle', () => {
    expect(translate(StringKeys.analysisSubmit, en)).toBe('Analyze');
    expect(translate(StringKeys.analysisSubmit, ptBR)).toBe('Analisar');
  });

  it('falls back to the raw key when the entry is missing', () => {
    expect(translate('analysis.nope', en)).toBe('analysis.nope');
  });
});

describe('analysis helpers', () => {
  it('credibilityScore is the mean claim verifiability', () => {
    const report: AnalysisReport = {
      summary: 's',
      claims: [
        { text: 'a', verifiability: 1 },
        { text: 'b', verifiability: 0.5 },
      ],
    };
    expect(credibilityScore(report)).toBeCloseTo(0.75);
  });

  it('credibilityScore is 0 with no claims', () => {
    expect(credibilityScore({ summary: 's', claims: [] })).toBe(0);
  });

  it('isTerminal covers completed and failed only', () => {
    expect(isTerminal('completed')).toBe(true);
    expect(isTerminal('failed')).toBe(true);
    expect(isTerminal('pending')).toBe(false);
    expect(isTerminal('processing')).toBe(false);
  });
});
