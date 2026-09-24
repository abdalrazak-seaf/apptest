import { formatDate, formatNumber } from './format';

describe('formatNumber', () => {
  it('uses Western digits in both languages, which is how Saudi prices are written', () => {
    expect(formatNumber(90000, 'ar')).toBe('90,000');
    expect(formatNumber(90000, 'en')).toBe('90,000');
  });

  it('groups large numbers', () => {
    expect(formatNumber(1234567, 'ar')).toContain('1,234,567');
  });
});

describe('formatDate', () => {
  it('formats with Western digits in Arabic too', () => {
    const formatted = formatDate('2026-09-24T10:00:00Z', 'ar');
    expect(formatted).toMatch(/2026/);
    expect(formatted).not.toMatch(/[٠-٩]/);
  });
});
