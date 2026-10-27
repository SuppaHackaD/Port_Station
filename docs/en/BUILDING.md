# Build Port Station from source

[Documentation](INDEX.md) · [Home](../../README.md)

This guide is for development. To package a game with the ready-made kit, use
the [quick start](QUICKSTART.md) or [new game guide](NEW_GAME.md).

## Development environment

The frontend uses Python 3.13/Tk and Pillow 13.0.0. The Windows build tools
include Clang/LLD 18.1.8, public SDK v0.44, CMake, Ninja and the Zig versions
verified by the kit. Node.js runs JavaScript tests. .NET SDK 10 rebuilds the
managed tools: Breath preparer, Unity Mono bridge and extractor scanner.

Clone the repository and install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

To compile titles, use `build/` and `tools/` from the matching Windows kit.
They supply public binaries and the clean prefix missing from the source-only
download. Then run:

```powershell
python -m port_station doctor
python -m port_station verify-runtime
python -m unittest discover -s port_station/tests -v
node port_station/tests/test_nw_bridge.js
python release_support/test-prepare-game.py
dotnet run --project release_support/managed/VerifierTests -c Release
```

Audio conversion tests are skipped without FFmpeg. Install it with
`python release_support/install-ffmpeg.py` to run them too.

## Source layout

- `port_station/`: UI, CLI, projects, generators and tests.
- `sdk/prospero-achievements/`: SDK and event bridges.
- `src/prospero_achievements/`: C server and embedded web UI.
- `sdk/ps5-game-port/`: title toolchain integration.
- `build/prospero-evaluation/source-v020/`: runtime sources consumed by builds.
- `release_support/`: example preparation and kit packaging tools.

The frontend is in `port_station`; `achievement_extractor` provides the
integrated analysis and standalone UI. Runtime data paths and game IDs are
independent of the Python package name.

## Backend and SDK

```powershell
python scripts/build-prospero-achievements.py --ps5
python scripts/test-prospero-achievements.py
```

The build embeds `src/prospero_achievements/web/` and compiles the host server,
probes, PS5 payloads and static library. Outputs are in
`build/prospero-achievements/{host,ps5}`. Use a header and `.a` from the same revision.

## Resource and title tools

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-native-tools.ps1
python -c "from port_station.builder import build_profile_checker; build_profile_checker()"
python release_support/build-assets.py
python scripts/build-port-studio-audio.py
```

These rebuild, respectively, the native converter/public libc, profile validator,
BC7 encoder and ATRAC9 encoder. The audio script uses the installed FFmpeg to
update its complete receipt.

A game build generates title-specific C/CMake and recompiles the launcher and
helper. `python -m port_station build <project> --output <new-folder>` uses the
same pipeline as the UI.

Rebuild the supported LÖVE revision's profile and event helpers with
`python -m port_station.love`. It uses the kit's Zig to generate
`build/port-studio/compat/pe64/{paenv.dll,paevents.dll,helper.json}`. Sources are
`port_station/native_compat/paenv.c` and
`sdk/prospero-achievements/bridge/pa_windows_events.c`; the manifest associates
each source with its DLL. Commercial files are prepared locally during a port build.

`port_station.tests.test_love_achievements` uses owned fixtures only. With the
Windows kit, it also checks the real DLL and per-user file output. Set
`PORT_STATION_LUAJIT_DLL` to a local LuaJIT 2.x library to run optional argument,
return, duplicate, error and FFI tests; they execute only project test scripts.

## Managed Breath example preparer

```powershell
dotnet build release_support/managed/Bridge/Bridge.csproj -c Release -o build/release-managed
dotnet publish release_support/managed/Patcher/Patcher.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o build/release-managed
```

Restore uses Microsoft.NETFramework.ReferenceAssemblies 1.0.3 and Mono.Cecil
0.11.6. Bridge/patcher sources are in `src/breath/wine_title/`. Modified game
files are produced locally by users, not by building the project itself.

## Integrated scanner and generic bridge

```powershell
dotnet publish achievement_extractor/managed/Scanner.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o achievement_extractor/bin
python achievement_extractor/build-package.py --seal-helper
python sdk/prospero-achievements/managed/build.py
python -m unittest discover -s achievement_extractor/tests -v
python -m unittest port_station.tests.test_extractor_gui -v
```

The kit includes owned binaries and helper hashes. ZIP/LuaJIT readers are pure
Python; they neither require Lua nor execute the game. See the
[managed bridge](MANAGED_BRIDGE.md) for its tests.

## Runtime and upstream dependencies

Revisions are in `SOURCES.json` and `port_station/runtime.lock.json`; primary
snapshots are in the `upstream-sources.zip` release asset. The prospero-win
snapshot contains Wine patches and scripts such as `tools/build_wine_ps5.sh`
and `tools/build_tls_ps5.sh`.

Rebuilding the entire Wine/Mesa/SDK stack requires the POSIX environment and
toolchains specified upstream. The frontend rebuilds titles and owned components
on Windows using the pinned stack. Bit-for-bit reproduction of the entire
stack on arbitrary machines is not promised.

Rebuilding WGL/Zink with the `needs_present` cleanup is documented in
[the Mesa WGL build guide](../../release_support/mesa-wgl/README.md). Its script
checks the Mesa snapshot and compiler SHA-256, supports `--arch x86_64` or
`--arch i686`, and produces binaries with manifests and modified sources.
The kit runtime uses `--release-pending-present --clean`, without per-frame tracing.

After an intentional, tested tool/runtime change, update the baseline with:

```powershell
python -m port_station lock --accept-current
```

The command preserves the previous lock. Investigate unexpected differences
before accepting a baseline. Component licenses, credits and revisions are in
[third-party notices](THIRD_PARTY.md).
