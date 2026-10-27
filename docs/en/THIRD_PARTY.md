# Credits and licenses

[Documentation](INDEX.md) · [Home](../../README.md)

These projects make Port Station possible. Upstream authorship remains in the
original source and notices. Port Station does not claim authorship of Wine,
drivers, the public SDK or codecs.

| Component | Authors/project and license | Revision used |
|---|---|---|
| Main runtime | [mpereiraesaa/prospero-win](https://github.com/mpereiraesaa/prospero-win), LGPL-2.1-or-later | 0.2.0; commit `644e32e400c555e340d507383398c5d21b39b0b0`; consumed sources in `build/prospero-evaluation/source-v020` |
| Wine | [Wine contributors](https://gitlab.winehq.org/wine/wine), LGPL-2.1-or-later and internal component notices | `490f6d5dcbb2a5047345b8af88d114bbcaad69a8` + prospero-win patches |
| Title, FSELF, owned libc | [BlackBearReloaded / PS5 Native App Boilerplate](https://github.com/mpereiraesaa/ps5-native-app-boilerplate), GPL-3.0-or-later; tools obtained from PS5_Vulkan | Title `9c0b994a048521af6fb84c73ded364504fe250e9`; module `30597512539e7edfde079cbcaf4a626bc0a948c5`; complete local sources in `tools/PS5_Vulkan/tooling/native` |
| Public SDK | [ps5-payload-dev](https://github.com/ps5-payload-dev/sdk), GPL-3.0-or-later and bundled library licenses | v0.44; not Sony's official SDK |
| Per-title privilege helper | [Arksama / Team PHU — Lapy JB Daemon](https://github.com/mpereiraesaa/PS5-Lapy-JB-Daemon), MIT | Local base `b48b7d7236eca25c7b9dfd6c040c763ae05dde80`; changes/sources in `tools/Lapy-breath-reference/source`; rebuilt per Title ID |
| RADV/Mesa driver, WGL/Zink | [mpereiraesaa/PS5_Mesa](https://github.com/mpereiraesaa/PS5_Mesa), Mesa contributors, per-file permissive licenses; PS5 linkage GPL | RADV `01d70579b8d410d6a482e36c6f184798ae4c83ad`; Zink `e4607ef697fe3df8d1ebc329bf1917d041843306` |
| Vulkan platform | [PS5_Vulkan](https://github.com/mpereiraesaa/PS5_Vulkan), [mihawk-99/PS5_PayloadSDK](https://github.com/mihawk-99/PS5_PayloadSDK), GPL-3.0-or-later | `8aee3afb37bcfad06f0c7d263b901040f08ebbd0` / `95c08f27386fc698f6bbe21dde3030140a41d10b` |
| DXVK | [doitsujin and contributors](https://github.com/doitsujin/dxvk), zlib | 2.6.2; public D3D11 profile DLLs |
| BC7 presentation | [heydemoura/ps5-forwarder-manager](https://github.com/heydemoura/ps5-forwarder-manager), GPL-3.0-or-later; stb under its own licenses | `4c463596e5eaf42648200117cb6c67c0769b01f8`; `port_station/vendor/forwarder` |
| ATRAC9 encoder | [griches/PS5_ArtSwap](https://github.com/griches/PS5_ArtSwap), GPL-3.0-or-later; LibAtrac9 tables MIT | `03a5c40b9b34bba20deaae46aa0de272f21065cf`; local host adapter/driver; `port_station/vendor/artswap_at9` |
| Optional FFmpeg | [FFmpeg contributors](https://ffmpeg.org/) / [Gyan Doshi build](https://www.gyan.dev/ffmpeg/builds/), GPLv3 for the selected build | `bf0e831606938f530326c9679591109407fa8d0d`; executable excluded from releases; verified direct user download |
| Backend JSON/hash | [Dave Gamble/cJSON](https://github.com/DaveGamble/cJSON), MIT; [Brad Conte](https://github.com/B-Con/crypto-algorithms), public domain | cJSON 1.7.19; SHA-256 `cfbde48414baacf51fc7c74f275190881f037d32`; namespace changes in `src/prospero_achievements/vendor` |
| Managed patcher | [Jb Evain/Mono.Cecil](https://github.com/jbevain/cecil), MIT | 0.11.6; no game assembly included |
| Font rendering | FreeType 2.13.3, FreeType License; DejaVu, Noto, Faustina and Wine fonts under their respective notices | Runtime font licenses and Faustina OFL included |
| TLS | GnuTLS 3.8.13, Nettle 3.10.2 and dependencies; component LGPL/GPL/permissive licenses | Licenses/AUTHORS in runtime `LICENSES/gnutls` and nettle |
| Host tools | LLVM 18.1.8 (Apache2/LLVM exception), Zig (MIT/components), CMake (BSD), Ninja (Apache2), Pillow 13.0.0 (HPND), .NET (MIT/components), zlib 1.3.2 (zlib) | Pinned in runtime.lock; notices in their respective directories |

VideoOut tile permutation derives from John Törnblom's SDL/PS5 code under
zlib. Its notice is in runtime `native/pw_videoout_ps5.c`. That routine does
not require a separate SDL installation.

The original runtime inventory accompanies the kit at
`build/prospero-evaluation/staged/PPSA99995/{THIRD_PARTY.md,SOURCES.txt,LICENSES/}`.
Also read vendored notices and audio manifests. Root licenses do not replace
individual component notices.

The kit's WGL/Zink includes Port Station's release of the `needs_present`
reference at context destruction. Reconstruction, source checks and binary
associations are in `release_support/mesa-wgl/`. Original Mesa notices apply;
added code is MIT-licensed.

The `paenv.dll` user-directory helper is Port Station GPL-3.0-or-later code,
with source in `port_station/native_compat/paenv.c`. It queries the current
process token and USERPROFILE, and contains no game components. Preparers and
other files retain their individual licenses.

The Windows publisher `paevents.dll` and Lua adapter are owned MIT code.
Sources are `sdk/prospero-achievements/bridge/pa_windows_events.c` and
`port_station/templates/love_achievements.lua`; helper manifests associate
binaries with their sources. They contain no commercial game scripts.

Tested games are credited to their creators: Breath — Herbherth; The Coffin
of Andy and Leyley — Kit9 Studio; Kindergarten — Con Man Games; Intravenous
2: Mercenarism — Explosive Squat Games. Acquire commercial files from their
owners. No affiliation, endorsement or authorization by the creators is claimed.
