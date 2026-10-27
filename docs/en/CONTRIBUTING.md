# Contributing

[Documentation](INDEX.md) · [Home](../../README.md)

Fixes, tested configurations and new adapters are welcome. See the README to
use the tool and [building](BUILDING.md) to develop it.

Compatibility reports should identify the game version, profile, executable,
arguments, controller mapping and tested scope. Distinguish reaching the menu
from a complete playthrough and explain how to reproduce failures.

For a new adapter, explain where events originate and test persistence,
duplicate-free replay, active-user handling and recovery after backend downtime.
The catalog editor does not replace integration of real gameplay conditions.

Before submitting a change, run relevant `port_station/tests`, JavaScript
regressions and, for service/SDK changes, the backend host tests. CI runs checks
that do not require games or the complete compilation kit.

Retain third-party licenses and credits. Examples must use user-supplied local
files; reports and contributions must not include games, saves or personal data.
