# Production operator runbook

Use one Compose project for one guild or a trusted guild cluster. SQLite is the
default; PostgreSQL setup and tested transfer/restore instructions are in
[DATABASES.md](DATABASES.md). Complete [READINESS.md](READINESS.md)'s live checks
before officers rely on a particular installation.

## Prepare Discord and the host

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
   Record its application/client ID. In OAuth2, add exactly
   `https://YOUR_HOST/auth/discord/callback/` as an allowed redirect. Store the
   client secret in the host's private `.env`, never in Git or browser settings.
2. Create/reset the bot token in the application's Bot settings. The bot uses default, non-privileged intents. Role checks use interaction
   membership data and REST requests; these slash-command workflows do not
   require privileged Server Members or Message Content intents.
3. Install the bot with scopes `bot` and `applications.commands`. Grant View
   Channels, Send Messages, Embed Links, Read Message History, Manage Channels
   (tickets) and Manage Roles (welcome selections). The onboarding screen supplies
   an invite link. Put its highest role above every welcome role it may grant;
   configure ticket staff roles and channel overwrites deliberately. Run the
   read-only diagnostics below before enabling delivery.
4. On the Ubuntu host, install Docker Engine and Compose, clone the repository,
   copy `.env.example` to `.env`, and restrict that file to the operator. Set
   `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, all three `DISCORD_CLIENT_*`/redirect
   values, `HTTPS=1`, and the bot token when enabling the bot. The OAuth variables
   are `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`.
5. Terminate TLS at your reverse proxy and route to loopback port 8765. Use
   `TRUST_PROXY=1` only when that proxy strips incoming forwarded headers and sets
   its own. Keep the application port inaccessible from the public network.
   Configure DNS/certificates and host firewall for the selected host.
   [SECURITY.md](SECURITY.md) covers HSTS, sessions, proxy trust and rotation.

## Start and onboard

```sh
docker compose config --quiet
docker compose up --build -d web
docker compose logs --tail=100 web
docker compose exec web python manage.py diagnostics
```

Startup validates settings, applies migrations and rotates the optional backend
administrator. Its new password appears in the private web logs; restrict access
to those logs. The `/admin/` account is for backend recovery, not member access.
Demo seeding and member password login stay disabled in production.

Open the HTTPS site and sign in with Discord. A server owner, administrator or
user with Manage Guild can select a verified server, name the BDO guild and set
its region. In Settings, configure owner/admin/member role IDs, channel
destinations, ticket staff/categories, welcome selections and schedules. A user
without a matching role does not automatically gain member access. Multiple BDO
guilds may share a Discord server; set each guild's roles separately and select
`guild_name` in ambiguous slash commands.

For staging, set `DISCORD_SYNC_GLOBAL=0` and `DISCORD_SYNC_GUILD=SERVER_ID`.
Use global sync for a production installation when ready; do not enable both.
Set `ENABLE_DISCORD_DELIVERY=1` only after reviewing destinations and permissions.

```sh
docker compose exec web python manage.py bot_diagnostics --guild GUILD_ID
docker compose --profile discord --profile jobs up -d
docker compose logs --tail=100 bot scheduler
```

`GUILD_ID` is OpenIQ's numeric database ID from the dashboard API, not the Discord
server ID. Settings reports local configuration, last capture acknowledgement,
process heartbeats and the delivery queue; ?configured? does not prove that an
external provider is reachable. `/healthz/` reports web liveness. `/readyz/`
checks database, migrations and storage; `REQUIRED_PROCESSES=bot,scheduler` also
checks their heartbeats. Keep that setting consistent with enabled profiles.

## Operate and recover

- **Backups:** prepare the operator-owned backup directory for container UID
  10001, enable the `backups` profile and perform the isolated restore drill in
  [BACKUPS.md](BACKUPS.md). Keep a protected off-host copy including the signing
  key. A successful scheduled heartbeat is not a substitute for a restore drill.
- **Capture/imports:** follow [CAPTURE_HANDOFF.md](CAPTURE_HANDOFF.md). Use
  `verify_imports` for synthetic compatibility, then validate current regional
  game samples. Pairing credentials expire and are scoped to one live session.
- **Upgrades:** follow [UPGRADES.md](UPGRADES.md): preflight, backup, stop all
  writers, build/migrate/start, verify and keep the previous image and data copy.
- **Recovery:** use the backend administrator only to inspect/fix authorized
  state. Moving a guild to another server requires the single-use adoption key
  and a fresh verified Discord owner/Administrator/Manage Guild claim; see
  [CONTRACTS.md](CONTRACTS.md). Never edit JSON or a live database as a routine
  substitute for the supported maintenance commands.
- **Data/privacy:** `maintain` previews operator changes before `--apply`.
  [PRIVACY.md](PRIVACY.md) describes member export/unlink/anonymization/deletion;
  `retention` previews age-based cleanup. Historical war scores stay anonymous
  when member identifiers are removed.
- **Delivery failures:** inspect logs and outbox state. Rate limits retry with
  backoff; an ambiguous remote creation remains pending for inspection. Resolve
  the remote outcome before retrying. Do not delete idempotency records merely
  to force another message. Discord and the local database cannot jointly offer
  an unconditional exactly-once transaction.

## Shutdown and installation acceptance

```sh
docker compose --profile discord --profile jobs --profile backups stop
# Or remove containers while preserving the named volume:
docker compose --profile discord --profile jobs --profile backups down
```

Do not add `--volumes` unless intentionally destroying the saved installation.
Rehearse shutdown, abrupt termination, restart and upgrade on the target Linux
host. Record staging command/button/role/ticket/reminder results, a real war and
import review, restore evidence, and officer/member acceptance in READINESS.md.
Include keyboard and spoken screen-reader workflow review. Keep failed or
unavailable checks open with their reason and next action.
