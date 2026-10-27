# File bridge — Node/NW.js and Windows/LuaJIT

[Documentation](../../../docs/en/INDEX.md) · [Home](../../../README.md)

Add-on to the C SDK 0.1.1. Compile pa_file_bridge.c in the game's native adapter and link the existing SDK archive. Load prospero_file_bridge.js in Node/NW.js. The C worker creates an owned context containing the game ID and active console user, then consumes the corresponding per-user append-only source stream. It must prepare SDK/catalog first and call poll only from its worker.

The game provides an explicit whitelist of achievement IDs. One accepted original game award calls publisher.unlock(id); no save-state heuristic or Steam login is needed. This unlock-only transport reserves the achievement ID itself as a stable event ID in the backend's game/user namespace. Do not reuse those event IDs for unrelated SDK events. Full 64-character IDs are supported. The retained source stream supports recovery across process restarts; the SDK outbox remains the network delivery queue.

The publisher syncs each rare event append, retries failed appends when flush is called, and prefixes records with a newline to isolate incomplete writes. The consumer validates exact canonical records, user/game/ID, incomplete and oversized lines, and advances only after the SDK has durably accepted the event. Duplicate input and replay are idempotent. No HTTP operation runs in the game's JavaScript frame loop. The native adapter performs network calls on its own worker. A single writer/worker owns each context/stream.

Wire records (ASCII, LF): PA_FILE_CONTEXT_V1\tgame\tuser; PA_FILE_BRIDGE_V1\tgame\tuser; PA_FILE_UNLOCK_V1\tgame\tuser\tachievement. Context filename is game-context-v1.txt and stream filename game-user.tsv inside the prefix drive_c/ProsperoAchievements. TCOAAL supplies the first complete integration example. This module does not register system trophies or import foreign account histories.

## Windows publisher

`pa_windows_events.c` builds the owned x64 `paevents.dll`. It exports cdecl functions
`int pa_event_ready_v1(const char *folder, const char *game)` and
`int pa_event_unlock_v1(const char *folder, const char *game, const char *id)`.
Use `C:/ProsperoAchievements` inside Wine, with the same game namespace as the
native adapter. Both functions bind the active user from the canonical context.
Only an explicit award request should call unlock; ready writes no achievement.

Zero means the append was flushed and the handle closed successfully. Negative
results identify invalid arguments (-1), missing context (-2), malformed context
(-3), open failure (-4), seek/write failure (-5), flush failure (-6), or close
failure (-7). Keep failed events pending and retry. The publisher opens with
`GENERIC_WRITE` so `FlushFileBuffers` can commit the data, and permits native
readers while keeping one Windows writer. Game-specific diagnostics go to
`<game>-bridge.log` in the same owned folder. No HTTP runs on the Lua thread.

`port_station/templates/love_achievements.lua` provides a whitelist/mapping,
in-process deduplication and retries around real `SetAchievement` calls. The
original function runs first; its arguments, results and errors are preserved.
`port_station/love_achievements.py` applies this adapter only to a verified module
in a local build copy, retaining the original module. It does not contain or
distribute commercial game scripts. A catalog alone is not a universal producer.
