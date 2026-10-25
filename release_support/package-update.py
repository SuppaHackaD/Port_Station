"""Create a program-only overlay from a known base tag; never includes user games."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile
R=Path(__file__).resolve().parents[1]

def package(base,output):
    if output.exists():raise ValueError('Output already exists')
    changes=subprocess.run(['git','diff','--name-only','--diff-filter=ACM',base,'HEAD'],cwd=R,check=True,capture_output=True,text=True).stdout.splitlines()
    entries={n:R/n for n in changes if (R/n).is_file()}
    if any(n.startswith(('local-games/','outputs/','build/port-studio/runtime-kit/'))or p.stat().st_size>8*1024**2 for n,p in entries.items()):raise ValueError('Unexpected update input')
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
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args();package(a.base,a.output)
