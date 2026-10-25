"""Make a private working copy from the purchaser's own game. No downloads."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R))
from port_station.builder import tree

def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def prepare(kind,source,output):
    source=source.resolve();output=output.resolve()
    if output.exists():raise ValueError('Output must be a new directory; existing files are preserved.')
    if output.is_relative_to(source)or source.is_relative_to(output):raise ValueError('Source and output must be separate trees.')
    required='Breath.exe'if kind=='breath'else'Game.exe'
    if not(source/required).is_file():raise ValueError('Missing '+required)
    files={p.relative_to(source).as_posix():sha(p)for p in tree(source)}
    if kind=='breath':
        original=source/'Breath_Data/Managed/Assembly-CSharp.dll'
        if sha(original)!='b98be2ab162e9f7f2ff4029b0bf8221db075df052d5782b96c73424c6ee95f18':raise ValueError('Unsupported Breath assembly. Original PC version 1.0.3 is required; do not use an already patched copy.')
        bridge=R/'build/release-managed/BreathPS5Bridge.dll'
        patcher=R/'build/release-managed/PatchBreathAchievements.exe'
        if not bridge.is_file()or not patcher.is_file():raise ValueError('Install the release kit or compile release_support/managed first.')
    shutil.copytree(source,output)
    changes=[]
    if kind=='breath':
        assembly=output/'Breath_Data/Managed/Assembly-CSharp.dll';new=assembly.with_suffix('.patched.dll')
        subprocess.run([str(patcher),str(assembly),str(bridge),str(new)],check=True)
        new.replace(assembly);shutil.copy2(bridge,assembly.parent/bridge.name)
        changes=['Breath_Data/Managed/Assembly-CSharp.dll','Breath_Data/Managed/BreathPS5Bridge.dll']
    else:
        # Only supplement missing labels using data from the purchaser's copy.
        data=output/'www/data/9c7050ae76645487'
        if data.is_file():
            native=json.loads(data.read_text(encoding='utf-8-sig')[8:]).get('labelLUT',{})
            for language in (output/'www/languages').glob('*/dialogue.txt'):
                raw=language.read_bytes();text=raw.decode('utf-8-sig')
                present=set(re.findall(r'^#([A-Za-z0-9]+)[ \t]*:',text,re.M))
                missing={k:v for k,v in native.items()if k not in present and isinstance(v,str)and v and '\n'not in v and '\r'not in v}
                if not missing:continue
                nl='\r\n'if b'\r\n'in raw else'\n'
                block=nl+'[CHOICES]'+nl
                for k,v in sorted(missing.items()):
                    if language.parent.name=='Portugues(Brasil)'and v=='Call again.':v='Ligar novamente.'
                    block+='#'+k+' : '+v+nl
                language.write_bytes(raw+block.encode('utf8'));changes.append(language.relative_to(output).as_posix())
    after={p.relative_to(source).as_posix():sha(p)for p in tree(source)}
    if after!=files:raise ValueError('Source changed during preparation. Do not distribute this output.')
    receipt={'game':kind,'private_output':True,'source_preserved':True,'changes':changes,'inputs':files}
    (output.parent/(output.name+'-preparation.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    print('Private game prepared:',output)
    print('Select this directory in the matching .ps5port.json recipe. Never commit it.')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('game',choices=['breath','tcoaal','tcoal']);ap.add_argument('--source',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args();prepare(a.game,a.source,a.output)
