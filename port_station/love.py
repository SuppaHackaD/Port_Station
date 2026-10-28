"""Fingerprint-gated LÖVE preparation, applied only to generated build copies."""
from pathlib import Path
import copy,hashlib,json,shutil,struct,subprocess,tempfile,zipfile,zlib
from .project import WORKSPACE,ProjectError,relative_file,runtime_id

ENGINE='c8dbd4082621a925befa13dfc8328d05feb04ddb6b1be9b1962fd8c01e4d7dd3'
ENGINE_FIXED='39c8ef0714033ccc6a6d8ad5c4be3c7048d34ab97c1268f0d2d1a625d38b1c55'
GAME='ce9742aa4f87fdc235d712e0afaf8909095efe76d0a4fc4a8162ad0739d8a0bf'
GAME_FIXED='b76dbc1ac361c22470220a8d44ca04ad2d4f41236566bf158f4b8818d6891b2c'
MEMBER='engine/joystick_handler.lua'
CHUNK='bc9c85a85367c5c488f9191251c8d85d03aba130d46ccc2d0b6df25b89af6ccc'
CHUNK_FIXED='226c65bd31357349c9d0d5dd4f8a2cc64799cb7e1477cca8c76fb5c8b095f218'
HELPER=WORKSPACE/'build/port-studio/compat/pe64/paenv.dll'

def digest(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def inspect(project,game):
    directory=Path(project['executable']).parent
    matches=[p for p in (Path(game)/directory).iterdir()if p.name.casefold()=='love.dll'and p.is_file()] if (Path(game)/directory).is_dir()else []
    if len(matches)!=1:return None
    path=matches[0];engine=directory/path.name
    value=digest(path)
    if value not in (ENGINE,ENGINE_FIXED):return None
    if project['profile']!='opengl-xinput':
        raise ProjectError('Esta versão de LÖVE usa OpenGL. Selecione o perfil opengl-xinput para gerar o port.')
    return {'engine':engine.as_posix(),'engine_sha256':value,'executable':project['executable']}

def engine_bytes(data):
    value=hashlib.sha256(data).hexdigest()
    if value==ENGINE_FIXED:return data
    if value!=ENGINE:raise ProjectError('A DLL LÖVE mudou depois da inspeção.')
    needle=b'userenv.dll\0';replacement=b'paenv.dll\0'.ljust(len(needle),b'\0')
    if data.count(needle)!=1:raise ProjectError('Consulta de perfil LÖVE diferente da versão verificada.')
    result=data.replace(needle,replacement)
    if hashlib.sha256(result).hexdigest()!=ENGINE_FIXED:raise ProjectError('Verificação da DLL LÖVE preparada falhou.')
    return result

def uleb(value):
    out=bytearray()
    while value>=128:out.append((value&127)|128);value>>=7
    out.append(value);return bytes(out)

def controller_chunk(data):
    """Fix only the known dump's fallback; no game bytecode is distributed here."""
    if hashlib.sha256(data).hexdigest()!=CHUNK:raise ProjectError('Bytecode do controle diferente da revisão verificada.')
    body=bytearray(data[13:334])
    if len(body)!=321 or struct.unpack_from('<I',body,63)[0]!=0x1042b or body[4]!=5:
        raise ProjectError('Layout do controle diferente da revisão verificada.')
    struct.pack_into('<I',body,63,0x50433)
    body[145:145]=b'\x01\x03\x00\x00\x09xbox\x09xbox'
    body[4]=6
    result=data[:11]+uleb(len(body))+body+data[334:]
    if hashlib.sha256(result).hexdigest()!=CHUNK_FIXED:raise ProjectError('Verificação do controle preparado falhou.')
    return result

def prepare(plan,game,out,helper=HELPER,project=None):
    game=Path(game);out=Path(out);out.mkdir(parents=True,exist_ok=True);helper=Path(helper)
    if not helper.is_file():raise ProjectError('Helper LÖVE ausente: aplique o update completo do Port Station.')
    try:metadata=json.loads(helper.with_name('helper.json').read_text(encoding='utf-8'))
    except (OSError,ValueError)as e:raise ProjectError('Manifesto do helper LÖVE ausente ou inválido.')from e
    if metadata.get('architecture')!='pe64' or metadata.get('dll_sha256')!=digest(helper) or metadata.get('source_sha256')!=digest(WORKSPACE/'port_station/native_compat/paenv.c'):
        raise ProjectError('O helper LÖVE diverge do fonte ou do manifesto verificado.')
    files={};engine=relative_file(plan['engine']);dest=out/engine;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(engine_bytes((game/engine).read_bytes()));files[engine.as_posix()]=dest
    siblings=[p for p in (game/engine.parent).iterdir()if p.name.casefold()=='paenv.dll']
    shim=engine.parent/(siblings[0].name if siblings else 'paenv.dll')
    if (game/shim).exists() and digest(game/shim)!=digest(helper):raise ProjectError('paenv.dll existente conflita com o helper LÖVE.')
    dest=out/shim;shutil.copy2(helper,dest);files[shim.as_posix()]=dest
    exe=relative_file(plan['executable']);source=game/exe;original=digest(source)
    if original==GAME:
        target=out/exe;target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(source)as z:
            if len(z.namelist())!=len(set(z.namelist())):raise ProjectError('ZIP do jogo contém nomes duplicados.')
            info=copy.copy(z.getinfo(MEMBER));fixed=controller_chunk(z.read(MEMBER))
        shutil.copyfile(source,target)
        with zipfile.ZipFile(target,'a')as z:
            z.filelist=[x for x in z.filelist if x.filename!=MEMBER];del z.NameToInfo[MEMBER];z.writestr(info,fixed)
        with zipfile.ZipFile(source)as src,zipfile.ZipFile(target)as dst:
            if len(dst.namelist())!=len(set(dst.namelist())) or set(src.namelist())!=set(dst.namelist()):raise ProjectError('Inventário ZIP alterado.')
            for entry in src.infolist():
                other=dst.getinfo(entry.filename)
                if entry.filename!=MEMBER and (entry.CRC,entry.file_size,entry.compress_size,entry.header_offset)!=(other.CRC,other.file_size,other.compress_size,other.header_offset):raise ProjectError('Outro membro do jogo foi alterado.')
            if dst.testzip()is not None:raise ProjectError('CRC do jogo preparado inválido.')
        if digest(target)!=GAME_FIXED:raise ProjectError('Executável preparado diverge da revisão verificada.')
        files[exe.as_posix()]=target
    elif original==GAME_FIXED:
        dest=out/exe;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);files[exe.as_posix()]=dest
    producer=None
    if project and project['adapter']=='file-v1'and original in (GAME,GAME_FIXED):
        event_helper=helper.with_name('paevents.dll')
        if not event_helper.is_file()or metadata.get('events_dll_sha256')!=digest(event_helper)or metadata.get('events_source_sha256')!=digest(WORKSPACE/'sdk/prospero-achievements/bridge/pa_windows_events.c'):
            raise ProjectError('Helper de eventos LÖVE ausente ou divergente: aplique o update completo.')
        from .love_achievements import integrate
        producer=integrate(project,files[exe.as_posix()])
        relative=engine.parent/'paevents.dll';dest=out/relative;shutil.copy2(event_helper,dest);files[relative.as_posix()]=dest
        if (game/relative).exists()and digest(game/relative)!=digest(event_helper):raise ProjectError('paevents.dll existente conflita com o publicador.')
    if digest(game/engine)!=plan['engine_sha256'] or digest(source)!=original:raise ProjectError('Os arquivos de origem mudaram durante a preparação.')
    return files,{'engine':'LOVE11.4-pe64','source_engine_sha256':plan['engine_sha256'],'prepared_engine_sha256':ENGINE_FIXED,'helper_sha256':digest(helper),'controller_repair':original in (GAME,GAME_FIXED),'achievement_producer':producer,'files':{n:digest(p)for n,p in files.items()},'source_modified':False}

def sync_rows(project,files):
    prefix='prefixes/'+runtime_id(project)+'/drive_c/Games/'+runtime_id(project)+'/'
    rows=[];hashes={}
    for name,path in sorted(files.items()):
        relative_file(name);crc=0;size=0;sha=hashlib.sha256()
        with Path(path).open('rb')as f:
            for b in iter(lambda:f.read(1024*1024),b''):crc=zlib.crc32(b,crc);size+=len(b);sha.update(b)
        if not 0<size<=512*1024*1024:raise ProjectError('Arquivo de compatibilidade fora do limite.')
        rows.append((prefix+name,size,crc));hashes[name]=sha.hexdigest()
    stamp=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    return rows,stamp

def build_helper():
    source=WORKSPACE/'port_station/native_compat/paenv.c';HELPER.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='station-love-helper-')as td:
        output=Path(td)/'paenv.dll'
        subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-target','x86_64-windows-gnu','-shared','-O2','-Wall','-Wextra','-Werror',str(source),'-ladvapi32','-o',str(output)],check=True)
        shutil.copy2(output,HELPER)
    events=WORKSPACE/'sdk/prospero-achievements/bridge/pa_windows_events.c'
    with tempfile.TemporaryDirectory(prefix='station-event-helper-')as td:
        output=Path(td)/'paevents.dll'
        subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-target','x86_64-windows-gnu','-shared','-O2','-Wall','-Wextra','-Werror',str(events),'-o',str(output)],check=True)
        shutil.copy2(output,HELPER.with_name('paevents.dll'))
    (HELPER.parent/'helper.json').write_text(json.dumps({'architecture':'pe64','source_sha256':digest(source),'dll_sha256':digest(HELPER),'events_source_sha256':digest(events),'events_dll_sha256':digest(HELPER.with_name('paevents.dll'))},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':build_helper()
