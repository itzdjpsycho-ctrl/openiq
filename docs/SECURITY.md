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
