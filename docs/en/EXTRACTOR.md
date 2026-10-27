# Achievement Extractor 0.3.0

[Documentation](INDEX.md) · [Home](../../README.md)

Available in Port Station under **Conquistas → Extrair do jogo…** (Achievements
→ Extract from game), and as a standalone app. It recovers achievement IDs
and definitions from a local Windows game and exports an importable catalog.
The standalone extractor does not require the full Port Station kit.

## Getting started

Install Python 3.13 x64 with Tk. In the standalone Windows package, run
`Achievement_Extractor.cmd`; in the source checkout or Port Station kit, run
`achievement_extractor/Achievement_Extractor.cmd`. No extra Python dependencies
are required. The current UI uses Portuguese labels.

1. Select the game folder and its main executable inside that folder.
2. Optionally select a separate local schema under **Metadados extras**
   (Additional metadata).
3. Choose the preferred language. If unavailable, the reader tries English
   and then another available language; the report records the result.
4. Click **Analisar arquivos** (Analyze files). Review names, descriptions,
   icons and items marked for review. Double-click an item to edit it and
   inspect its source.
5. Optionally confirm the Steam **AppID** and click **Buscar textos oficiais
   no idioma escolhido** (Fetch official text in the selected language).
   Only AppID/language are queried, without login or player progress. IDs must
   match exactly. **Só IDs oficiais** (Official IDs only) selects matches from
   the last query and keeps other entries visible for review.
6. Choose a new output directory and click **Exportar JSON** (Export JSON).
7. In Port Station, use **Conquistas → Importar catálogo JSON** to import
   `achievements.json`. Choose the event adapter and optional completion.

**Somente oficiais** (Official only) is enabled by default. Export requires a
successful Steam lookup for the current AppID and accepts only
`locally extracted IDs ∩ IDs returned by Steam`, with exact case-sensitive
equality. Matching titles do not confirm an ID. Unmatched local IDs remain
in the report but are excluded even if selected again. Query again after a
failed lookup or AppID change; disable this option for manual/offline work.

An official-only catalog does not add completion. That is a separate Port
Station choice; leave it disabled for only the original achievements.

Output contains `achievements.json`, `extraction-report.json`, import instructions
and recovered local icons. Image paths are relative so the folder can be moved
as a unit. Existing output directories are not overwritten.

If nothing is recovered, **Salvar só relatório** (Save report only) saves
diagnostics without an empty catalog. The CLI saves that report automatically
and returns code 2 when no items are selected.

## Supported inputs

| Input | Result |
|---|---|
| JSON with `achievements`, Steam schemas and compatible local definitions | IDs, available names/descriptions, hidden flag and local icon reference. |
| Text VDF and legacy binary KeyValues with terminator 8 | Explicit achievement definitions; type-4 `stats` with `bits`. Other binary variants are rejected. |
| Known literal JavaScript calls such as `Steam.awardAchievement("ID")` and `greenworks.activateAchievement("ID", ...)` | IDs and script locations. Comments, strings containing code, regex and dynamic arguments do not become confirmed IDs. |
| Managed assemblies, including Unity Mono game scripts | Strings passed directly to achievement APIs and local string-return maps used by those calls. Mono.Cecil reads metadata/CIL. |
| LÖVE/ZIP packages, including ZIPs appended to PE files, and LuaJIT v1/v2 dumps | Constants with member source/hash, matched exactly against official IDs. No instruction interpretation or proof of executed award calls. |
| Native executable strings prefixed `ACH_`, `ACHIEVEMENT_`, `ACHV_` or `TROPHY_` | Review candidates, unselected by default; no confirmed call relationship. |

This is not a universal engine/container/decryption extractor. Dynamic
expressions, obfuscation, unsupported archives, IL2CPP and other schema
revisions may need future readers. Reports record limits, unresolved managed
calls and read failures. Missing extraction does not prove a game lacks achievements.

Names/descriptions are often supplied by the platform rather than bundled with
the game. When absent, the provisional title is the ID and missing descriptions
remain indicated in the editor/report. Export uses **“Descrição não fornecida”**
(“Description not provided”) so the backend accepts the catalog. Official
lookups request Steam localization, not AI or external-service translation.
Steam may return English if the requested language is unavailable. Manually
edited fields are protected from later queries; received official text remains
in the report for comparison. Network errors preserve existing text and allow
offline work. Remote images are not downloaded; local PNG/JPEG icons up to
4 MiB can accompany export.

The catalog does not implement gameplay conditions, import player progress or
grant achievements. Connecting events is a separate porting step. Keep
`source_id` identical to the game's emitted ID; if an ID is incompatible with
the canonical format, the exporter generates a stable name and preserves the
original as `source_id`.

## Command line

From the directory containing `achievement_extractor/`:

```powershell
python -m achievement_extractor --game-dir "D:/Games/MyGame" --exe "Game.exe" --output "D:/Catalogs/MyGame" --language english
```

Use `--steam-appid 12345 --official-only` for official intersection on the CLI;
lookup failure stops export. `--steam-appid 12345` alone fetches official text
after local analysis. There is no name search or positional matching: confirm
the AppID on the game's Steam page. A root `steam_appid.txt` only supplies a UI hint.

Use `--metadata "D:/Schemas/achievements.json"` for an extra local schema.
`--include-candidates` includes unconfirmed native strings; review their origin
first. No arguments opens the UI. Port Station's **Aplicar ao projeto** (Apply
to project) uses the same JSON exporter/importer, preserving project options;
the catalog does not automatically choose an adapter.

## Build and test

The scanner is independent of game files. With .NET SDK 10, from the source root:

```powershell
dotnet publish achievement_extractor/managed/Scanner.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:DebugType=None -o achievement_extractor/bin
python achievement_extractor/build-package.py --seal-helper
python -m unittest discover -s achievement_extractor/tests -v
```

The Windows package includes the owned scanner and its SHA-256. A source-only
clone supports JSON/VDF/JavaScript readers; without the scanner, managed
analysis is marked partial. The program never starts the selected executable,
executes game scripts, loads game DLLs into its runtime or modifies input files.

## Licenses and references

Owned code uses the Port Station license. Mono.Cecil 0.11.6 is MIT; the .NET
runtime's notices/licenses are included under `LICENSES/`.

- [Steam catalog API](https://api.steampowered.com/IPlayerService/GetGameAchievements/v1/): optional AppID/language lookup; availability depends on Valve.
- [LuaJIT dump format](https://github.com/LuaJIT/LuaJIT/blob/v2.1/src/lj_bcdump.h) and [upstream reader](https://github.com/LuaJIT/LuaJIT/blob/v2.0/src/lj_bcread.c): references for the owned constant reader; LuaJIT is not bundled or executed by the extractor.
- [Mono.Cecil](https://github.com/jbevain/cecil): static metadata/CIL reading.
- [Steamworks achievements](https://partner.steamgames.com/doc/features/achievements): IDs versus display attributes.
- [Valve KeyValues](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/tier1/KeyValues.cpp): format reference; the reader is an independent implementation.
- [Pinned upstream sources](https://github.com/SuppaHackaD/Port_Station/releases/download/v0.4.0/upstream-sources.zip), including Mono.Cecil; [.NET runtime v10.0.13](https://github.com/dotnet/runtime/tree/v10.0.13) supplies the scanner runtime source.

The project is unaffiliated with game developers, Valve or Sony. No commercial
game files, catalogs or images are included. Use your own copy and respect
the authors' rights when sharing extracted results.
