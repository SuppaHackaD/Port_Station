"""Prepare a source tree and runtime kit from an installed Port Station kit."""
from pathlib import Path
import argparse,json,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from port_station import __version__
from port_station.builder import check_lock,tree
from layout import source_entries,copy_file

def stage(output):
    output=output.resolve();repo=output/'Port_Station';kit=output/'_staging/Port_Station'
    if repo.exists()or kit.exists():raise ValueError('Choose a new staging destination.')
    if not(R/'public-release.json').is_file():raise ValueError('Start from an installed Port Station kit.')
    lock=check_lock();repo.mkdir(parents=True);kit.mkdir(parents=True)
    optional={'tools/port-studio-audio/ffmpeg/ffmpeg.exe','tools/port-studio-audio/port-at9-encode.pdb'}
    for rel in lock['files']:
        if rel not in optional:copy_file(R/rel,kit/rel,link=True)
    entries=source_entries(R)
    for rel,p in entries.items():copy_file(p,repo/rel);copy_file(p,kit/rel)
    for p in tree(R/'tools/port-studio-audio'):
        rel=p.relative_to(R).as_posix()
        if rel not in optional:copy_file(p,kit/rel,link=True)
    for name in ['BreathPS5Bridge.dll','PatchBreathAchievements.exe']:copy_file(R/'build/release-managed'/name,kit/'build/release-managed'/name)
    for name in ['prospero_achievements.elf','pa_stop.elf','pa_sdk_probe.elf','libprospero_achievements.a']:copy_file(R/'build/prospero-achievements/ps5'/name,kit/'build/prospero-achievements/ps5'/name)
    for name in ['build/prospero-achievements/build.json']:
        if (R/name).exists():copy_file(R/name,kit/name)
    for p in (R/'build/prospero-achievements/host').glob('*.exe'):copy_file(p,kit/p.relative_to(R))
    names=sorted(p.relative_to(kit).as_posix()for p in tree(kit)if '__pycache__'not in p.parts)
    (output/'releases').mkdir(exist_ok=True)
    (output/'staging.json').write_text(json.dumps({'version':__version__,'repository':str(repo),'kit_staging':str(kit),'kit_files':names,'games_included':False,'source_files':sorted(entries)},indent=2)+'\n',encoding='utf8')
    print('Staged source and kit:',output,flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('output',type=Path);stage(ap.parse_args().output)
