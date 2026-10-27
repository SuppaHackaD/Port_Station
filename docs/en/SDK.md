# Prospero Achievements SDK 0.1.2

[Documentation](INDEX.md) · [Home](../../README.md)

A C/C++ client for `prospero_achievements.elf`, using HTTP API v1 without Sony
trophy APIs. Manual tests confirmed service continuity and Breath/TCOAAL
integrations; see the root README for tested scope.

Games supply catalogs, icons and events. The payload persists progress per
user/game and serves an embedded web UI. The static library and public header
let a port integrate without embedding the server. The native example links
the same library.

Version 0.1.1 retains protocol v1 and backend 0.1.0 compatibility. It adds an
alternative PS5 directory reader using 64 KiB `getdents` and queue diagnostics
through `last_stage`, `last_errno` and `directory_method` (1: readdir; 2: getdents).
These fields describe queue operations, not every network error. Recompile
clients with a matching header and `.a`: the `PA_SDK` structure changed size.
The directory fix was confirmed on the console.

Version 0.1.2 adds `pa_sdk_pump_with_callback` without changing `PA_SDK`.
The callback receives only newly unlocked IDs from an accepted acknowledgment
with the correct event ID; duplicates/replays do not notify again. It runs on
the adapter worker and must not reenter the SDK. The port chooses how to show
the popup. The backend remains 0.1.0/API1. A lost response can suppress a popup
while the achievement remains committed in the backend.

## Usage

One port worker owns each `PA_SDK` context. Run SDK operations on that worker,
outside rendering: preparation/enqueue perform durable I/O, and pump performs
network I/O. SDK v0.1 does not create threads implicitly. Do not share a
context/outbox among concurrent workers or processes.

```c
#include <prospero_achievements.h>
PA_SDK sdk;
/* Writable homebrew path and the active local console user's ID. */
pa_sdk_init(&sdk, "/data/my-port/achievements-outbox",
            "my.game", "0000002a", PA_SDK_DEFAULT_PORT);
char hash[65];
pa_sdk_asset(&sdk, png_bytes, png_size, hash);
pa_sdk_catalog(&sdk, catalog_json, catalog_size);
pa_sdk_unlock(&sdk, "FIRST_CAPTURE", "session001-event0001");
pa_sdk_progress(&sdk, "COLLECT_10", 3, "session001-event0002");
/* Periodically on the worker, with the port's interval/backoff. */
int acknowledged = pa_sdk_pump(&sdk);
```

Check every return value. Successful enqueue means local persistence, not
server delivery. Pump removes an event only after accepted/duplicate with the
matching event ID. If the payload is absent, the queue remains. A new server
instance triggers catalog/image synchronization again. Preparation can work offline.

Provide an event ID unique per user/game and stable across retries. Use a
persistent installation/session identity and counter, or source-queue identity
and position. Do not generate a new ID for every retry. Game/achievement IDs
are independent of the PS5 Title ID and UI position.

## Build and link

```powershell
python scripts/build-prospero-achievements.py --ps5
python scripts/test-prospero-achievements.py
```

Outputs include `build/prospero-achievements/ps5/prospero_achievements.elf` and
`libprospero_achievements.a`. The header is
`sdk/prospero-achievements/include/prospero_achievements.h`.

Link using the project's PS5 toolchain and the usual libc/kernel/SceNet
libraries. `sdk/prospero-achievements/examples/CMakeLists.txt` shows native
homebrew linking. Ports use public SDK v0.44. See [building](BUILDING.md).

cJSON 1.7.19 (MIT) and Brad Conte's SHA-256 (public domain) are included with
private symbol prefixes to avoid collisions. Sources, licenses and changes
are in `src/prospero_achievements/vendor`. See the [HTTP contract](PROTOCOL.md).

## Current limits

- One writer per service directory; one worker per context/outbox.
- Up to 256 achievements per catalog; JSON up to 128 KiB.
- PNG up to 512 KiB and 1024×1024, identified by SHA-256.
- Up to 4096 events per user/game, without compaction. Aggregate progress at
  milestones, never per frame.
- The adapter supplies the user. The SDK does not query Sony accounts or
  authenticate third-party achievement histories.
- Writes are loopback-only without Origin; the LAN UI is read-only.
- Breath/TCOAAL adapters and confirmed popups are supplied. Automatic payload
  loading and generic migration of gameplay conditions are not implemented.
- Synchronization depends on successful filesystem operations. Actual power
  loss on the PS5 has not been tested.
