import { describe, expect, it } from 'vitest';
import { humanize } from './badge';
import { DurationPipe } from './pipes';

describe('pipes', () => {
  it('formats durations with singular/plural units', () => {
    const p = new DurationPipe();
    expect(p.transform({ duration_value: 1, duration_unit: 'months' })).toBe('1 month');
    expect(p.transform({ duration_value: 30, duration_unit: 'days' })).toBe('30 days');
  });

  it('humanizes enum values', () => {
    expect(humanize('bank_transfer')).toBe('Bank transfer');
  });
});
