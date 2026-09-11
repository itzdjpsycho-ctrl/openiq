# Guild readiness checklist

This is the shared work queue for making OpenIQ safe and practical for a real,
self-hosted Black Desert guild. Contributors should take one unchecked item,
avoid combining unrelated items, and push a focused commit when its validation
passes. Mark the item complete in that same commit. Items within a numbered
group are ordered; separate groups can usually be worked on in parallel.

The target deployment is one guild or a small, trusted guild cluster using one
Compose project and its persistent data volume. Live BDO, Discord, and Twitch
verification and the choice of a public host remain external launch checks.

## 1. Identity and initial setup

- [x] **AUTH-01 — Rotating backend recovery administrator.** Compose enables one
  Django admin account, rotates its generated password on every web start, prints
  it to the web log, and can disable the account through configuration.
- [x] **AUTH-02 — Discord-only member login.** Route the normal login entry point
  directly to Discord OAuth in production. Keep password login available only
  behind an explicit development setting; `/admin/` remains available to the
  rotating backend administrator.
- [x] **AUTH-03 — Verified Discord guild onboarding.** Persist the OAuth guild
  claims in the server-side session and allow creation only for a Discord server
  where the user is owner, administrator, or has Manage Guild.
- [x] **AUTH-04 — Secure OAuth lifecycle.** Handle denied authorization, missing
  refresh tokens, account reuse, logout/session cleanup, and safe refresh failure
  messages without exposing credentials.
- [ ] **AUTH-05 — First-run setup screen (reserved for UX contributor).** Let an authorized Discord owner select
  a server, set region and guild name, configure the bot invite, and see which
  setup steps remain.
- [ ] **AUTH-06 — Guild recovery constraints.** Require verified Discord authority
  when applying an adoption key and audit both its issuer and redeemer.

## 2. Discord bot

- [x] **BOT-01 — Compose bot service and secrets.** Add a long-running bot service
  with shared persistent data, health/restart behavior, Discord environment
  wiring, and an explicit switch controlling outbound delivery.
- [ ] **BOT-02 — Development-guild command sync.** Support fast guild-scoped sync
  as well as global sync, document both modes, and report sync failures clearly.
- [ ] **BOT-03 — Native slash-command options.** Replace the generic JSON argument
  box with typed Discord inputs, choices, autocomplete where useful, and command
  descriptions generated from the command catalog.
- [ ] **BOT-04 — Discord-safe responses.** Present domain results as readable
  messages or files, paginate output beyond Discord limits, and map validation
  and permission failures to stable user-facing responses.
- [ ] **BOT-05 — Persistent interactive components.** Restore signup and welcome
  views after bot restart and reject stale, malformed, cross-guild, or replayed
  component identifiers.
- [ ] **BOT-06 — Event message lifecycle.** Create and update signup cards,
  capacities, waitlists, locks, archive state, recurrence, and missing-response
  reminders through Discord.
- [ ] **BOT-07 — Ticket lifecycle.** Create private channels, synchronize replies,
  close/reopen tickets, retain transcripts, and reconcile partial remote failures.
- [ ] **BOT-08 — Welcome and role lifecycle.** Post welcome cards, grant only
  configured roles below the bot role, remove obsolete selections where desired,
  and explain Discord hierarchy/permission failures.
- [ ] **BOT-09 — Scheduler delivery.** Deliver due reminders exactly once with
  retry/backoff and restart-safe idempotency instead of leaving scheduled work as
  previews.
- [ ] **BOT-10 — Bot diagnostics.** Add an operator command/check that verifies
  token validity, guild installation, intents, channel access, role hierarchy,
  and command registration without sending messages.

## 3. War management end to end

- [x] **WAR-01 — Explicit score review.** OCR/CSV imports require correction of
  unmatched or ambiguous participants before finalization.
- [x] **WAR-02 — War metadata and relationships.** Recorded wars support opponent,
  result, score, event links, live-session links, relinking, and safe deletion.
- [x] **WAR-03 — Full browser lifecycle.** Browser smoke coverage exercises roster,
  event, OCR review, correction, finalization, live linking, and debrief.
- [x] **WAR-04 — Replay-scoped debrief.** Live-war summaries can isolate replay
  segments and remain connected to the finalized war.
- [ ] **WAR-05 — Operational war checklist.** Provide a single pre-war/during-war/
  post-war view showing event, signup state, capture state, review state, finalized
  result, outstanding corrections, and Discord delivery state.
- [ ] **WAR-06 — Capture handoff durability.** Authenticate capture submissions,
  resume after disconnect, deduplicate retries, expose last-seen state, and retain
  a bounded diagnostic log.
- [ ] **WAR-07 — Import compatibility report.** Validate all supported synthetic
  CSV/OCR/IKUSA/JSONL inputs from one command and produce a clear operator report.
- [ ] **WAR-08 — Export and correction history.** Export a complete war package and
  retain an audit trail when finalized participant scores or metadata are edited.
- [ ] **WAR-09 — Retention controls.** Configure retention for raw captures, OCR
  uploads, public recaps, and derived summaries without deleting finalized wars.

## 4. Self-hosted operations and data safety

- [ ] **OPS-01 — Production environment contract.** Supply every required and
  optional environment variable through Compose, validate unsafe/missing values
  at startup, disable demo data by default, and provide a deployment-oriented
  example file without secrets.
- [ ] **OPS-02 — Consistent backup command.** Create timestamped SQLite backups
  using SQLite's online backup API, include the signing key and a manifest, and
  support a retention count without stopping the services.
- [ ] **OPS-03 — Verified restore command.** Validate a backup manifest, refuse an
  accidental overwrite unless explicitly requested, restore atomically, and run
  Django checks before reporting success.
- [ ] **OPS-04 — Scheduled backup service.** Add an optional Compose service that
  writes backups to a bind-mounted operator directory and document a restore
  drill.
- [ ] **OPS-05 — Readiness and diagnostics.** Separate liveness from readiness and
  report database access, migrations, writable storage, bot/scheduler heartbeat,
  and version without revealing secrets.
- [ ] **OPS-06 — Graceful process behavior.** Confirm signal handling, shutdown,
  startup ordering, SQLite contention handling, and recovery after abrupt process
  termination for web, scheduler, and bot.
- [ ] **OPS-07 — Upgrade workflow.** Document pull/build/migrate/backup/rollback
  steps and add a preflight command that checks the current data before upgrade.
- [ ] **OPS-08 — Structured maintenance tools.** Add supported commands for user
  removal, Discord relinking, guild export, guild deletion, expired-token cleanup,
  and audit/outbox retention.

## 5. Security and privacy

- [ ] **SEC-01 — Production security settings.** Validate allowed hosts, trusted
  origins, TLS/proxy settings, secure cookies, HSTS options, and production Django
  deployment checks.
- [ ] **SEC-02 — Request and login abuse controls.** Rate-limit OAuth starts,
  callbacks, recovery attempts, OCR uploads, and mutation endpoints with useful
  retry responses.
- [ ] **SEC-03 — Session and secret hygiene.** Define session lifetime, rotate
  sessions at login, clear Discord tokens at logout, redact credentials from
  errors/logs, and document secret rotation.
- [ ] **SEC-04 — Upload hardening.** Enforce content signatures, decoded dimensions,
  processing timeouts, temporary-file cleanup, and aggregate request limits for
  OCR inputs.
- [ ] **SEC-05 — Permission regression matrix.** Verify owner/admin/member and
  unauthenticated behavior for every HTTP action, Discord command, component, and
  private/public record type.
- [ ] **SEC-06 — Privacy controls.** Document stored Discord/game data and provide
  guild-member export, unlink, anonymization, and deletion workflows.

## 6. Product completion and operator experience

- [ ] **UX-01 — Complete settings forms (reserved for UX contributor).** Replace remaining raw nested settings
  edits with validated forms for roles, channels, tickets, recruitment, schedules,
  capture, retention, and integrations.
  - [x] **UX-01a: Editable schedule forms.** Show weekly/sync summaries, load
    existing settings, use weekday names, validate hour/timezone input, and
    preserve unrelated settings. Browser regression verifies save and recovery.
- [ ] **UX-02 — Setup and integration status (reserved for UX contributor).** Show Discord bot, OAuth, Twitch,
  capture, scheduler, backup, and delivery status with actionable diagnostics.
- [ ] **UX-03 — Empty/error/loading states (reserved for UX contributor).** Make every dashboard section usable
  with no demo data and preserve entered values after validation failures.
  - [x] **UX-03a: Shared table and form feedback.** Explain empty tables, show
    saving state, prevent duplicate submission/dismissal while pending, retain
    entered values on failure, and focus the error for correction.
  - [ ] **UX-03b: Section-specific states.** Verify every dashboard section with
    no demo data and complete its empty, error, and loading states.
- [ ] **UX-04 — Accessibility and mobile pass (reserved for UX contributor).** Verify keyboard operation, focus,
  labels, contrast, reduced motion, narrow layouts, and screen-reader announcements
  for dynamic workflows.
  - [x] **UX-04a: Shared accessibility and mobile improvements.** Name guild/action
    selectors and dialogs, expose the current section, retain navigation focus,
    add visible focus outlines and reduced-motion styles, and constrain mobile
    toast sizing. Verify empty history at 390px, keyboard navigation, and
    failed-save correction with the opt-in Edge browser regression test:
    `OPENIQ_BROWSER_TEST=1 python manage.py test guilds.test_ux_browser`.
  - [ ] **UX-04b: Full accessibility and mobile verification.** Complete the
    section-by-section keyboard, labels, contrast, narrow-layout, and
    screen-reader checks for dynamic workflows.
- [ ] **UX-05 — Guild-cluster boundaries (reserved for UX contributor).** Test two BDO guilds on one Discord
  server and allied guilds in separate servers without data or permission leakage.
- [ ] **DOC-01 — Production runbook.** Document Discord application creation, OAuth
  redirect, bot install permissions, first-run setup, backups, upgrade, recovery,
  diagnostics, and shutdown.
- [ ] **DOC-02 — Remove prototype contradictions.** Keep README, contracts, feature
  matrix, test totals, Compose defaults, and UI wording aligned with actual
  production behavior.
- [ ] **QA-01 — Offline release gate.** Run Django checks, full statement/branch
  coverage, bot registry checks, OCR fixtures, packet fixtures, JavaScript syntax,
  Compose config validation, and the browser lifecycle from one command.

## External launch checks

These checks cannot be completed from synthetic data or without the chosen host.
They still block calling a specific installation live-ready.

- [ ] **LIVE-01 — Discord staging guild.** Exercise OAuth, bot install/sync,
  commands, buttons, roles, tickets, reminders, restarts, and permission failures.
- [ ] **LIVE-02 — Current BDO data.** Calibrate and verify capture against the
  current patch and test OCR/roster imports with representative regional data.
- [ ] **LIVE-03 — Hosting rehearsal.** Verify TLS, reverse proxy, DNS, firewall,
  persistent storage, scheduled backups, restore, monitoring, and upgrades on the
  selected Ubuntu host.
- [ ] **LIVE-04 — Guild acceptance.** Run one full event and war with officers and
  members, review privacy/retention policy, and record sign-off on the workflow.
