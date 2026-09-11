# Prototype feature status

This is an implementation audit, not a claim of CritIQ parity. The [research inventory](RESEARCH.md) remains the target. “Working” below means local behavior is implemented; “adapter” means code exists but the real remote service was not exercised. “Simulated” is an explicit test input, not real game data.

| Feature family | Working prototype | Remaining parity work |
|---|---|---|
| Setup / identity | Local guild onboarding, owner/admin/member accounts, guild picker, reviewed roster sync, Discord-family links; OAuth adapter, role refresh, one-use adoption key | Live Discord setup wizard, independent recovery for an orphaned owner; test regional BDO roster pages |
| Roster | Add/edit/inactivate, search, class filter, stat sorting, draggable groups, class/spec and historical backfill, private notes, exceptions, dated vacations, merge | More filter/sort combinations, card animation; merges currently reconcile wars/gear/coaching but not every event identity reference |
| Score ingestion | CSV review, fuzzy suggestions, paired-image Tesseract OCR, alignment validation, manual corrections, atomic finalize, repeat-finalize prevention | Real BDO screenshot corpus, language/crop presets and extraction accuracy benchmarking |
| War history | Create/edit/delete, dates/types/results/caps, participant add/remove via form, class snapshot, K/D exclusion and alliance sharing, notes, live link | Dedicated per-row exclusion control and polished per-war awards sidebar; API supports row exclusions |
| Analytics | Aggregate K/D, eligible-war attendance, timeline, class composition/performance, normalized comparison radar, heatmap, retention, awards | Exact undocumented CritIQ award formulas, physics bubble animation, all chart drill-down interactions |
| Personal statistics | Linked-member dossier, recent wars, trends, attendance, opponent matchup totals, trophy case | Dedicated assessment text and personal weekly digest presentation |
| Coaching | Private flags, KDR war window, attendance/miss/no-show thresholds, grace/vacation exemptions, leads/capacity, assignments, resolution cooldown | Every independent days/month/window combination; notification role ping formatting |
| Signups | Create/edit, team capacities and per-team waitlists, drag/drop, withdrawals and promotion, lock/archive, presets, timezone-aware recurrence, event-card/missing-response previews; archival waitlist pity points | Native Discord signup buttons, nested visual subteams, custom card images, automatic recurring event creation, ally event-sharing links |
| Alliances | Two to four guild invitations, unanimous activation, rejection/cancellation, leave, read-only shared-war totals | Full allied roster/history UI, exception-inclusive toggle, invite notification and rejection acknowledgment UI |
| Gear | Reviewed labeled-image extraction, AP/AAP/DP, history, delete-current, local member ranking and manually reviewed rival guild snapshots | Live rival tracking and daily refresh, game-screen-specific crop profiles |
| Live analysis | Sessions, ingest, duplicate IDs, chronological feed, one-minute chart, replay slider, stop/save, war link, public recap/revoke, enemy profiles, manual character/family resolution, visible backoff fixture | Automatic BDO class discovery queue, true push transport, per-guild zoom controls, full debrief layout |
| Capture / IKUSA | Browser JSON event-file import, incremental JSONL tail with rotation/partial-line handling, desktop file-adapter companion, independent IKUSA text parser, midnight rollover | **Native BDO packet decoding is not implemented.** No Windows Npcap integration or executable auto-update. IKUSA contract tests use synthetic lines; real logs still need validation |
| Streams | Twitch linking, fixture directory, viewer/category/partner display, category filter, live API refresh adapter | Partner lookup, embedded player/carousel, automatic authenticated refresh/backoff testing |
| Scheduled operations | Timezone-aware weekly/sync schedule, idempotent run records, lookback catchup, reminder processing and milestone previews | Continuous service installation and external roster-source fetching; sync jobs explicitly report missing source unless a fixture is configured |
| Community | Tickets/replies/close, ticket categories, application forms/submit/review, welcome message and local role assignment, reminders | Native Discord ticket channels, real role buttons, more granular applicant ownership/views and notification routing |
| Fun / AI | Roll, simulated challenge opponent, persistent enhancement minigame; deterministic roast and extractive discussion summary | Real opponent acceptance, configurable LLM adapter; local text utilities are not represented as AI generation |
| Configuration | Local access controls, channels, schedule forms, generic settings API for roles/overrides/recruitment/tickets, audit history, confirmed stats purge, adoption-key flow | Full settings UI for each nested value, live permission override semantics, guild disband workflow |
| Discord | 53 command names build locally; local command dispatcher; optional gateway/OAuth/send-update adapters; no external messages sent | End-to-end Discord tests, native command argument forms and interactive cards, complete command-by-command behavioral parity |

## Interpretation

All major product areas have a usable local workflow or a clearly labeled adapter/simulator. This is **not yet a working prototype of every individual documented behavior**: the rightmost column is remaining work, not silently accepted scope reduction. Native game capture is the largest missing capability and cannot be verified from the currently available data.

## Validation evidence

- Django domain/API tests exercise transactions, permissions, attendance, waitlists, alliances, reminders, OCR parsing, OAuth-state rejection, role mapping and event-file handling.
- Chromium smoke checks cover every dashboard section, member creation/search and responsive layout with no JavaScript errors.
- Real Tesseract invocation recognizes the generated two-panel fixture. A narrow/ambiguous numeric row is rejected by the parser.
- `runbot --check` constructs all 53 commands without opening a Discord connection.
- No live Discord, Twitch, BDO account, real packet capture or real war screenshot validation has been performed.
