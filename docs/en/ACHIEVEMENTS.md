# Achievements and the web interface

[Documentation](INDEX.md) · [Home](../../README.md)

Prospero Achievements is an independent payload that receives game catalogs
and events. It stores progress per user and provides a web interface for
browsing lists. Integrated games show a popup after a confirmed unlock.

## Start the backend

1. Copy `build/prospero-achievements/ps5/prospero_achievements.elf` from the kit
   to your loader's payload location.
2. Load the payload once.
3. Open `http://CONSOLE_IP:38765/` in a browser on the same network.
4. Start an integrated game and select the user on the page.

The service remains independent of the game. If unavailable, the client retains
pending events and retries later. Use `pa_stop.elf` when you need to stop the
service; do not load it alongside the service as a dependency.

## Extract achievements

In **Conquistas** (Achievements), click **Extrair do jogo…** (Extract from
game). The window uses the folder and executable configured in the project.
Click **Analisar arquivos** (Analyze files), enter the correct Steam AppID and
use **Buscar textos oficiais** (Fetch official text). Review the entries and
click **Aplicar ao projeto** (Apply to project). The catalog and report are
also saved in your chosen output folder.

**Somente oficiais** (Official only) requires an exact match between a local
ID and an ID returned by Steam. A failed lookup blocks export in this mode.
You may edit or translate names/descriptions without changing IDs. Completion
is a separate project option.

The reader supports JSON/VDF catalogs, known JavaScript calls, Unity Mono
metadata and LuaJIT constants in LÖVE/ZIP packages, including a ZIP appended to
an executable. Constants show that an ID is present, not that an award call
executes. The reader neither launches the game nor executes bytecode. See the
[extractor reference](EXTRACTOR.md) for supported inputs and CLI options.

Event adapters are selected separately. The verified Intravenous 2: Mercenarism
revision receives a LÖVE bridge with `file-v1`; other revisions require their
own validation. `unity-mono-steam` supports only compatible Unity Mono wrappers.

## Configure the catalog

### Completion markers written by the game

The experimental `file-markers` adapter observes empty files the game itself
creates when an achievement condition is met. Verify that relationship first;
a similar filename is not evidence of the original condition. The adapter
does not modify game code, saves or Steam integration.

Map every regular catalog ID to a path relative to the Wine prefix's `drive_c`
in the project JSON:

```json
{
  "adapter": "file-markers",
  "file_markers": {
    "FIRST_WIN": "users/prospero/AppData/LocalLow/OwnedStudio/OwnedGame/Save/FirstWin"
  }
}
```

This example requires a `FIRST_WIN` catalog entry. All regular entries need
distinct paths; completion/platinum remains calculated by the backend. Rules
are configured in the project file and preserved by the UI.

Before starting Wine, the launcher saves its own baseline and ignores files
already present. A new regular empty file, observed twice, queues a durable SDK
event. The baseline recovers an event after queue storage errors or closing
before delivery. Retries reuse the event ID and should not repeat a confirmed
unlock popup. Nonempty files, directories and unmatched paths do not award
achievements. This adapter neither decodes binary saves nor adds conditions.

Add a name, description, icon and ID for each entry in the **Conquistas** tab.
The canonical ID identifies the achievement in the backend. **ID emitida pelo
jogo** (ID emitted by the game) maps a different engine name, such as
`first_win`, to `FIRST_WIN`.

Enable the completion/platinum option to add an achievement calculated after
all regular entries are obtained. Adapters must not unlock it directly.

An extracted catalog may lack descriptions. Backend conversion uses
“Descrição não fornecida” (“Description not provided”) because the protocol
requires nonempty descriptions. The project and extraction report still
record that the original text is missing. You can fill it in later without
inventing an unlock condition.

Increase the catalog version when editing an existing catalog. Preserve IDs
whose progress should remain. Importing through the UI starts a higher revision.

## Choose an adapter

| Adapter | Use |
|---|---|
| `none` | Play without an achievement catalog or events. |
| `nwjs-steam` | NW.js games using `Steam.awardAchievement` or `Steam.API.activateAchievement`. The bridge maps IDs and preserves the original call. |
| `unity-mono-steam` | Experimental generic Unity Mono DLL with a conservative Steamworks.NET wrapper integrator. See the [managed bridge](MANAGED_BRIDGE.md). |
| `file-v1` | File bridge protocol. Includes an automatic producer for the verified Intravenous LÖVE revision; other integrations provide their own producer. |
| `breath` | The specific integration supplied by the Breath example. |

A catalog alone cannot detect when a gameplay condition was met. Games using
other APIs or engines need an integration.

With `file-v1`, the launcher uploads the catalog and consumes files published
by the game. For the verified LÖVE revision, the builder wraps
`love.platformAPI.SetAchievement`, preserving the original call and the game's
progress/difficulty conditions. Only configured IDs are forwarded, using the
source-ID mapping where needed. `love-compatibility.json` records the producer
and the number of mapped IDs.

This integration does not import save achievements or change internal flags.
If the game already considers an achievement obtained, repeating its condition
may not emit another call; test one still locked in the game. The backend
derives completion. Other engines/revisions need compatible producers;
extracting definitions does not create arbitrary integrations.

See [integration](INTEGRATION.md) to add an adapter. The Breath and TCOAAL
examples already provide their integrations.

## Test an unlock

First confirm the catalog appears on the web. Earn an achievement during
gameplay, check its popup and refresh the page. Close and reopen the game to
check persistence without another notification.

Keeping the stable game ID preserves the same backend entry across builds.
Different console users have separate progress.

These are Port Station/Prospero Achievements local achievements, not official
Sony system trophies; they do not sync with PSN. The web UI is read-only and
intended for the local network.
