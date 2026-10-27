"""Create a program-only overlay from a known base tag; never includes user games."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile
R=Path(__file__).resolve().parents[1]

def package(base,output,kit=None):
    if output.exists():raise ValueError('Output already exists')
    changes=subprocess.run(['git','diff','--name-only','--diff-filter=ACM',base,'HEAD'],cwd=R,check=True,capture_output=True,text=True).stdout.splitlines()
    entries={n:R/n for n in changes if (R/n).is_file()}
    if any(n.startswith(('local-games/','outputs/','build/port-studio/runtime-kit/'))or p.stat().st_size>8*1024**2 for n,p in entries.items()):raise ValueError('Unexpected update input')
    current=json.loads((R/'port_station/runtime.lock.json').read_text(encoding='utf8'))['files']
    old=json.loads(subprocess.check_output(['git','show',base+':port_station/runtime.lock.json'],cwd=R,text=True,encoding='utf8'))['files']
    for name,wanted in current.items():
        if old.get(name)==wanted or name in entries:continue
        compiled={'build/release-managed/PatchBreathAchievements.exe',
                  'build/port-studio/managed/ProsperoManagedIntegrator.exe',
                  'build/port-studio/managed/ProsperoAchievements.dll',
                  'build/port-studio/managed/managed.lock.json',
                  'achievement_extractor/bin/AchievementScanner.exe',
                  'achievement_extractor/bin/helper.lock.json'}
        compiled.update({'build/port-studio/compat/pe64/paenv.dll','build/port-studio/compat/pe64/paevents.dll','build/port-studio/compat/pe64/helper.json'})
        compiled.add('build/prospero-evaluation/staged/PPSA99995/mesa-zink-manifest.json')
        compiled.update('build/prospero-evaluation/staged/PPSA99995/win/mesa-zink/'+arch+'/'+dll
                        for arch in ('i386-windows','x86_64-windows')
                        for dll in ('opengl32.dll','libgallium_wgl.dll'))
        if name not in compiled or kit is None:raise ValueError('Changed runtime input requires an explicit update source: '+name)
        path=kit/name
        if path.stat().st_size>160*1024**2 or hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:raise ValueError('Compiled preparation tool differs from lock')
        entries[name]=path
    manifest={'base_tag':base,'files':{n:hashlib.sha256(p.read_bytes()).hexdigest()for n,p in entries.items()},'games_included':False,'user_projects_included':False}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=1)as z:
        for n,p in sorted(entries.items()):z.write(p,'Port_Station/'+n)
        z.writestr('UPDATE.json',json.dumps(manifest,indent=2)+'\n')
        z.writestr('ATUALIZAR.txt','Para um kit '+base+' existente: feche Port Station. Copie o conteúdo de Port_Station/ deste ZIP para a pasta do kit, substituindo os arquivos de programa. Reabra Port_Station.cmd. Projetos e arquivos dos jogos não fazem parte deste update. Para uma instalação nova, use o Windows kit completo.\n')
    with zipfile.ZipFile(output)as z:
        assert z.testzip()is None
        for n,h in manifest['files'].items():assert hashlib.sha256(z.read('Port_Station/'+n)).hexdigest()==h
    print('Verified program-only update:',output,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--output',required=True,type=Path);p.add_argument('--kit',type=Path);a=p.parse_args();package(a.base,a.output,a.kit)
