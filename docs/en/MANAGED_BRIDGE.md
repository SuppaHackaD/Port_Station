# Generic managed bridge · experimental 0.1.0

[Documentation](INDEX.md) · [Home](../../README.md)

`ProsperoAchievements.dll` is a .NET Framework 4.0 library without Unity or
Steam dependencies. The same binary can accompany multiple ports; a configuration
maps IDs emitted by the game to catalog IDs.

```text
Original game condition
  -> adapted award method
  -> ProsperoAchievements.dll
  -> event file inside the Wine prefix
  -> native bridge + SDK outbox
  -> prospero_achievements.elf -> web UI
```

The payload and native SDK handle persistence, retries, notifications, user
isolation and automatic completion. The DLL publishes requests only when the
game calls its award point. It does not evaluate gameplay conditions or create
unlocks at startup.

## Use in Port Station

1. Import/review the catalog and keep each `source_id` exactly equal to the ID
   emitted by the game. Translate names/descriptions, not IDs.
2. Select **`unity-mono-steam`**. The kit must contain
   `build/port-studio/managed/` with the DLL, integrator and `managed.lock.json`.
3. Build again. The integrator reads `*_Data/Managed/Assembly-CSharp.dll` without
   running the game and accepts only a restricted static `void(string)` method
   dedicated to awarding achievements. Its report is `managed/compatibility.json`.
4. The output receives an adapted assembly copy, the generic DLL and
   `ProsperoAchievements.config.tsv`. Inputs remain intact. On launch, the
   launcher also synchronizes these three files in an existing prefix, checking
   size and CRC before replacing each one.
5. With the payload running, test game launch and catalog first. Then earn a
   legitimate achievement, check popup/web state, close/reopen and check persistence.

**Status:** Windows compilation/tests passed, including an owned fixture using
the compiled DLL and native synchronization of large files. Static analysis
recognizes the Kindergarten wrapper used during development. A Kindergarten
PS5 build validated a legitimate Best Boyfriend Ever unlock, popup and backend
persistence. Other games/wrappers need their own validation. Breath's specific
integration remains separately available and validated.

### Automatic integrator limits

The initial pattern is a wrapper checking `SteamManager.Initialized`, querying
whether the achievement is already obtained, then calling
`SteamUserStats.SetAchievement(id)` and `StoreStats()`. The integrator checks
the signature, instruction sequence and branch destinations. It adds a local
route at wrapper entry and preserves the original body for use outside the
port's context.

Methods with extra gameplay conditions, enum-based routines, other APIs or
signatures, strong-named assemblies, IL2CPP and native binaries are rejected.
There is no global SteamManager replacement or replacement of native
`steam_api64.dll`. Unsupported patterns need a reviewed adapter: **using the
same SDK/DLL does not make every game's integration point identical**.
Breath retains its specific recipe; NW.js uses the JavaScript bridge.

Stats and stat-threshold achievements are not converted in this version. A
catalog may include IDs from paths/editions unreachable in the active game;
review it rather than treating static extraction as gameplay coverage.

## Build

From the source root with Python 3.13 and .NET SDK 10:

```powershell
python sdk/prospero-achievements/managed/build.py
dotnet run --project sdk/prospero-achievements/managed/Tests -c Release -- build/port-studio/managed/ProsperoManagedIntegrator.exe build/port-studio/managed/ProsperoAchievements.dll
```

This produces a `net40` DLL and a standalone Windows x64 integrator requiring
no installed .NET on the user's machine. Restore downloads Mono.Cecil 0.11.6
and .NET Framework 4.0 reference assemblies; no game source/files are used.
The kit's .NET/Mono.Cecil notices also apply.

Read-only inspection:

```powershell
build/port-studio/managed/ProsperoManagedIntegrator.exe "D:/MyGame/Game_Data/Managed/Assembly-CSharp.dll"
```

## Manual integration with your own source

Reference the DLL and call it where your game already awards the achievement:

```csharp
if (ProsperoAchievements.Bridge.TryUnlock(originalAchievementId)) return;
// Original platform path when no local port context exists.
```

The return value means the local context took ownership of the request,
including write failures. This avoids entering an unavailable Steam API after
recognizing a valid context. A failure before any write is not persisted by
the DLL; the player must repeat the condition. The native worker performs HTTP
and retries after reading a complete record and placing it in the outbox.

`ProsperoAchievements.config.tsv`, beside the DLL, uses UTF-8 without BOM:

```text
PA_MANAGED_CONFIG_V1\tmy.game
MAP\tRklSU1Q=\tFIRST
```

Separators are real TABs; `RklSU1Q=` is the source ID `FIRST` encoded as UTF-8
base64. Configuration contains regular achievements only. The launcher supplies
`C:\ProsperoAchievements\my.game-context-v1.txt` with the active game/user.
Without a matching context, the DLL retains the original path. Records follow
the [file bridge protocol](../../sdk/prospero-achievements/bridge/README.md),
with no direct backend HTTP access or Sony trophy system dependency.

Do not distribute modified commercial assemblies with project source/tools.
Each user's local copy is prepared by the tool.
