# Pinned Mesa WGL provider builds

[Documentation](../../docs/en/INDEX.md) · [Home](../../README.md)

This helper cross-compiles the pinned Windows x86/x64 WGL/Zink provider in three
variants. They do not change Vulkan display ownership rules or grant achievements.

| Options | Result |
| --- | --- |
| No additional options | Lifetime logging only; original reference behavior. |
| `--release-pending-present` | Lifetime logging and context-owned resource cleanup. |
| `--release-pending-present --clean` | Only context-owned resource cleanup, without added logging. |

After existing queue waits and batch cleanup, the cleanup releases the context's
remaining `needs_present` resource reference. Unbinding may already have cleared
the framebuffer, leaving this independently owned reference behind. It uses the
normal resource reference helper and never forces reference counts. The clean
variant changes only `zink_context.c`; the manifest records `behavior_patch: true`
and `lifetime_logging: false`.

The instrumented cleanup passed the separate console probe: both 1280x720 and
1920x1080 windows rendered 30 frames without OpenGL errors, and display targets
were destroyed between windows. The clean x64 variant also passed in-game
4K → 1080p → 720p → 4K switching and adapter reselection in an already configured
Intravenous 2: Mercenarism port on firmware 13.60. The x86 variant is cross-built
from the same cleanup; its console gameplay validation is separate. The current
workflow builds both architectures without lifetime logging.

Lifetime logging records context/framebuffer destruction and display-target
reference operations, including caller, destination slot and counts. Use logging
variants only for short probes; they can generate large logs in a real game.

Build on Linux with Python 3.12, Ninja and the pinned Python tools from the workflow:

```sh
python release_support/mesa-wgl/build.py --work /tmp/station-mesa-new --jobs 2
```

For the clean runtime use `--release-pending-present --clean --arch x86_64`;
use a second new work directory and `--arch i686` for the 32-bit provider.

The work directory must be new. Mesa and llvm-mingw archives are downloaded from
their public projects and checked against pinned SHA-256 digests. The artifact
contains DLL digests, the added logging source, changed Mesa files with their
original notices, and licence texts. The original Mesa archive and its digest
are declared in the artifact manifest and `SOURCES.json`, allowing the full build
to be reconstructed. No game files or proprietary console SDK are needed.

The cross-build configuration follows
[prospero-win's Mesa build recipe](https://github.com/mpereiraesaa/prospero-win/blob/main/tools/build_mesa_zink.sh).
The underlying WGL and Zink implementations belong to the
[Mesa contributors](https://www.mesa3d.org/) and the pinned
[PS5_Mesa fork](https://github.com/mpereiraesaa/PS5_Mesa).
The cross-compiler is [llvm-mingw](https://github.com/mstorsjo/llvm-mingw).
Their original notices and licences continue to apply. Added Port Station
diagnostic code is MIT-licensed.

Use this provider only for controlled tests. Record and restore the previous
provider and the prepared Wine prefix before returning to a normal game build.
