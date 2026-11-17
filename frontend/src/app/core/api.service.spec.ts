import { describe, expect, it } from 'vitest';
import { errorMessage } from './api.service';

describe('errorMessage', () => {
  it('returns string details as-is', () => {
    expect(errorMessage({ error: { detail: 'You have already checked in today.' } })).toBe('You have already checked in today.');
  });

  it('joins validation errors with their field names', () => {
    const err = { error: { detail: [{ loc: ['body', 'mobile'], msg: 'String should match pattern' }] } };
    expect(errorMessage(err)).toBe('mobile: String should match pattern');
  });

  it('explains network failures', () => {
    expect(errorMessage({ status: 0 })).toContain('Cannot reach the server');
  });
});
