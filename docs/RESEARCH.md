# Guild-management workflow research

Research date: 2026-09-11. Target: https://critiq.one, unrelated to the code-review products with the same name. This is an independent implementation; no upstream application code or branding assets are incorporated.

## Evidence

- [Public documentation](https://critiq.one/docs/index.html): workflows, permission matrix, command catalog, operational rules.
- [Product page](https://critiq.one/): public interactive demonstrations and advertised capabilities.
- Publicly served landing page inspected to locate documentation. Search-index pricing differs from the currently served landing page. Pricing is not a reliable basis for feature entitlements.

## Product boundaries

Guild operations span roster management, reviewed screenshot imports, war history, analytics, private performance coaching, signups, gear, alliances, streaming, and Discord utilities. The companion CritCap application captures Windows network traffic. Neither packet layouts nor a reproducible decoding algorithm are published in the documentation. A log-import alternative exists. Full capture parity requires representative data and protocol investigation; inventing a packet parser would not establish compatibility.

## Behavioral specification and acceptance inventory

This inventory translates the published behavior into independent acceptance cases. Implementation status must be recorded separately; inclusion here does not mean implemented.

| Area | Acceptance cases |
|---|---|
| Identity | Discord sign-in; guild selector; owner/admin/member checks on server; role refresh; bootstrap administrator; orphan recovery/adoption |
| Setup | Select BDO region/guild; fetch official roster; review before registration; resync adds arrivals, inactivates departures, retains historical results; multiple BDO guilds per Discord server |
| Members | Search family/character, class/group/unlinked filters, sorting, cards and group board; class/spec changes with optional historical backfill; exceptions, dated vacations, join grace; notes; merge family renames; inactive records |
| Scores | Up to five name/stat image pairs; row correspondence; OCR and fuzzy suggestions; explicit review; correct unmatched names; atomic finalization; no duplicate finalization |
| Wars | Date, node/siege, cap, outcome; participant edits/add/remove; notes; exclusions; opt-in alliance sharing; linked live session |
| Metrics | Kills/deaths aggregated before division; zero-death convention made explicit; exclusions do not erase attendance; eligibility honors join date and vacation; last-seven eligible-war attendance; filters shared by global and member statistics |
| Analytics | Timeline, attendance calendar, class/spec composition and performance, comparison, priority trends, retention; awards and improved/consistent-player definitions documented |
| Personal | Linked member dossier, trends, attendance, recent wars, matchup history, awards, weekly digest |
| Coaching | Officer-only thresholds/windows for KDR, attendance, no-shows; minimum samples, grace, cooldown; lead capacity; active/resolved assignments and notes |
| Events | Timezone-aware dates, recurrence, templates/presets, teams/subteams, capacities, waitlist per team, signup/withdraw, lock/archive; Discord cards and edits; class/gear on signup; ally read-only access |
| Alliances | Two to four guilds; creator accepted; pending invitations; unanimous activation; decline disbands and cancels pending invites; no writes to allied data; opted-in wars only; exception-inclusive/exclusive totals |
| Gear | AP/AAP/DP from reviewed equipment/detail images; explicit GS formula; immutable history; current-entry removal preserves history; linked-member ownership; rankings; missing-gear reminders and channel restrictions |
| Live | Input events with stable IDs; incremental feed, timeline, opponent guild/player/class statistics; session start/stop/save/replay; war link; public recap opt-in; enemy profiles; character/family switch; reconnect/deduplication |
| Capture | CritCap Windows/Npcap equivalent; local decoding, adapter/VPN handling, local bridge, update mechanism; authentic IKUSA format; class-resolution cache, paced lookups, backoff |
| Streams | Twitch account linking, live member and BDO directory views, categories/partners, refresh and API backoff |
| Administration | Channels/roles/command overrides; scheduled sync, summaries, milestones; welcomes/role buttons, tickets, recruitment/review, reminders; guild deletion and stats purge with explicit confirmation |
| Utilities | Help, roll/challenge, enhancement game, optional AI roast/message summary, slash registration and sync status |

## Command compatibility inventory

Setup: `setup`, `adopt`, `sync roster`, `cancel`.
War/member operations: `warscores`, `warscores-beta`, `exception`, `removeexception`, `vacation`, `guildstats`, `warlog`, `trends`, `weeklysummary`, `configweeklysummary`, `catchup-summaries`, `purgestats`.
Gear: `gearupdate`, `gear`, `gearlist`, `deletegear`, `gearping`, `rankings`.
Identity: `link`, `unlink`, `whois`, `unlinked`, `link-twitch`, `unlink-twitch`, `twitch-links`, `setclass`, `class`, `reset-class`.
Events/coaching: `unsigned ping`, `unsigned message`, `performance-flags list`, `performance-flags notify`.
Configuration: `config`, `setbotchannel`, `setsyncnotifications`, `seteventlog`, `retention`, `sync-status`, `reload-commands`, `redeploy-slash-commands`.
Utilities: `help`, `welcome`, `reminder set/list/cancel`, `roll`, `roast`, `tap`, `notreadingallthat`.

## Open questions and verification requirements

1. Private dashboard behavior, exact award formulas, OCR crop geometry and ambiguous name handling need real examples. Public docs are a baseline, not proof of identical results.
2. CritCap protocol and authentic IKUSA logs need samples; Ubuntu can host the platform, while a Windows game capture adapter is a separate compatibility target.
3. Discord application credentials and a test guild are required for live OAuth/bot tests. Twitch credentials are required for live directory tests. Do not send notifications during development without the user's explicit authorization.
4. BDO roster page format varies by region. Sync must not mark everyone inactive on an empty/error parse.
5. Recruitment, tickets, minigame rules and AI behavior are described only at a high level. Record independent design decisions rather than claiming discovered internals.

## Architecture decision

Django 5.2 provides database migrations, authentication, sessions, CSRF protection and relational transactions. SQLite supports a local installation; a production installation should use PostgreSQL when concurrent writes require it. Server-rendered accessible pages plus JavaScript provide the dashboard without a frontend build dependency. Discord is a separate process using the same domain services. OCR is local Tesseract with review before persistence. External adapters are separate from calculations so recorded fixtures can validate domain behavior offline.

The installed Django release supports the host's Python 3.14; see [Django 5.2 release notes](https://docs.djangoproject.com/en/5.2/releases/5.2/).


## Later packet-format finding

A deeper search located [sch-28/ikusa_logger](https://github.com/sch-28/ikusa_logger), including its public field-calibration format. The checked-in calibration reports patch **2023-04-19**. OpenIQ now has an independently written configurable decoder with per-flow TCP assembly, offline PCAP and explicit-interface capture adapters. Tests generate packets using the historical field locations. This establishes prototype decoding behavior, not compatibility with the current BDO patch. Public field offsets and the text-log contract were used as facts; no upstream source implementation is distributed in this repository.

### Private ticket channel adapter

OpenIQ independently builds private-channel permission overwrites, transcript updates, and read-only closure using the [official Discord guild-channel API](https://docs.discord.com/developers/resources/guild#create-guild-channel). The adapter is opt-in and tested with mocked responses; no live server writes have been performed.

Welcome role buttons use the [official Add Guild Member Role API](https://docs.discord.com/developers/resources/guild#add-guild-member-role) through an explicit delivery gate. Local selections and mocked role-grant requests are independently tested.
