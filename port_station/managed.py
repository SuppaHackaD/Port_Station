"""Conservative Unity Mono integration, prepared outside the original game."""
import base64
import hashlib
import json
from pathlib import Path
import zlib
from .project import WORKSPACE as R, ProjectError, relative_file

TOOLS = R/'build/port-studio/managed'


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def prepare(project, game, output, run):
    game, output = Path(game), Path(output)
    tool = TOOLS/'ProsperoManagedIntegrator.exe'
    bridge = TOOLS/'ProsperoAchievements.dll'
    lock_path = TOOLS/'managed.lock.json'
    if not all(p.is_file() for p in (tool,bridge,lock_path)):
        raise ProjectError('Ponte Unity Mono ausente. Instale o kit com a ponte gerenciada ou compile sdk/prospero-achievements/managed.')
    lock=json.loads(lock_path.read_text(encoding='utf-8'))
    for p in (tool,bridge):
        if sha(p)!=lock['files'].get(p.name): raise ProjectError('Ponte gerenciada diverge do lock: '+p.name)
    folders=sorted(game.glob('*_Data/Managed'))
    if len(folders)!=1: raise ProjectError('Unity Mono: é necessário um único *_Data/Managed. IL2CPP não é suportado por este adaptador.')
    managed=folders[0]; source=managed/'Assembly-CSharp.dll'
    if not source.is_file(): raise ProjectError('Unity Mono: Assembly-CSharp.dll não encontrado.')
    relative=source.relative_to(game).as_posix();relative_file(relative)
    reserved={relative.casefold(), (managed.relative_to(game)/bridge.name).as_posix().casefold(),
              (managed.relative_to(game)/'ProsperoAchievements.config.tsv').as_posix().casefold()}
    if any(a['destination'].casefold() in reserved for a in project['overlays']):
        raise ProjectError('Um overlay conflita com os arquivos da ponte gerenciada.')
    output.mkdir(parents=True,exist_ok=False)
    # The integrator performs its own bounded signature/control-flow inspection.
    patched=output/'Assembly-CSharp.dll'
    before=sha(source)
    run([tool,source,bridge,patched,before])
    if sha(source)!=before: raise ProjectError('A assembly original mudou durante a preparação.')
    dll=output/bridge.name;dll.write_bytes(bridge.read_bytes())
    config=output/'ProsperoAchievements.config.tsv'
    rows=['PA_MANAGED_CONFIG_V1\t'+project['game_id']+'\n']
    for item in project['achievements']:
        source_id=item.get('source_id') or item['id']
        rows.append('MAP\t'+base64.b64encode(source_id.encode('utf-8')).decode('ascii')+'\t'+item['id']+'\n')
    config.write_text(''.join(rows),encoding='utf-8',newline='\n')
    files={ (managed.relative_to(game)/p.name).as_posix():p for p in (patched,dll,config) }
    receipt={'adapter':'unity-mono-steam','scope':'achievement-only-string-wrapper-v1',
             'original_sha256':before,'files':{rel:sha(p) for rel,p in files.items()},
             'console_validated':False,'original_game_modified':False}
    (output/'compatibility.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return files


def sync_rows(project, files):
    from .project import runtime_id
    prefix='prefixes/'+runtime_id(project)+'/drive_c/Games/'+runtime_id(project)+'/'
    rows=[]
    for relative,path in files.items():
        relative_file(relative)
        data=Path(path).read_bytes()
        if not data or len(data)>32*1024*1024: raise ProjectError('Arquivo da ponte fora do limite de 32 MiB.')
        rows.append((prefix+relative,len(data),zlib.crc32(data)))
    return rows
