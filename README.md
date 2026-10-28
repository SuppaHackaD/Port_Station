# Port Station

Build PS5 homebrew packages from your own Windows game files using Wine and
[prospero-win](https://github.com/mpereiraesaa/prospero-win). Configure graphics,
controls, presentation and achievements through a Python desktop app or CLI.

**[Download the Windows kit](https://github.com/SuppaHackaD/Port_Station/releases/latest)**
· [Português](README.pt-BR.md) · [New game guide](docs/en/NEW_GAME.md)
· [Achievements](docs/en/ACHIEVEMENTS.md) · [All guides](docs/en/INDEX.md)

Port Station is a compatibility and packaging tool, not an automatic native
recompiler. Game support depends on the engine, renderer and APIs it uses.
The initial public release is **0.4.0**; compatibility remains experimental.

## Quick start

1. Install **Python 3.13 x64 with Tcl/Tk** on Windows.
2. Download and extract `Port_Station-0.4.0-windows-kit.zip` from the release.
   It includes the public SDK, compilers, runtime and resource tools. GitHub's
   source download alone is intended for development.
   Then apply the [October 28 cumulative update](https://github.com/SuppaHackaD/Port_Station/releases/download/v0.4.0/Port-Station-v0.4.0-update-20261028.zip) over the kit folder, replacing program files. It includes the earlier fixes; no update chain is needed.
3. Run **Port_Station.cmd**. Create a project and select the complete game folder
   and its main `.exe`.
4. Choose a compatibility profile and an unused `PPSA` + five-digit Title ID.
   Start with achievements disabled while testing basic compatibility.
5. Build into a new output folder. Copy the complete generated
   `<build>/native/dist/<TITLE_ID>/` folder to `/data/homebrew/` on your console
   and refresh your loader.

The first launch prepares writable game data and can take longer. Hold
**Options + touchpad click** for one second to exit, or close the game through
the PS menu in a supported setup.

The tested environment is PS5 **13.60**, Relapse, PLDMGR 0.6.1 and ShadowMount+.
You need a console already capable of running homebrew. This project does not
provide a jailbreak or Sony's proprietary SDK.

The detailed [quick start](docs/en/QUICKSTART.md) walks through the first build.
A [generic project](port_station/examples/windows-game.ps5port.json)
is included; the tool does not depend on either example game.

## Features

- Python/Tk desktop UI and CLI sharing the same build pipeline.
- Direct3D/DXVK and OpenGL/Mesa-Zink profiles with XInput, NW.js Canvas, and GDI
  with keyboard mappings.
- Automatic or configurable virtual desktop resolution up to 4K, with in-game
  mode selection where supported.
- Custom title, icon, backgrounds and optional selection music; local PNG/BC7
  image conversion and ATRAC9 audio encoding.
- Stick-to-keyboard and mouse mappings for games without native controller support.
- Integrated achievement extraction, including Unity IL2CPP and serialized asset candidates, exact official Steam ID matching,
  official localized text lookup and manual metadata editing.
- Optional completion achievement, event adapters and **Prospero Achievements**,
  an independent persistent backend with a web UI.
- Reusable `.ps5port.json` projects, build logs and dependency hashes.

MP3 and other audio inputs need the optional FFmpeg decoder. Install it from the
kit folder with `python release_support/install-ffmpeg.py`. No music is required
to build a package.

## How it works

```text
Your Windows game + project configuration
                  |
        Port Station (Python UI / CLI)
                  |
  validation -> local preparation -> native compilation -> package
                  |
  PS5 launcher + Wine/prospero-win + your local game files
                  |
  game award adapter -> native SDK queue -> Prospero Achievements
                                                   |
                                                web UI
```

Game files are prepared in the build output. The original PC installation is
preserved. The package contains a title-specific launcher, compatibility runtime
and an initial data seed; writable data and saves live in the title's own
directory on the console.

Achievement extraction supplies definitions, not gameplay conditions. Select an
adapter compatible with the game's actual award API, or implement one using the
[SDK and integration guide](docs/en/INTEGRATION.md). The backend stores progress by
game and console user and can derive the completion achievement. These are
**local achievements**, not Sony system trophies; they do not sync with PSN.

## Tested configurations

These are manual compatibility checks, not a promise of full campaign coverage
or support for every revision of the games or engines.

| Game | Tested path | Configuration |
|---|---|---|
| Breath 1.0.3 | Unity 2019, DXVK/XInput, gameplay and achievement events | [Example project](port_station/examples/breath.ps5port.json) |
| The Coffin of Andy and Leyley 3.0.13 | NW.js/Canvas, local fonts, gameplay and achievement events | [Example project](port_station/examples/tcoaal.ps5port.json) |
| Kindergarten | Compatible Unity Mono award wrapper and official achievement events | Create a project; use `unity-mono-steam` after extracting the official catalog |
| Intravenous 2: Mercenarism 1.7.1 | Verified LÖVE x64 revision, OpenGL/XInput, resolution switching and achievement events | Create a project; use `opengl-xinput` and `file-v1` with the official catalog |

The LÖVE preparation is fingerprint-gated; it is not a universal LÖVE adapter.
See [new game configuration](docs/en/NEW_GAME.md) and [example versions](docs/en/EXAMPLES.md).
The included example art is original placeholder artwork; no game music is bundled.

## Documentation and development

- [First build](docs/en/QUICKSTART.md)
- [Configure a new game](docs/en/NEW_GAME.md)
- [Achievements and web backend](docs/en/ACHIEVEMENTS.md)
- [Example projects](docs/en/EXAMPLES.md)
- [Build from source](docs/en/BUILDING.md)
- [Architecture and adapters](docs/en/INTEGRATION.md)
- [Contributing](docs/en/CONTRIBUTING.md)
- [Release notes](docs/en/RELEASE_NOTES.md)
- [Credits and component licenses](docs/en/THIRD_PARTY.md)

The release includes the complete project source, compiled tools, the backend
and SDK, and pinned upstream source archives. The achievement extractor is
available inside the app and can also run independently from
`achievement_extractor/Achievement_Extractor.cmd`.

## Credits, license and game ownership

Port Station builds on **prospero-win**, **Wine**, the **ps5-payload-dev public
SDK**, **PS5_Mesa / Mesa-Zink**, **PS5_Vulkan**, **DXVK**, **PS5 Native App
Boilerplate**, **Lapy JB Daemon**, **ps5-forwarder-manager**, **PS5_ArtSwap** and
the other projects credited in [THIRD_PARTY.md](docs/en/THIRD_PARTY.md). Their authors
retain credit and their component licenses remain applicable.

Our code is **GPL-3.0-or-later**, except files with an explicit individual
license. See [LICENSE](LICENSE) and [NOTICE](docs/en/NOTICE.md).

This is an independent community project, unaffiliated with Sony, Valve or the
developers of the example games. **No games, commercial game binaries, official
game artwork or soundtracks are distributed.** Supply your own legally obtained
files and support the creators.

Games tested:
[Breath by Herbherth](https://store.steampowered.com/app/1475350/).
[The Coffin of Andy and Leyley by Kit9 Studio](https://store.steampowered.com/app/2378900/).
[Kindergarten by Con Man Games](https://store.steampowered.com/app/589590/).
[Intravenous 2: Mercenarism by Explosive Squat Games](https://store.steampowered.com/app/2651330/).
[MiSide by AIHASTO](https://store.steampowered.com/app/2527500/).
