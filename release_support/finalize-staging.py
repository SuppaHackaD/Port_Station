"""Synchronize reviewed publication support and freeze its explicit runtime baseline."""
from pathlib import Path
import argparse,hashlib,json,shutil
R=Path(__file__).resolve().parents[1]

def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():dst.unlink()
    shutil.copy2(src,dst)

def finalize(root):
    root=root.resolve();repo=root/'Port_Station';kit=root/'_staging/Port_Station'
    staged=json.loads((root/'staging.json').read_text(encoding='utf8'))
    if not(repo/'port_studio/examples/tcoal.ps5port.json').is_file():raise ValueError('Missing public staging')
    for p in (R/'release_support').rglob('*'):
        if p.is_file()and not any(x in p.relative_to(R/'release_support').parts for x in ('bin','obj','__pycache__','.git')):copy(p,repo/p.relative_to(R))
    copy(R/'port_studio/distribution.py',repo/'port_studio/distribution.py')
    for p in (R/'release_support/public').rglob('*'):
        if p.is_file():copy(p,repo/p.relative_to(R/'release_support/public'))
    (repo/'.gitattributes').write_text('* text=auto eol=lf\n*.png binary\n*.webp binary\n*.ttf binary\n*.otf binary\n*.at9 binary\n',encoding='utf8')
    (repo/'public-release.json').write_text(json.dumps({'schema':1,'name':'Port Station','version':'0.2.2','bundle_ffmpeg':False,'commercial_game_data':False},indent=2)+'\n',encoding='utf8')
    for p in repo.rglob('*'):
        if not p.is_file()or any(x in p.relative_to(repo).parts for x in ('__pycache__','.git')):continue
        data=p.read_bytes()
        if b'\0'not in data and b'\r\n'in data:p.write_bytes(data.replace(b'\r\n',b'\n'))
        copy(p,kit/p.relative_to(repo))
    lock=json.loads((repo/'port_studio/runtime.lock.json').read_text(encoding='utf8'));delta=[]
    for rel,old in lock['files'].items():
        # Other locked inputs remain the byte-verified hardlinks from initial staging.
        if not(repo/rel).is_file()and rel!='build/prospero-achievements/ps5/libprospero_achievements.a':continue
        actual=sha(kit/rel)
        if actual!=old:
            # First-party/public source or the SDK explicitly rebuilt in this tree.
            if not(repo/rel).is_file()and rel!='build/prospero-achievements/ps5/libprospero_achievements.a':raise ValueError('Unexpected binary change: '+rel)
            delta.append({'file':rel,'before':old,'after':actual})
            lock['files'][rel]=actual
    lock['publication_notes']='Reviewed public source canonicalized to LF for Git; toolkit SDK rebuilt from the same public source. FFmpeg is optional and excluded.'
    text=json.dumps(lock,indent=2)+'\n'
    for base in [repo,kit]:(base/'port_studio/runtime.lock.json').write_text(text,encoding='utf8')
    (root/'runtime-publication-delta.json').write_text(json.dumps({'schema':1,'changes':delta,'commercial_game_data_included':False},indent=2)+'\n',encoding='utf8')
    # Do not pick up fixtures or compiler intermediates created during validation.
    names=set(staged['kit_files'])
    names.update(p.relative_to(repo).as_posix()for p in repo.rglob('*')if p.is_file()and not any(x in p.relative_to(repo).parts for x in ('__pycache__','.git')))
    staged['kit_files']=sorted(names)
    (root/'staging.json').write_text(json.dumps(staged,indent=2)+'\n',encoding='utf8')
    print('Reviewed source synced; explicit baseline changes:',len(delta),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('deploy',type=Path);finalize(ap.parse_args().deploy)
