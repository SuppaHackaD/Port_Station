"""Seal the owned helper and export a standalone tool, never extracted game data."""
from pathlib import Path
import argparse,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent

def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def seal():
    exe=ROOT/'bin/AchievementScanner.exe'
    (exe.parent/'helper.lock.json').write_text(json.dumps({'version':'0.1.0','sha256':sha(exe)},indent=2)+'\n',encoding='utf-8')

def package(output,source_only=False):
    if output.exists():raise ValueError('Choose a new output ZIP')
    entries={}
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file() or any(x in ('bin','obj','__pycache__','.git')for x in rel.parts):continue
        entries['achievement_extractor/'+rel.as_posix()]=p
    if not source_only:
        for n in ['AchievementScanner.exe','helper.lock.json']:entries['achievement_extractor/bin/'+n]=ROOT/'bin'/n
        lock=json.loads((ROOT/'bin/helper.lock.json').read_text(encoding='utf-8'));assert sha(ROOT/'bin/AchievementScanner.exe')==lock['sha256']
    entries['LICENSE']=REPO/'LICENSE'
    entries['Achievement_Extractor.cmd']=ROOT/'launcher.cmd.in'
    entries['README.md']=ROOT/'README.md'
    for n in ['DOTNET-LICENSE.txt','DOTNET-ThirdPartyNotices.txt','Mono-Cecil-MIT.txt']:entries['LICENSES/'+n]=REPO/'LICENSES'/n
    for n,p in entries.items():
        if p.is_symlink() or p.is_junction():raise ValueError('Link in package')
        if n.endswith(('Assembly-CSharp.dll','Breath.exe','Game.exe')):raise ValueError('Unexpected game input')
    hashes={n:sha(p)for n,p in entries.items()}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=1)as z:
        for n,p in sorted(entries.items()):z.write(p,n)
        z.writestr('PACKAGE-MANIFEST.json',json.dumps({'version':'0.1.0','files':hashes,'game_data_included':False,'managed_binary_included':not source_only},indent=2)+'\n')
    with zipfile.ZipFile(output)as z:
        assert z.testzip()is None
        for n,h in hashes.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
    print(output,output.stat().st_size,sha(output))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seal-helper',action='store_true');p.add_argument('--source-only',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.seal_helper:seal()
    if a.output:package(a.output,a.source_only)
