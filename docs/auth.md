# Authentication

The app uses server-side cookie sessions.

## Session cookies

- Cookie name: `kanban_session`
- Cookie contents: opaque random session token
- Cookie flags: `HttpOnly`, `SameSite=Lax`, `Path=/`
- `SESSION_COOKIE_SECURE` controls the `Secure` flag.

Local Docker development runs over plain HTTP, so `SESSION_COOKIE_SECURE` may be omitted or set to `false` locally.

Production must run over HTTPS and set:

```text
SESSION_COOKIE_SECURE=true
```

## Session storage

SQLite stores only `sha256(session_token)`, never the raw cookie token. The browser receives the raw opaque token; the server hashes incoming cookie tokens before lookup or deletion.

Sessions expire according to `SESSION_TTL_DAYS` (default `7`). Logout deletes the matching session row and clears the cookie with the same cookie settings used for login/register.

## Auth rate limiting

`/api/auth/login` and `/api/auth/register` use simple in-memory rate limiting by client IP and username. This is intended for the single-container MVP.

Environment knobs:

- `AUTH_RATE_LIMIT_ATTEMPTS` (default `10`)
- `AUTH_RATE_LIMIT_WINDOW_SECONDS` (default `300`)
