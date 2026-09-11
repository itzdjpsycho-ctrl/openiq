# Independent prototype contracts

## Calculations

- Guild K/D divides total included kills by total included deaths, never averages individual ratios. A positive kill count with zero deaths is represented by JSON `null` and displayed as infinity; 0/0 is displayed as 0.
- Member exception status removes that member from guild combat totals. Their personal totals remain available.
- War/row exclusions remove combat statistics, not attendance. Eligibility requires a war on/after the member's join date and outside recorded inclusive vacation intervals. The card uses the last seven eligible wars. Current inactive members retain their historical data.
- Win rate is wins divided by wins plus losses; draws are not in the denominator.
- Gear score is `max(AP, AAP) + DP`. This is an explicit prototype convention, not an assertion about an unpublished upstream formula.
- Improvement compares the last and first included single-war K/D using a denominator floor of one. Consistency uses the population standard deviation of those ratios. Award definitions differ from a possible upstream implementation.
- Event waitlists use signup time within the selected team. Withdrawing promotes the earliest remaining signup. Moves enter the target team's queue at the current time. Repeating a manually requested event preserves wall-clock time in its configured timezone.
- Archiving an event adds one pity point to each waitlisted member, once per event. Three points can be treated as a prototype token; automatic token-based prioritization is not implemented.
- Scheduled jobs write a unique job record per schedule/date. Notification output stays in the outbox. The prototype does not run an autonomous daemon unless a caller repeatedly invokes `tick`.

## API

Authenticated session and CSRF token are required for mutations:

```text
GET  /api/<guild_id>/state/
POST /api/<guild_id>/<module>/<action>/
POST /ocr/<guild_id>/
POST /onboard/
```

JSON mutation responses contain `{ "ok": true, "result": ... }`. Domain validation returns HTTP 400; denied access returns HTTP 403. Modules validate cross-guild record references. The service wraps mutation, revision increment and audit entry in one database transaction.

## Normalized event file

A JSON array or newline-delimited objects:

```json
{"id":"session-1-event-1","at":"2026-09-11T09:00:00Z","kind":"kill","player":"Aster","target":"Opponent","guild":"Moonfall","class":"Warrior","family":"EnemyFamily"}
```

`player` is the killer and `target` the victim, including death events. `kind` describes the local player's perspective. Stable event IDs support repeat ingestion. Timestamps require an offset. The JSONL tail adapter waits for a newline before parsing a partial record; truncated or rotated files reset its read position. Browser ingestion uploads parsed event objects; it does not capture network packets.

## IKUSA text contract

The public CritIQ log-import frontend revealed this interoperable text shape:

```text
[23:59:58] LocalCharacter has killed EnemyCharacter from EnemyGuild (LocalFamily, EnemyFamily)
[00:00:02] LocalCharacter died to EnemyCharacter from EnemyGuild
```

The independently written parser takes an explicit date and timezone offset. It reverses actor/victim for `died to`, and recognizes a greater-than-12-hour backwards clock jump as midnight. Smaller out-of-order clock changes are rejected for review. IDs are derived from date, line position and text; importing arbitrary overlapping subsets is not guaranteed to deduplicate the same way as importing the complete same file.

Only the text format was used as compatibility evidence from the publicly served `ikusaParser` asset. No upstream implementation is bundled. Synthetic contract fixtures are provided; authentic game-log verification remains pending. See [IKUSA introduction](https://ikusa.site/docs/introduction) and [CritIQ documentation](https://critiq.one/docs/index.html).

## External adapters

Discord OAuth follows the [authorization code flow](https://docs.discord.com/developers/topics/oauth2). Tokens remain in the server-side session store. Guild roles are refreshed on requests after three minutes; an API failure invalidates the login rather than retaining unverified privilege.

Twitch uses its [streams API](https://dev.twitch.tv/docs/api/reference/#get-streams). Partner flags in fixture data are fixture metadata; the live adapter does not infer partner status.

Notification delivery is opt-in and separate from preview generation. HTTP retries around a successful remote post followed by a local persistence failure may duplicate a message; a production queue needs durable delivery reconciliation.
