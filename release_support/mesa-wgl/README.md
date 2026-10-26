# Mesa WGL lifetime diagnostic

This is a **diagnostic x64 provider**, not a release runtime or a resolution-switching fix.
It adds `STATION_MESA` messages around context, framebuffer, resource and display-target
destruction. It does not relax Vulkan display ownership or grant achievements.
Revision 2 also records display-target resource reference operations, including
the caller, destination slot and counts before the unchanged reference helper.
This distinguishes resources retained by other owners from a window destruction
callback that was never reached. Run only the short two-window probe with this
provider; logging every displayed frame can produce large logs in a real game.

An experimental variant adds `--release-pending-present`. After the existing
queue waits and batch cleanup, context destruction releases its remaining
`needs_present` resource reference. Unbinding may already have cleared the
framebuffer, leaving this independently owned reference behind. The variant
logs the released field and uses the normal resource reference helper. It does
not force reference counts, destroy another context's resource or change WSI
ownership rules. Its manifest has `behavior_patch: true`; the default command
below remains diagnostic only. The current workflow builds the experimental
variant for the two-window console test. Neither variant is a release runtime.

Build on Linux with Python 3.12, Ninja and the pinned Python tools from the workflow:

```sh
python release_support/mesa-wgl/build.py --work /tmp/station-mesa-new --jobs 2
```

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
