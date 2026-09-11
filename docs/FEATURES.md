# Prototype feature status

This is an implementation audit, not a claim of CritIQ parity. The [research inventory](RESEARCH.md) remains the target. “Working” below means local behavior is implemented; “adapter” means code exists but the real remote service was not exercised. “Simulated” is an explicit test input, not real game data.

| Feature family | Working prototype | Remaining parity work |
|---|---|---|
| Setup / identity | Local guild onboarding, owner/admin/member accounts, guild picker, reviewed roster sync, Discord-family links; OAuth adapter, role refresh, one-use adoption key | Live Discord setup wizard; test regional BDO roster pages. Local recovery supports expiring, single-use adoption keys |
| Roster | Add/edit/inactivate, search, class filter, stat sorting, draggable groups, class/spec and historical backfill, private notes, exceptions, dated vacations, merge | More filter/sort combinations and card animation; merges reconcile wars, gear, coaching and event signups |
| Score ingestion | CSV review, fuzzy suggestions, paired-image Tesseract OCR, alignment validation, manual corrections, atomic finalize, repeat-finalize prevention | Real BDO screenshot corpus, language/crop presets and extraction accuracy benchmarking |
| War history | Create/edit/delete, dates/types/results/caps, participant add/remove via form, class snapshot, K/D exclusion and alliance sharing, notes, live link | Polished per-war awards sidebar; the participant editor includes class and exclusion controls |
| Analytics | Aggregate K/D, eligible-war attendance, timeline, class composition/performance, normalized comparison radar, heatmap, retention, awards | Exact undocumented CritIQ award formulas, physics bubble animation, all chart drill-down interactions |
| Personal statistics | Linked-member dossier, recent wars, trends, attendance, opponent matchup totals, trophy case | Exact original assessment and digest rules; local weekly roundup and trend assessment are implemented |
| Coaching | Private flags, KDR war window, attendance/miss/no-show thresholds, grace/vacation exemptions, leads/capacity, assignments, resolution cooldown | Live notification role ping formatting; independent all/wars/days/previous-month windows and lead notification previews are implemented |
| Signups | Create/edit, team capacities and per-team waitlists, drag/drop, withdrawals and promotion, lock/archive, presets, timezone-aware recurrence, event-card/missing-response previews; archival waitlist pity points | Live Discord button verification and exact original subteam layout. Native button payloads, grouped teams, custom card images/accent, automatic recurrence and protected ally links are implemented |
| Alliances | Two to four guild invitations, unanimous activation, rejection/cancellation, leave, read-only shared-war totals | Invite notification and rejection acknowledgment UI; allied roster/history/events and exception-inclusive totals are implemented |
| Gear | Reviewed labeled-image extraction, AP/AAP/DP, history, delete-current, local member ranking and manually reviewed rival guild snapshots | Live rival tracking and daily refresh, game-screen-specific crop profiles |
| Live analysis | Sessions, ingest, duplicate IDs, chronological feed, one-minute chart, replay slider, stop/save, war link, public recap/revoke, enemy profiles, manual character/family resolution, visible backoff fixture | Automatic BDO class discovery queue, true push transport, per-guild zoom controls, full debrief layout |
| Capture / IKUSA | Browser JSON event-file import, incremental JSONL tail with rotation/partial-line handling, desktop file-adapter companion, independent IKUSA text parser, midnight rollover | Configurable native TCP/PCAP decoding and source-release checksum updater are implemented. Historical public calibration is tested with synthetic packets; current-patch calibration, real logs, Windows Npcap installation and packaged executable updates remain unverified or incomplete |
| Streams | Twitch linking, fixture directory, viewer/category/partner display, category filter, live API refresh adapter | Partner lookup, embedded player/carousel, automatic authenticated refresh/backoff testing |
| Scheduled operations | Timezone-aware weekly/sync schedule, idempotent run records, lookback catchup, reminder processing and milestone previews | Continuous scheduler and verified regional roster-source adapters are implemented, including Docker jobs profile. Live scheduled source validation remains outstanding |
| Community | Tickets/replies/close, ticket categories, application forms/submit/review, welcome message and local role assignment, reminders | Native Discord ticket channels, real role buttons, more granular applicant ownership/views and notification routing |
| Fun / AI | Roll, two-player challenge acceptance, persistent enhancement minigame; optional Ollama summary/roast adapter with explicit offline fallback | Live model testing and exact original minigame rules |
| Configuration | Local access controls, channels, schedule forms, generic settings API for roles/overrides/recruitment/tickets, audit history, confirmed stats purge, adoption-key flow | Full settings UI for each nested value and live permission override semantics; confirmed guild disband is implemented |
| Discord | 53 command names build locally; local command dispatcher; optional gateway/OAuth/send-update adapters; no external messages sent | End-to-end Discord tests, native command argument forms and interactive cards, complete command-by-command behavioral parity |

## Interpretation

All major product areas have a usable local workflow or a clearly labeled adapter/simulator. This is **not yet a working prototype of every individual documented behavior**: the rightmost column is remaining work, not silently accepted scope reduction. Current-patch game capture and private dashboard behavior cannot be verified from the currently available data.

## Validation evidence

- Django domain/API tests exercise transactions, permissions, attendance, waitlists, alliances, reminders, OCR parsing, OAuth-state rejection, role mapping and event-file handling.
- Chromium smoke checks cover all 12 dashboard sections, member creation/search, war entry, event creation, gear entry, browser IKUSA parsing and responsive layout with no JavaScript errors.
- Real Tesseract invocation recognizes the generated two-panel fixture. A narrow/ambiguous numeric row is rejected by the parser.
- `runbot --check` constructs all 53 commands without opening a Discord connection.
- No live Discord, Twitch, BDO account, real packet capture or real war screenshot validation has been performed.

## Test coverage

Run `python -m coverage run manage.py test`, then `python -m coverage report` or `python -m coverage html`. Coverage excludes test code and generated migrations; uncovered application branches remain visible. Full coverage is an active goal, not a claim. Remote API tests use mocks; synthetic packet and browser tests do not establish upstream feature parity.

The latest baseline is 112 passing Python tests with 100% statement and branch coverage for `guilds` and `config`, including management commands. `.coveragerc` enforces that threshold. This does not include JavaScript coverage, desktop Tk UI coverage, or live external-service validation. Recruitment now preserves structured questions/answers and exposes each applicant's own submissions; closed tickets reject further replies.
