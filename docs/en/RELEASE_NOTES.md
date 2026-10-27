# Release notes

[Documentation](INDEX.md) · [Home](../../README.md)

## 0.4.0 — first public release

The complete kit includes the Python/Tk frontend and CLI, Wine/prospero-win
runtime, public SDK, compilers and resource tools. No previews or update chain
are required. Python 3.13 x64 with Tcl/Tk is the external prerequisite; FFmpeg
is optional for decoding audio files.

### Packaging and presentation

- Reusable projects with Direct3D/DXVK, OpenGL/Mesa-Zink, NW.js/Canvas and GDI profiles.
- Optional custom title, icon, backgrounds and music, with BC7 conversion and
  local ATRAC9 encoding.
- Automatic or configurable virtual desktop up to 4K. The OpenGL backend
  releases the presentation reference at context destruction so compatible
  games can recreate their window when changing resolution.
- Options + touchpad click exit shortcut and PS-menu closing in the tested
  environment; writable data preparation and compatibility-file updates in
  cached prefixes while preserving saves.

### Achievements

- Integrated extractor for JSON/VDF, JavaScript, Unity Mono and LuaJIT constants
  in LÖVE/ZIP packages, including ZIPs appended to executables.
- Exact intersection with official Steam IDs, official text lookup by language
  and manual editing, without automatic external translation services.
- Prospero Achievements backend, persistent SDK queue, confirmed-unlock popup,
  per-user progress and optional backend-derived completion.
- NW.js, Unity Mono, Breath and file-protocol adapters. The verified Intravenous
  LÖVE revision receives an original `SetAchievement` call producer, with the
  owned source and DLL included.

### Compatibility and validation

Manual PS5 13.60 checks confirmed sampled gameplay and achievement functions in
Breath, TCOAAL, Kindergarten and the x64 Intravenous 2: Mercenarism 1.7.1 revision.
The user confirmed the LÖVE bridge's real unlock test. Intravenous also passed
4K → 1080p → 720p → 4K switching and reselection of the same adapter without
the previous black screen. Coverage is by feature/section, not complete
campaigns or a guarantee of other game revisions.

Local tests cover builds, catalogs, fonts, event transport, user isolation,
replay, write failures and preservation of the original game API. CI checks
source and extractor behavior without commercial files. Recipes, revisions,
hashes and reconstruction instructions accompany the kit.

### Installation

Download `Port_Station-0.4.0-windows-kit.zip`, extract into a new folder and run
`Port_Station.cmd`. See the [quick start](QUICKSTART.md). Open existing
`.ps5port.json` projects in the new kit and build again; the app does not
automatically replace the console installation.

Breath and TCOAAL configurations are examples with owned placeholder images.
No games, saves, official artwork or commercial music are distributed. Complete
project source, compiled backend/SDK and upstream sources accompany the release.
