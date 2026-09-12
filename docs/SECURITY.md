# Deployment security

Production startup requires `DEBUG=0`, `HTTPS=1`, explicit `ALLOWED_HOSTS`,
Discord OAuth credentials and an HTTPS callback on an allowed host. Set
`CSRF_TRUSTED_ORIGINS` to the exact HTTPS origins used by the guild. Keep the
Gunicorn port private behind a TLS reverse proxy. Enable `TRUST_PROXY=1` only
when that proxy removes untrusted forwarded headers and sets its own protocol.

Secure session/CSRF cookies and HTTPS redirects follow `HTTPS`. Liveness and
readiness paths are exempt from redirects for internal probes. `HSTS_SECONDS`
defaults to one hour in Compose. Increase it after validating TLS. Enable
`HSTS_INCLUDE_SUBDOMAINS` or `HSTS_PRELOAD` only when every affected hostname can
maintain HTTPS. These settings can make browsers refuse HTTP long after a deploy.

Run `python manage.py validate_environment` before deployment and
`python manage.py check --deploy --fail-level WARNING` against the final production
configuration. Deliberately omitted HSTS subdomain/preload policies may produce
deployment warnings that the operator must review. Local development explicitly
uses `DEBUG=1`, `HTTPS=0` and `ALLOW_LOCAL_LOGIN=1`; demo data is opt-in.

Reference: [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

Request budgets use the shared database and expire every minute. Defaults are
20 OAuth/login requests, 5 recovery requests, 10 OCR uploads and 240 mutations
per authenticated user or anonymous IP. Configure `RATE_LIMIT_OAUTH`,
`RATE_LIMIT_RECOVERY`, `RATE_LIMIT_OCR`, and `RATE_LIMIT_MUTATION` for guild load.
Blocked requests return HTTP 429 and Retry-After. Only a trusted proxy configuration
permits the final X-Forwarded-For address to identify the client; configure that
proxy to overwrite/append the real client address. Untrusted forwarding headers
are ignored. Production startup rejects disabling request protection.

Sessions expire eight hours after login by default (`SESSION_MAX_AGE`, 60 seconds
to seven days). OAuth refresh does not extend this absolute deadline. Django
rotates session keys at login, and OpenIQ clears any previous Discord state;
logout flushes the session and its tokens. Gunicorn access logs omit query strings,
and application logs redact configured secrets and OAuth callback codes.

To rotate the application signing key, stop all services, preserve a private
backup and replace the persistent `.secret-key` with a newly generated random key
(or change the shared `SECRET_KEY` environment value). Restart all services with
the same value. Existing sessions, signed Discord cards and protected links become
invalid; sign in again and republish cards. Revoke capture credentials separately
with `pair_capture --revoke`; they are independently scoped and hashed. Rotate
Discord/Twitch credentials in their provider consoles and update `.env` without
putting values in shell history, Git or chat. Restrict old backups because they
retain earlier signing keys and data.
