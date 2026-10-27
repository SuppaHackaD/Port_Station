"""Explicit source layout shared by release tooling; no per-game assumptions."""
from pathlib import Path
import os,shutil
SOURCE_DIRS=['port_station','achievement_extractor','docs','LICENSES','.github','release_support','sdk/ps5-game-port/cmake','sdk/ps5-game-port/runtime','sdk/prospero-achievements','src/prospero_achievements','src/tcoal/wine_title','src/tcoal/prospero_adapter','src/breath/wine_title','src/breath/prospero_adapter','build/prospero-evaluation/source-v020','tools/Lapy-breath-reference/source','tools/PS5_Vulkan/tooling/native','tools/zlib-1.3.2']
SOURCE_FILES=['README.md','PORT_STATION.md','Port_Station.cmd','CONTRIBUTING.md','NOTICE.md','THIRD_PARTY.md','SOURCES.json','LICENSE','public-release.json','requirements.txt','.gitignore','.gitattributes','src/native_runtime.c','sdk/ps5-game-port/host/package_title.py','scripts/build-native-tools.ps1','scripts/build-prospero-achievements.py','scripts/test-prospero-achievements.py','scripts/build-port-studio-audio.py','tools/Lapy-breath-reference/LICENSE','tools/PS5_Vulkan/LICENSE']
EXCLUDED={'__pycache__','bin','obj','.git'}
def source_path(name):
    return name in SOURCE_FILES or name.startswith('port_studio/') or any(name.startswith(d+'/')for d in SOURCE_DIRS)
def source_entries(root):
    root=Path(root);entries={}
    for rel in SOURCE_FILES:
        p=root/rel
        if p.is_file():entries[rel]=p
    for rel in SOURCE_DIRS:
        base=root/rel
        if not base.is_dir():continue
        for p in base.rglob('*'):
            if p.is_file()and not any(x in p.relative_to(base).parts for x in EXCLUDED):
                if p.is_symlink()or p.is_junction():raise ValueError('Source link is not supported: '+str(p))
                entries[p.relative_to(root).as_posix()]=p
    return entries
def copy_file(src,dest,link=False):
    src=Path(src);dest=Path(dest)
    if src.resolve()==dest.resolve():return
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():dest.unlink()
    if link:
        try:os.link(src,dest);return
        except OSError:pass
    shutil.copy2(src,dest)
