# Configure a new game

[Documentation](INDEX.md) · [Home](../../README.md)

This guide starts from a new project and does not depend on the Breath or
TCOAAL examples. Profiles are starting configurations: finding a working setup
may require testing the executable, renderer, arguments and controls separately.
The current UI uses Portuguese labels; their meanings are given below.

## 1. Choose the input files

Select the **complete Windows game folder**, including the data, DLLs and
subfolders used by the executable. Select the main `.exe`, rather than a
shortcut or installer.

**Executável** (Executable) is relative to the selected folder. For example:

```text
Game folder: D:/Games/MyGame
Executable: bin/MyGame.exe
```

The app detects x86 or x64 from the executable and sets the working directory
to its subfolder. Input files are copied into the package; the build does not
edit the original PC installation.

## 2. Set the identity

| Field | How to choose |
|---|---|
| Display title | The name shown on the console. |
| Title ID | `PPSA` + five digits, different from titles you already use. Example: `PPSA99510`. |
| Stable achievement game ID | A lowercase name with letters, digits, `.`, `_` or `-`, up to 32 characters. Example: `my.game`. Keep it across builds to retain the same backend entry. |
| Application version | Use `01.000.001` format. Increase it when updating the title. |

The Title ID identifies the console application. The achievement game ID
identifies the game in the backend; it is not a username and need not match a
platform account.

## 3. Choose a profile

| Profile | When to start with it | Initial controls |
|---|---|---|
| `dxvk-xinput` | Direct3D games with XInput support. | XInput. |
| `opengl-xinput` | OpenGL games through Mesa/Zink over Vulkan. | XInput. |
| `nwjs-canvas` | NW.js/RPG Maker games with a Canvas mode. | Buttons mapped to keyboard keys. |
| `gdi-keyboard` | 2D/GDI applications or games requiring a keyboard. | Buttons mapped to keyboard keys. |

`nwjs-canvas` adds `canvas` as the first argument and configures a writable
NW.js data folder. Do not add `canvas` again. Games that require WebGL may
need a different configuration.

The NW.js font fix installs local CSS-referenced TTF/OTF fonts in the prefix
and favors local font loading. It runs automatically when building this profile.

### LÖVE

Use `opengl-xinput`. Port Station recognizes the verified x64 LÖVE 11.4 DLL by
SHA-256 and prepares a Wine user-directory helper in the build copy. For the
verified Intravenous 2: Mercenarism executable, it also fixes the controller
descriptor used by the options menu. Input files are preserved; other DLL or
executable revisions need separate validation.

For achievements in this revision, import the official catalog and choose
`file-v1`. The build integrates a publisher of the game's original award calls.
The report should include `achievement_producer` with type
`love-platform-setachievement-v1`. Other LÖVE executables do not automatically
receive this bridge. See [achievements](ACHIEVEMENTS.md).

`love-compatibility.json` records prepared files and their hashes. Before
launching the game, the package updates these files in an existing cached
prefix while preserving saves and other resources. This lets you reinstall
a corrected build with the same Title ID using the complete generated folder.

When a game fails, change one setting at a time. Changing renderer, arguments
and controls together makes it harder to identify the fix. A profile cannot
supply every API or component missing from the runtime.

## 4. Launch arguments

### Resolution and display

Under **Jogo → Resolução do desktop virtual** (Game → Virtual desktop
resolution), `auto` queries the VideoOut size at title startup. If that fails
or returns invalid data, it uses 1920×1080. The current limit is 3840×2160.
You can select or type a size such as `1920x1080` or `2560x1440`.

This defines the desktop and the upper limit of the modes advertised to the
game. The game controls its rendering resolution and can select smaller modes
through its own menu when supported. A 4K display does not require rendering
at 4K; lower the in-game resolution if needed for performance. The graphics
backend presents to the supported console output while preserving the aspect
ratio with `scaling=fit`. The GDI presenter still uses 1080p output.

The advanced `display.desktop` option takes precedence over the UI field;
remove that override to use `auto`. Arguments such as `-screen-width` and
`-screen-height`, or settings saved by the game, can also enforce a particular
resolution. The Breath example retains its tested 720p arguments; remove them
when testing menu selection. Detection happens at launch: reopen the title
after changing the TV or the PS5 output setting.

In project JSON, use `"display_resolution": "auto"`. Older projects without
this field also use `auto`; existing advanced overrides are preserved. Mode
changes depend on the engine and renderer and must be tested per game. This
does not add HDR or change the refresh rate.

Automatic detection, 4K → 1080p → 720p → 4K switching and reselection of the
same adapter were validated in the x64 OpenGL/Zink Intravenous port on 13.60.
The corrected runtime releases the presentation reference retained by the
context before recreating the window. Other games still need validation.

Use arguments that the game actually recognizes. For a Unity game supporting
these parameters, for example:

```text
-force-d3d11 -screen-width 1280 -screen-height 720 -screen-fullscreen 0
```

Do not apply these arguments indiscriminately to other engines. If no required
argument is known, start with the field empty.

## 5. Adjust controls

Start with XInput when the game already supports controllers. Keyboard profiles
initially map Cross to Enter, Circle to Escape, Square to Shift, Triangle to X,
and the directional buttons to arrow keys.

Under **Avançado → Opções do perfil** (Advanced → Profile options), you can
override the key assigned to each button. Example:

```json
{
  "input": {
    "mode": "keyboard",
    "cross": "enter",
    "circle": "escape",
    "square": "shift",
    "triangle": "x",
    "l1": "pageup",
    "r1": "pagedown"
  }
}
```

These options do not change the **Options + touchpad click** exit shortcut.
Test controls both in menus and during gameplay; a button can serve different
functions on those screens.

Advanced options accept `display`, `input`, `runtime`, `debug` and
`application.dll_overrides`. Names and values depend on the runtime parser;
prefer the profile defaults until you identify a specific need.

For a Direct3D game without native controller support, keep `dxvk-xinput`
and override only its input settings. Experimental keyboard/mouse example:

```json
{"input":{"mode":"keyboard","left_stick":"dpad","mouse":"right_stick","mouse_speed":"800","up":"w","down":"s","left":"a","right":"d","cross":"space","square":"e","r2":"mouse_left","l2":"mouse_right","circle":"escape","options":"escape","create":"none"}}
```

`left_stick: dpad` sends the keys assigned to directional buttons from the
left stick, with a dead zone and release on disconnect. The right stick moves
the mouse. Games still show keyboard/mouse prompts; test their particular
shortcuts, sensitivity and minigames. This does not add native controller
support to the engine.

## 6. Customize presentation

- **Icon:** select an image; the app prepares a center-cropped 512×512 PNG.
- **Backgrounds:** common image formats are converted to 3840×2160 DDS BC7.
  Selecting one background uses it for both screens.
- **Selection music:** select audio and adjust its start/duration in the
  **Áudio** tab. This plays in the title presentation, not as the game's soundtrack.

The ATRAC9 encoder is included in the kit. MP3/WAV/OGG/FLAC/M4A/AAC and other
formats use the optional FFmpeg installed as described in the quick start.
The default clip is 15 seconds; the maximum is 87.3 seconds. A ready-made `.at9`
is copied in full without trimming.

Leave backgrounds and music empty to simplify the first build if desired.

## 7. Test without achievements first

Use adapter `none` with no catalog items. Click **Validar projeto** (Validate
project), then **Compilar e empacotar** (Build and package).

After copying the complete folder to the console, check in this order:

1. Initial preparation completes and the game reaches its menu.
2. Text and images appear.
3. Audio and controls work.
4. A new game starts and a save loads after reopening.
5. Closing and reopening work.

Once stable, configure the [achievement catalog and adapter](ACHIEVEMENTS.md).
This helps distinguish startup failures from integration failures.

## 8. Adjust and rebuild

Save the `.ps5port.json` to reuse your settings. The UI creates a new folder
for each build. Arguments and owned bridge scripts synchronize at title startup.

An updated build does not automatically replace every file already prepared
on the console. When changing game files, the registry or overlays, test with
another Title ID or plan a prefix update. This matters particularly when
changing game versions; changing only arguments does not require that procedure.

## Common problems

In `auto` mode, OpenGL/DXVK follow the console output up to 4K. Canvas/GDI
use a 1920×1080 ceiling to reduce memory consumption from software surfaces.
TCOAAL 3.0.13 was validated on the console at 720p and 1080p; a 4K virtual
desktop caused memory-mapping failure and process exit. This automatic policy
does not change the PS5's physical output mode. An explicit resolution still
takes priority and must be validated with the game.

| Symptom | First things to check |
|---|---|
| Build does not start | Folder path, selected `.exe`, icon and diagnostics. |
| Immediately returns to the loader | Main executable, complete DLLs/data and startup log. |
| NW.js stays on loading | Canvas availability, selected profile, fonts and engine log. |
| Controls work in menus but not gameplay | Keyboard/XInput mapping and the game's own control settings. |
| Black screen or renderer error | The game's graphics API and selected profile; not every dependency is supported. |
| Presentation has sound but the game does not | Selection music is independent of engine audio; inspect the runtime log. |
| Achievement catalog appears but nothing unlocks | Catalog delivery worked; check the actual award event and adapter. |

Output paths containing spaces are supported. The helper invokes the linker
directly, and the launcher uses a response file to preserve paths and long object
lists. An error such as `cannot open 2` when building under
`Intravenous 2 Mercenarism` indicates an installation predating this fix; update
the program files and generate a new build.

Use a different Title ID for each installed game. Reusing another game's ID can
replace its entry and conflict with the preparation cache. Changing only the
visible title does not create a separate installation.

`build.log` records compilation. Startup, runtime and engine logs help locate
post-launch failures. Record the profile, arguments and game version for each test.

## Command line

Save a project through the UI or adapt
`port_station/examples/windows-game.ps5port.json`. From the kit folder:

```powershell
python -m port_station doctor
python -m port_station validate "D:/Projects/MyGame.ps5port.json"
python -m port_station prepare "D:/Projects/MyGame.ps5port.json" --output "D:/Builds/MyGame-review"
python -m port_station build "D:/Projects/MyGame.ps5port.json" --output "D:/Builds/MyGame-build"
```

`prepare` generates configuration and resources for review without compiling
the title. `build` produces the complete folder and ZIP; `--no-zip` keeps only
the folder. CLI destinations must be new: existing builds are not overwritten.
