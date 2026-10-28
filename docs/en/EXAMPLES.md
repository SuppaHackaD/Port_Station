# Tested example configurations

[Documentation](INDEX.md) · [Home](../../README.md)

The examples demonstrate two working integrations with different profiles.
For another game, follow [new game configuration](NEW_GAME.md); you do not
need to adapt either example.

Included images are owned placeholders. Selection music is disabled by default.

## Breath

Project: `port_station/examples/breath.ps5port.json`.

- Tested version: Breath 1.0.3, Unity 2019.
- Profile: `dxvk-xinput`, Direct3D 11, 1280×720 window.
- Achievements: 11 originals and optional completion.

Select your original game folder in the project. The build automatically
prepares the achievement bridge **in the output copy**, preserving the PC
installation. Previously prepared copies are accepted too: the bridge
connection is verified and is not patched a second time.

To keep a separate prepared copy, use this optional command:

```powershell
python release_support/prepare-game.py breath --source "D:/Games/Breath" --output "D:/Prepared/Breath"
```

The preparer adds the owned bridge and adapts two achievement routines in a
copy. It recognizes the original assembly by SHA-256
`b98be2ab162e9f7f2ff4029b0bf8221db075df052d5782b96c73424c6ee95f18`;
other revisions are rejected rather than modified incorrectly. The bridge
forwards events to the backend before the Steam query. Without it, capturing
the eel in the original copy can request game shutdown when Steam initialization
is attempted on the console.

Customize the icon, backgrounds, title and music as with any project.

When updating an existing installation, the launcher synchronizes the prepared
bridge and achievement assembly before starting Wine. You do not need to erase
the prefix or saves to receive this fix. `breath-compatibility.json` reports
whether the input was original or already prepared and records output hashes.

Choose another Title ID for a separate installation. For a separate backend
achievement list too, choose another stable game ID, such as `breathy`.
The adapter supports this customization while retaining the 11 original
achievement IDs emitted by the game.

## The Coffin of Andy and Leyley — TCOAAL

Project: `port_station/examples/tcoaal.ps5port.json`.

- Tested version: 3.0.13, NW.js 0.29/RPG Maker.
- Profile: `nwjs-canvas`.
- Achievements: 20 originals and optional completion.

```powershell
python release_support/prepare-game.py tcoaal --source "D:/Games/The Coffin of Andy and Leyley" --output "D:/Prepared/TCOAAL"
```

The preparer fills missing choices in local translations when it finds a
compatible native catalog. During the build, the profile registers local
fonts and applies the CSS fallback. The bridge maps the observed achievement
APIs to the catalog IDs.

For revision 3.0.13, the native language database is
`www/data/9c7050ae76645487`, with no extension. `Critical error: language data missing`
can mean this file was renamed or is absent. The build preparer recognizes the
known file renamed to `.txt` and restores its name only in the output copy,
after SHA-256 verification. The new build also synchronizes that file into an
existing prefix while preserving saves. `nwjs-assets.json` records the repair;
files from other revisions are not renamed by guessing.

Check the Achievements tab when reusing another project: this example has
20 TCOAAL achievements, rather than Breath's 11. Optional completion is added
separately.

Open the example and select the prepared folder. The profile already adds
`canvas` as its first argument.

The internal `tcoal` key remains unchanged so existing progress and data are
recognized; the example's name is TCOAAL.

## Game updates

These projects describe the versions listed above. Updates to the engine,
data files or achievement APIs can require another configuration. Save a copy
of your project to experiment without replacing the previous settings.

Examples use their own catalog revision for the included images. If you
replace images or text after synchronization, increase the catalog version.
