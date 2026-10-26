"""Sync canonical source into an existing release staging tree."""
from pathlib import Path
import argparse,hashlib,json
from layout import source_entries,source_path,copy_file

def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def finalize(root):
    root=root.resolve();repo=root/'Port_Station';kit=root/'_staging/Port_Station'
    staged=json.loads((root/'staging.json').read_text(encoding='utf8'));entries=source_entries(repo)
    if 'port_station/builder.py'not in entries:raise ValueError('Missing canonical package')
    for rel,p in entries.items():copy_file(p,kit/rel)
    lock=json.loads((repo/'port_station/runtime.lock.json').read_text(encoding='utf8'));delta=[]
    managed_names=[]
    manifest=repo/'build/port-studio/managed/managed.lock.json'
    if manifest.is_file():
        declared=json.loads(manifest.read_text(encoding='utf8'))['files']
        expected={'ProsperoManagedIntegrator.exe','ProsperoAchievements.dll'}
        if set(declared)!=expected:raise ValueError('Unexpected managed bridge manifest')
        for name in sorted(expected):
            rel='build/port-studio/managed/'+name
            if sha(repo/rel)!=declared[name]:raise ValueError('Managed bridge differs from manifest')
            copy_file(repo/rel,kit/rel)
            managed_names.append(rel)
        rel='build/port-studio/managed/managed.lock.json'
        copy_file(manifest,kit/rel);managed_names.append(rel)
        for rel in managed_names:
            actual=sha(kit/rel);old=lock['files'].get(rel)
            if actual!=old:delta.append({'file':rel,'before':old,'after':actual});lock['files'][rel]=actual
    for rel,old in lock['files'].items():
        if rel not in entries and rel!='build/prospero-achievements/ps5/libprospero_achievements.a':continue
        actual=sha(kit/rel)
        if actual!=old:delta.append({'file':rel,'before':old,'after':actual});lock['files'][rel]=actual
    text=json.dumps(lock,indent=2)+'\n'
    for base in [repo,kit]:(base/'port_station/runtime.lock.json').write_text(text,encoding='utf8',newline='\n')
    names={n for n in staged['kit_files']if not source_path(n)}|set(entries)|set(managed_names)
    staged.update(version=json.loads((repo/'public-release.json').read_text())['version'],kit_files=sorted(names),source_files=sorted(entries))
    (root/'staging.json').write_text(json.dumps(staged,indent=2)+'\n',encoding='utf8')
    (root/'runtime-publication-delta.json').write_text(json.dumps({'changes':delta},indent=2)+'\n',encoding='utf8')
    print('Source synced; reviewed locked-source changes:',len(delta),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('deploy',type=Path);finalize(ap.parse_args().deploy)
