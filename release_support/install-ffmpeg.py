"""Optional, explicit download from the upstream binary distributor; no game data."""
from pathlib import Path
import hashlib,io,urllib.request,zipfile,json
R=Path(__file__).resolve().parents[1]
URL='https://github.com/GyanD/codexffmpeg/releases/download/2026-10-22-git-bf0e831606/ffmpeg-2026-10-22-git-bf0e831606-essentials_build.zip'
EXPECTED='966294d1e6c44e98c523f0c0e93d0c7f2a9c682d4b990621dd0b8aa7ab6228f3'
out=R/'tools/port-studio-audio/ffmpeg/ffmpeg.exe'
def sha(b):return hashlib.sha256(b).hexdigest()
if out.exists():
    if sha(out.read_bytes())!=EXPECTED:raise SystemExit('Existing FFmpeg differs; preserve it and review before replacing.')
    print('Pinned FFmpeg already installed.')
else:
    print('Downloading optional GPL FFmpeg directly from GyanD; source/version/license in tools/port-studio-audio/ffmpeg/README.txt',flush=True)
    req=urllib.request.Request(URL,headers={'User-Agent':'Port-Studio'})
    with urllib.request.urlopen(req,timeout=180)as f:data=f.read(250*1024*1024+1)
    if len(data)>250*1024*1024:raise SystemExit('Archive too large')
    with zipfile.ZipFile(io.BytesIO(data))as z:
        matches=[x for x in z.infolist()if x.filename.endswith('/bin/ffmpeg.exe')and x.file_size<200*1024*1024]
        if len(matches)!=1:raise SystemExit('Unexpected archive')
        binary=z.read(matches[0])
    if sha(binary)!=EXPECTED:raise SystemExit('Pinned binary SHA-256 mismatch; not installed')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(binary)
    print('Verified FFmpeg installed. Its absence was intentional in the public release.')
