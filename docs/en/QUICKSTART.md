# Your first build

[Documentation](INDEX.md) · [Home](../../README.md)

The current desktop UI uses Portuguese labels. This guide keeps those labels
in bold and explains their meaning in English.

## Install

On Windows x64, install Python 3.13 with **Tcl/Tk** and extract the **Windows
kit** from the [latest release](https://github.com/SuppaHackaD/Port_Station/releases/latest).
After extracting the 0.4.0 kit, apply the [October 28 cumulative update](https://github.com/SuppaHackaD/Port_Station/releases/download/v0.4.0/Port-Station-v0.4.0-update-20261028.zip) over the kit folder. It includes the previous fixes. Run `Port_Station.cmd`.

Use the Windows kit to build game packages. GitHub's source download is for
development and does not include the runtime binaries.

To add selection music, install the optional decoder once from the kit folder:

```powershell
python release_support/install-ffmpeg.py
```

You can skip this step when building without music.

## Create a project

1. Click **Novo** (New).
2. Under **Jogo** (Game), select the complete installation folder and its main
   executable. The `.exe` must be inside that folder.
3. Enter the title and choose an unused **Title ID** on the console: `PPSA`
   followed by five digits. Set a stable achievement game ID, such as `my.game`.
4. Choose a starting profile: `dxvk-xinput` for Direct3D with a controller,
   `opengl-xinput` for OpenGL/Mesa-Zink, `nwjs-canvas` for NW.js games with
   Canvas support, or `gdi-keyboard` for GDI/keyboard applications.
5. Under **Apresentação** (Presentation), choose an icon. Backgrounds and music
   are optional.
6. Under **Conquistas** (Achievements), leave the adapter set to `none` for the
   first test.
7. Save the project as a `.ps5port.json` file.

In the **Jogo** tab, leave the virtual desktop resolution at `auto` to use the
size reported by the console, or choose its upper limit. The game can select
smaller modes from its own menu. See [resolution and display](NEW_GAME.md#resolution-and-display)
for limits and the precedence of arguments and advanced options.

You can start from `port_station/examples/windows-game.ps5port.json`, which
already includes generic images. Replace its game folder and executable.

## Build

Open **Build e diagnóstico** (Build and diagnostics). Use **Diagnóstico** to
check the tools and **Validar projeto** to validate the project. Click
**Compilar e empacotar** (Build and package) and choose an output folder. The
app creates a new build subfolder and displays progress in the log.

The finished homebrew folder is:

```text
<YOUR_BUILD>/native/dist/<TITLE_ID>/
```

It contains `eboot.bin`, modules, the runtime and the data needed on first launch.

## Run on the console

Copy the complete `<TITLE_ID>` folder to `/data/homebrew/` and refresh your
loader's list. The tested setup launches titles through ShadowMount+.

The first launch prepares writable game data and may take longer. Let that
preparation finish. Later launches reuse the prepared data.

Test menus, text, audio, controls and saves. Hold **Options + touchpad click**
for one second to exit through the runtime. Also test closing through the PS
menu and launching again.

If the game does not start or a feature fails, see [configure a new game](NEW_GAME.md).
Once basic operation is stable, add the [achievement integration](ACHIEVEMENTS.md).
