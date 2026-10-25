"""Local-only archives. Never publish game files or send anything to the console."""
from pathlib import Path
import json
import zipfile
from .project import WORKSPACE as R, ProjectError, relative_file
from .builder import LOCK, check_lock, digest, tree

def toolkit(destination,log=print):
    destination=Path(destination).resolve()
    if destination.exists():raise ProjectError('O arquivo de destino já existe.')
    lock=check_lock(log);files={R/name for name in lock['files']}
    files.update(p for p in tree(R/'port_studio')if '__pycache__'not in p.parts)
    if (R/'port_station').is_dir():files.update(p for p in tree(R/'port_station')if '__pycache__'not in p.parts)
    files.update(p for p in tree(R/'tools/port-studio-audio'))
    files.update([R/'Port_Station.cmd',R/'PORT_STATION.md',LOCK,R/'scripts/build-port-studio-audio.py'])
    # Shared SDK build scripts expect these public sources / headers.
    files.update(p for p in tree(R/'src/prospero_achievements')if '__pycache__'not in p.parts)
    files.update(p for p in tree(R/'tools/PS5_Vulkan/tooling/native'))
    files.update([R/'tools/PS5_Vulkan/LICENSE',R/'scripts/build-prospero-achievements.py'])
    # Public releases carry the complete build support for preparing owned copies.
    # This marker is only present in an audited release tree, not private projects.
    public_release=R/'public-release.json'
    if public_release.is_file():
        for folder in ['release_support','docs','LICENSES','.github','tools/zlib-1.3.2']:
            files.update(p for p in tree(R/folder)if not any(x in p.relative_to(R/folder).parts for x in ('__pycache__','bin','obj','.git')))
        for name in ['README.md','LICENSE','NOTICE.md','THIRD_PARTY.md','SOURCES.json','public-release.json','requirements.txt','.gitignore','.gitattributes','scripts/build-native-tools.ps1','scripts/test-prospero-achievements.py']:
            files.add(R/name)
        for name in ['BreathPS5Bridge.dll','PatchBreathAchievements.exe']:
            files.add(R/'build/release-managed'/name)
        for name in ['prospero_achievements.elf','pa_stop.elf','pa_sdk_probe.elf']:
            files.add(R/'build/prospero-achievements/ps5'/name)
        files={p for p in files if p.relative_to(R).as_posix()not in ('tools/port-studio-audio/ffmpeg/ffmpeg.exe','tools/port-studio-audio/port-at9-encode.pdb')}
    entries={p.relative_to(R).as_posix():p for p in sorted(files)}
    if any('/Games/'in name or '/users/'in name or name.startswith(('handoff/','analysis/'))for name in entries):raise ProjectError('Toolkit contém caminho de dados pessoais/jogo inesperado.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    receipt={name:digest(path)for name,path in entries.items()}
    temporary=destination.with_name(destination.name+'.partial')
    if temporary.exists():raise ProjectError('Uma exportação parcial anterior existe; escolha outro destino.')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=1)as z:
        for i,(name,path)in enumerate(entries.items()):
            if digest(path)!=receipt[name]:raise ProjectError('Uma entrada mudou durante a exportação: '+name)
            info=zipfile.ZipInfo('Port_Station/'+name,(2026,1,1,0,0,0));info.create_system=3;info.external_attr=0o100755<<16;info.compress_type=zipfile.ZIP_DEFLATED;info.compress_level=1
            with path.open('rb')as src,z.open(info,'w',force_zip64=True)as dest:
                import shutil
                shutil.copyfileobj(src,dest,1024*1024)
            if i%1000==0:log(f'Exportando toolkit: {i}/{len(entries)}')
        z.writestr('Port_Station/toolkit-manifest.json',json.dumps({'schema':1,'files':receipt,'games_included':False,'python':'3.13 + Tk required; Wine/LLVM/public SDK/Pillow included'},indent=2))
    temporary.replace(destination);log('Toolkit local: '+str(destination));return destination
