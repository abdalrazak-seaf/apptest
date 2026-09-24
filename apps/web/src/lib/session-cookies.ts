/** Cookie names shared by the route handlers and the server components. */
export const ACCESS_TOKEN_COOKIE = 'thiqa_at';
export const REFRESH_TOKEN_COOKIE = 'thiqa_rt';

/** Tokens are httpOnly so page scripts can never read them. */
export const COOKIE_OPTIONS = {
  httpOnly: true,
  sameSite: 'lax',
  path: '/',
  secure: process.env.NODE_ENV === 'production',
} as const;
