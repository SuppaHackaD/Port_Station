# API v1 — contract 0.1.0

[Documentation](INDEX.md) · [Home](../../README.md)

TCP port 38765. The SDK uses 127.0.0.1; browsers use the console's LAN IP.
HTTP/1.1 with Content-Length, one request per connection, UTF-8 JSON. Writes
require loopback without Origin. No Trophy2, NPWR or PS5 system databases are used.

## Registration

Upload each PNG first: `PUT /api/v1/assets/<sha256>.png` with the binary body.
Filename and content must match. Then send `POST /api/v1/catalogs`:

```json
{
  "schema": 1,
  "game_id": "my.game",
  "title": "My game",
  "catalog_version": 1,
  "icon": "<64 SHA-256 characters>",
  "achievements": [
    {"id":"FIRST","title":"First step","description":"Complete the first stage.","target":1},
    {"id":"COLLECT","title":"Collector","description":"Find ten items.","target":10,"hidden":false},
    {"id":"ALL","title":"Complete set","description":"Obtain every other achievement.","target":1,"completion":true}
  ]
}
```

Each achievement may supply `icon` with another SHA-256. Only one `completion`
entry is allowed; it depends on all regular entries. An obtained completion
remains obtained if a later catalog adds achievements.

IDs: ASCII letters/digits, dot, hyphen and underscore, at most 64 characters,
starting with a letter/digit and without `..`. `game_id` uses lowercase letters
to avoid filesystem collisions. User IDs are eight lowercase hex digits.
Titles: up to 256 bytes; descriptions: up to 2048; integer targets: 1 to 1,000,000,000.

`hidden` hides presentation text while locked; it does not make catalog data
confidential. An equivalent catalog returns HTTP 200 `unchanged`. Changes
require increasing `catalog_version`. Adding entries and changing text/images
are allowed. Removing IDs or changing existing targets/rules returns 409 until
explicit migration exists. Unreadable catalogs are preserved.

An older catalog with compatible IDs/conditions returns 200
`newer_catalog_active`. The server retains newer metadata and accepts events
from the older game without downgrading its catalog.

## Events

`POST /api/v1/events`:

```json
{
  "event_id":"installation001-session003-event0004",
  "game_id":"my.game",
  "user_id":"0000002a",
  "achievement_id":"COLLECT",
  "type":"progress",
  "value":3
}
```

`type` is `progress` or `unlock`. Progress is an absolute accumulated value,
not an increment; it never decreases and is capped at the target. Unlock marks
the target reached without requiring `value`. Do not send unlock for completion.

The backend normalizes relevant fields, identifies events by user/game/event ID,
records receipt time and includes completion awards in the same transaction.
It acknowledges after synchronizing the write. Repeating identical content
returns `duplicate`; conflicting content for the same identity returns 409.

```json
{"status":"accepted","event_id":"installation001-session003-event0004","new_unlocks":[]}
```

Accepted uses HTTP 201; duplicate uses 200 with empty `new_unlocks`. The SDK
checks status and ID before removing its local file. Displayed time is receipt
by the payload, not the client's offline time.

## Queries

- `GET /api/v1/info`: service/version, api_major/minor, instance_id, uptime and limits.
- `GET /api/v1/games`: catalogs.
- `GET /api/v1/users`: users with progress.
- `GET /api/v1/state/<user>/<game>`: progress, unlocks and Unix timestamps.
- `GET /api/v1/assets/<sha256>.png`: immutable image.
- `/`, `/app.css`, `/app.js`: embedded UI without external fonts/CDNs.

The major version defines required compatibility; SDK 0.1 rejects other majors.
A new instance requires metadata synchronization.

## Persistence

```text
/data/prospero-achievements/
  .service.lock
  service.log
  catalogs/<game>.json
  assets/<sha256>.png
  users/<user>/<game>.journal
```

Journal v1: `[uint32_le length][uint32_le CRC32][UTF-8 JSON]`. JSON contains
the normalized event, `body_sha256`, `received_at` and `awards`. The limit is
4096 events without compaction. Physically incomplete tails are reported in
queries and truncated to the last valid record before the next write. A complete
record with invalid CRC/structure causes an error and is preserved.

The SDK uses a port-owned directory with `identity.txt`, `catalog.json`, assets
and `pending/<hash-event_id>.json`. It does not write directly to server progress.

## Control and errors

`POST /api/v1/service/stop` with an empty body and Content-Length 0 stops only
this service. Loopback/Origin restrictions still apply. `pa_stop.elf` uses it;
the web UI has no stop button.

400: invalid data; 403: nonlocal write/Origin; 404: missing route/game;
409: ID/version conflict; 503: unavailable storage/state; 507: quota.
Never treat errors as unlock acknowledgments.
