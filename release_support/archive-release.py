"""Archive and verify the explicit public deploy trees, never a private game build."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,zipfile

def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def files(root):
    return {p.relative_to(root).as_posix():p for p in root.rglob('*')if p.is_file()and '__pycache__'not in p.parts and '.git'not in p.parts}

def archive(dest,entries,prefix='',stored=False):
    if dest.exists():raise ValueError('Preserve existing release: '+str(dest))
    hashes={n:sha(p)for n,p in sorted(entries.items())}
    temporary=dest.with_suffix(dest.suffix+'.partial')
    if temporary.exists():raise ValueError('Partial archive exists; review it before continuing.')
    mode=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(temporary,'w',mode,compresslevel=None if stored else 1)as z:
        for i,(name,p)in enumerate(sorted(entries.items())):
            info=zipfile.ZipInfo(prefix+name,(2026,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=mode
            if not stored:info.compress_level=1
            with p.open('rb')as src,z.open(info,'w',force_zip64=True)as out:shutil.copyfileobj(src,out,1<<20)
            if i%2000==0:print(dest.name,'writing',i,'/',len(entries),flush=True)
        z.writestr(prefix+'RELEASE-MANIFEST.json',json.dumps({'schema':1,'files':hashes,'commercial_game_files_included':False},indent=2)+'\n')
    print('Verifying every decompressed entry:',dest.name,flush=True)
    with zipfile.ZipFile(temporary)as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate archive entry')
        for name,wanted in hashes.items():
            with z.open(prefix+name)as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            if actual!=wanted:raise ValueError('Archive differs: '+name)
    if temporary.stat().st_size>=2*1024**3:raise ValueError('Release file exceeds the selected 2 GiB asset limit; split before publication.')
    temporary.replace(dest)
    result={'file':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest),'entries':len(hashes),'all_entries_sha256_and_crc_verified':True}
    print(json.dumps(result),flush=True);return result

def main(root):
    root=root.resolve();repo=root/'Port_Station';kit=root/'_staging/Port_Station';out=root/'releases/0.3.1';out.mkdir(parents=True,exist_ok=True)
    staged=json.loads((root/'staging.json').read_text(encoding='utf8'))
    # Only entries listed before tests/compilations can enter the runtime archive.
    kitfiles={name:kit/name for name in staged['kit_files']}
    if any(n.startswith('port_studio/')or n=='docs/RELEASING.md' for n in kitfiles):raise ValueError('Obsolete package or maintainer guide in kit')
    if any(n.endswith(('Assembly-CSharp.dll','UnityPlayer.dll','Breath.exe','Game.exe','steam_api64.dll','steam_api.dll'))for n in kitfiles):raise ValueError('Commercial game filename detected')
    if any(n.endswith('/ffmpeg.exe')for n in kitfiles):raise ValueError('Optional external FFmpeg must not be redistributed here')
    sourcefiles=files(repo)
    if any(p.stat().st_size>90*1024**2 for p in sourcefiles.values()):raise ValueError('Oversized source file; use a release asset')
    results=[]
    results.append(archive(out/'Port_Station-0.3.1-source.zip',sourcefiles,'Port_Station/'))
    payload={n:kit/n for n in kitfiles if n.startswith(('src/prospero_achievements/','sdk/prospero-achievements/','build/prospero-achievements/ps5/','LICENSES/','docs/'))or n in ('scripts/build-prospero-achievements.py','scripts/test-prospero-achievements.py','LICENSE','NOTICE.md','THIRD_PARTY.md','README.md')}
    results.append(archive(out/'Prospero_Achievements-0.1.0-SDK-0.1.2.zip',payload,'Prospero_Achievements/'))
    old=root/'releases/upstream-sources.zip'
    if old.is_file()and (root/'releases/release.json').is_file():
        previous=json.loads((root/'releases/release.json').read_text(encoding='utf8'))
        item=next(x for x in previous['files']if x['file']=='upstream-sources.zip')
        if sha(old)!=item['sha256']or not item['all_entries_sha256_and_crc_verified']:raise ValueError('Previous upstream source archive differs')
        if (out/old.name).exists():raise ValueError('Preserve existing source archive')
        os.link(old,out/old.name);results.append(item)
    else:results.append(archive(out/'upstream-sources.zip',files(root/'_sources'),'upstream-sources/',stored=True))
    results.append(archive(out/'Port_Station-0.3.1-windows-kit.zip',kitfiles,'Port_Station/'))
    for update in sorted(out.glob('Port_Station-*-update-from-*.zip')):
        with zipfile.ZipFile(update)as z:
            if z.testzip()is not None:raise ValueError('Invalid update ZIP')
            count=len(z.namelist())
        results.append({'file':update.name,'bytes':update.stat().st_size,'sha256':sha(update),'entries':count,'all_entries_sha256_and_crc_verified':True})
    (out/'release.json').write_text(json.dumps({'schema':1,'version':'0.3.1','files':results,'games_included':False,'official_game_art_or_music_included':False,'ffmpeg_binary_included':False},indent=2)+'\n',encoding='utf8')
    (out/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['file']+'\n'for x in results),encoding='ascii')
    print('Release archives completed; no upload performed.',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('deploy',type=Path);main(ap.parse_args().deploy)
