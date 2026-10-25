"""Build the bundled Windows encoder from pinned GPL/MIT source; no network."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[1]
source=R/'port_studio/vendor/artswap_at9'
manifest=json.loads((source/'SOURCES.json').read_text())
for name,entry in manifest['files'].items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==entry['sha256'],name
out=R/'tools/port-studio-audio';out.mkdir(parents=True,exist_ok=True)
subprocess.run([str(R/'tools/zig-python/ziglang/zig.exe'),'cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-municode','-I'+str(source),str(R/'port_studio/templates/at9_host.c'),str(source/'at9.c'),str(source/'at9_tables.c'),'-o',str(out/'port-at9-encode.exe')],check=True)
files=[out/'port-at9-encode.exe',out/'ffmpeg/ffmpeg.exe',out/'ffmpeg/LICENSE',out/'ffmpeg/README.txt']
record={'schema':1,'encoder':manifest,'driver_sha256':hashlib.sha256((R/'port_studio/templates/at9_host.c').read_bytes()).hexdigest(),'ffmpeg_source':'https://github.com/FFmpeg/FFmpeg/commit/bf0e831606','ffmpeg_distribution':'https://www.gyan.dev/ffmpeg/builds/','files':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in files}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print('Built port-at9-encode.exe from pinned Art Swap source; FFmpeg pinned locally.')
