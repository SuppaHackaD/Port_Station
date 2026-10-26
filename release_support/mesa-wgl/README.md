# Mesa WGL lifetime diagnostic

This is a **diagnostic x64 provider**, not a release runtime or a resolution-switching fix.
It adds `STATION_MESA` messages around context, framebuffer, resource and display-target
destruction. It does not relax Vulkan display ownership or grant achievements.

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
