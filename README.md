# OpenIQ

**OpenIQ is unapologetically developed entirely with AI, with minimal human oversight.**

An independent, local CritIQ feature prototype for Black Desert guilds. Django + SQLite power independent domain modules; the browser UI uses HTML/CSS/JavaScript. It has no affiliation with CritIQ.

**Status:** working local platform with fixtures, reviewed imports and optional external adapters. **Not a complete, verified replacement for CritIQ.** A calibrated TCP/PCAP decoder is implemented and tested with synthetic captures; its historical calibration is not verified against the current BDO patch. Discord/Twitch adapters require credentials and have not been exercised against live accounts. See [feature status](docs/FEATURES.md) for the precise boundaries.

## Run with Docker

```bash
cd /home/user/src/openiq
docker compose up --build -d
```

Open **http://127.0.0.1:8765/** and sign in with `demo` / `prototype-local-2026`. Compose initializes demo data only when missing. The `openiq-data` named volume persists the database and signing key across container replacement. Existing host demo data is not copied into the image or container.

```bash
# Inspect status and logs.
docker compose ps
docker compose logs --tail=100 web

# Enable the optional continuous scheduler (notifications remain previews).
docker compose --profile jobs up -d

# Stop containers while retaining data.
docker compose down
```

For Docker without Compose:

```bash
docker build -t openiq:local .
docker run -d --name openiq -p 127.0.0.1:8765:8000 \
  -v openiq-data:/data -e SEED_DEMO=1 openiq:local
```

The application runs as UID 10001, includes Tesseract and uses Gunicorn/WhiteNoise to serve the app and static assets. It does not require a host Python installation. `.dockerignore` excludes the host database, signing key, environment files, Git metadata, virtual environment and screenshots.

Copy `.env.example` to `.env` to customize the port and initial demo password. `SEED_DEMO=0` disables demo initialization. For an empty installation, run `docker compose exec web python manage.py createsuperuser`, grant that account normal guild access through New guild, then add other accounts as needed. `HTTPS=1` enables secure cookies and HTTPS redirects when deployed behind TLS; set `TRUST_PROXY=1` only for a trusted reverse proxy that controls forwarded headers.

The Docker container hosts the platform. The desktop/live-interface capture process remains on the game host; offline PCAP parsing can also run in the image. No privileged container or host-network mode is required for the dashboard.

## Run on Ubuntu Desktop

```bash
cd /home/user/src/openiq
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 127.0.0.1:8765 --noreload
```

Open **http://127.0.0.1:8765/**. Demo accounts:

| Username | Role | Default password |
|---|---|---|
| `demo` | Owner | `prototype-local-2026` |
| `officer` | Admin | `prototype-local-2026` |
| `member` | Member, linked to Juniper | `prototype-local-2026` |

Set `DEMO_PASSWORD` before the first seed to choose a different demo password. Seeding is idempotent and does not reset existing credentials. This is a localhost development server, not a production deployment. Use `createsuperuser` for Django administration if needed.

## Try the workflows

1. **Members:** add/edit a family, set class, add vacation/notes, toggle exception, or switch to the draggable group board.
2. **History:** record a war with editable participant rows; import `fixtures/scores.csv` through Review scores and finalize the review. Change exclusions and alliance sharing separately.
3. **Signups:** join a capacity-limited team; overflow is waitlisted. Withdraw or drag members between teams. Save presets, repeat an event, lock/archive it and preview its Discord card.
4. **Performance:** configure thresholds, create a lead, assign and resolve mentoring. Link an event to its recorded war for no-show reconciliation.
5. **Gear:** update gear and inspect history; deletion clears the current display without losing history. Add reviewed rival snapshots for guild rankings.
6. **Live War:** start a session, generate a synthetic fight, import `fixtures/combat.jsonl`, or paste `fixtures/ikusa.log` into Import IKUSA text log with the date/timezone. Save, replay, link a war and enable/revoke a public recap.
7. **Alliance:** as `demo`, invite Silver Meridian, switch guild and accept. Only explicitly shared wars contribute.
8. **Community:** open/reply/close tickets; apply/review recruitment; generate welcomes, reminders, summaries, rolls and the enhancement minigame. All notifications appear as local previews.
9. **Settings:** configure roles, channels, schedules, create ticket categories and application forms, run scheduled work, and inspect the audit trail.

Real OCR uses the system `tesseract` executable (`sudo apt install tesseract-ocr` if absent). Upload cropped names/stat panels in alternating pairs. Misaligned or ambiguous results require correction; they never silently finalize a war. Gear OCR recognizes labeled AP/AAP/DP text and always requires review.

## Module layout

Each module exposes `handle(guild, action, payload, role, user)` and uses shared transactional dispatch. Browser routes and Discord commands call the same service boundary.

- `guilds/modules/roster.py`: roster, groups, class changes, identity links, notes, vacations, merge.
- `wars.py`, `analytics.py`, `intelligence.py`: reviewed scores, war history, metrics, awards, character lookup records and opponent profiles.
- `events.py`, `coaching.py`, `gear.py`, `alliances.py`: independent guild domain workflows.
- `community.py`, `operations.py`, `adminops.py`: support/recruitment, utilities, jobs, settings and access.
- `integrations.py`, `logformat.py`, `guilds/capture.py`: OCR, roster HTML, Twitch and event-file adapters.
- `commands.py`, `discord_auth.py`, `delivery.py`: local command routing, optional OAuth and explicit notification delivery.

Records have a relational guild/kind/key envelope, unique constraints and module-owned JSON payloads. Mutations acquire the database writer lock before reading mutable state and audit successful actions in the same transaction. This favors a small extensible prototype; a larger deployment should use typed relational domain models, schema-versioned payloads and PostgreSQL.

## Optional integrations and tools

No Discord messages have been sent. No bot has been connected.

```bash
# All 53 documented commands are constructed without a network connection.
.venv/bin/python manage.py runbot --check

# Exercise commands locally.
.venv/bin/python manage.py local_command guildstats --guild 1 --user demo
.venv/bin/python manage.py local_command 'reminder list' --guild 1 --user member

# Process scheduled jobs once; output remains in the preview queue.
.venv/bin/python manage.py tick

# Tail a normalized event log into an existing live session.
.venv/bin/python manage.py capture fixtures/combat.jsonl --session SESSION_ID --once

# Optional desktop file-capture companion (requires tkinter).
.venv/bin/python scripts/capture_desktop.py
```

Discord OAuth needs `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, and `DISCORD_REDIRECT_URI` (default `http://127.0.0.1:8765/auth/discord/callback/`). Configure guild `server_id` and role IDs. User OAuth requests profile, guild-list and own guild-membership read scopes. Role refresh fails closed. Local accounts are independent of Discord.

The optional bot uses `DISCORD_BOT_TOKEN` and requires `ENABLE_DISCORD_DELIVERY=1` before it will connect. `runbot --sync` registers the command tree. Its prototype slash interface accepts an `arguments` JSON object and optional `guild_name`; the dashboard offers the friendlier forms. `deliver ID` only previews an outbox item; `deliver ID --send` also requires delivery enablement and a numeric target channel. This code has not been live-tested. Do not enable it until you intend to connect/send.

Twitch uses `TWITCH_CLIENT_ID` and `TWITCH_ACCESS_TOKEN`; without them the demo directory is explicitly labeled as fixture data.

## Verification

```bash
.venv/bin/python manage.py test
.venv/bin/python manage.py check
.venv/bin/python manage.py runbot --check
.venv/bin/python scripts/verify_ocr.py
.venv/bin/python scripts/verify_packets.py
node --check static/app.js
```

Browser checks use optional `playwright` (`pip install -r requirements-dev.txt`, then `playwright install chromium`). With the server running, execute `scripts/browser_smoke.py`. The local test run used `PLAYWRIGHT_BROWSERS_PATH=/tmp/critiq-browsers`. Screenshots are in `docs/dashboard.png` and `docs/mobile.png`.

## Configuration and data

SQLite database: `db.sqlite3`; generated signing key: `.secret-key`. Both are excluded from Git. No credentials belong in source control. Back up the database while the application is stopped. The server uses `DEBUG=1` by default for local development; production configuration, deployment hardening, integration load testing, retention policy and recovery drills remain separate work.

Research and independent behavior decisions: [investigation](docs/RESEARCH.md), [feature matrix](docs/FEATURES.md), [data contract](docs/CONTRACTS.md).

## Calibrated packet capture

The decoder is independently implemented from the public IKUSA field-calibration contract. The bundled offsets are **historical (2023-04-19)** and use a documentation-only server network. They are suitable for the synthetic fixture, not an assertion of current game compatibility.

```bash
.venv/bin/python manage.py packet_capture \
  --calibration fixtures/calibration-historical.json \
  --pcap fixtures/combat-synthetic.pcap
```

For an actual game session, supply a verified current calibration and explicit server network/interface selection. `packet_capture --interfaces INTERFACE --calibration FILE --session SESSION_ID` provides live capture through Scapy; Windows uses Npcap, while Linux requires capture permission. Live traffic has not been captured during development.

The local capture-release prototype can build and checksum-verify portable source packages:

```bash
.venv/bin/python manage.py release_capture --output /tmp/openiq-release
.venv/bin/python manage.py update_capture /tmp/openiq-release/manifest.json /tmp/openiq-capture-install --install
```

These are local source releases, not a published Windows executable distribution. The installer validates archive paths and checksums and replaces the installed tree atomically. A remote release service would additionally need signed manifests and platform packaging.

Optional AI text generation uses a local Ollama server when `OLLAMA_MODEL` is set, with `OLLAMA_URL` defaulting to `http://127.0.0.1:11434`. Without a model it clearly identifies its deterministic offline fallback.

## Test coverage

The Python application and management commands currently have **100% statement and branch coverage** across **116 tests**. Coverage excludes test files and generated migrations. The C tracer is selected explicitly because Python 3.14's default monitoring tracer reported false missing branches for compact exception paths.

```bash
python -m pip install -r requirements-dev.txt
python -m coverage run manage.py test
python -m coverage report
python -m coverage html
python scripts/browser_smoke.py
```

The coverage report fails below 100%. Browser smoke tests separately exercise all 12 dashboard sections and representative data-entry workflows against the running container. This is not a claim of 100% JavaScript coverage or live-service parity: Discord/Twitch/Ollama calls are mocked, and packet tests use synthetic captures.

To build and inspect a portable capture source release locally:

```bash
python manage.py release_capture --release-version 0.1.0 --output /tmp/openiq-release
python manage.py update_capture /tmp/openiq-release/manifest.json /tmp/openiq-capture --install
```


## Discord ticket channels (optional)

The Community tab can preview a private ticket-channel plan. Configure `tickets.bot_user_id`, `tickets.staff_role`, and optional `tickets.category_id` through the settings API. The ticket author must have a roster entry linked to both their local account and Discord ID. Ticket categories can override the staff role.

```bash
python manage.py ticket_channel TICKET_ID --guild GUILD_ID --user demo
```

The command previews by default. Adding `--send` requires `ENABLE_DISCORD_DELIVERY=1` and `DISCORD_BOT_TOKEN`; it creates or updates a private channel, synchronizes transcript messages, and makes closed tickets read-only for their author. The bot needs the corresponding Discord channel/message permissions. Remote behavior is tested with mocks only. HTTP success followed by a local database failure can still require manual reconciliation.
