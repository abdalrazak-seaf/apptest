import { errorCode } from './errors';

describe('errorCode', () => {
  it('reads the API error code', () => {
    expect(errorCode({ code: 'otp_invalid' })).toBe('otp_invalid');
  });

  it('falls back to a generic code for anything else', () => {
    expect(errorCode(undefined)).toBe('generic');
    expect(errorCode({})).toBe('generic');
    expect(errorCode('boom')).toBe('generic');
    expect(errorCode({ code: 42 })).toBe('generic');
  });
});
