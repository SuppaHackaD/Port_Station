"""Add an owned award publisher around one fingerprint-verified game module."""
from pathlib import Path
import copy,hashlib,json,re,zipfile
from .project import WORKSPACE,ProjectError

MODULE='game/steam.lua'
MODULE_SHA='46b25dec9908f58d233937c2faf34e7ff4a94263f1924f157e1ca9f4e4a06efe'
ORIGINAL='port_station/original_steam.luac'
PUBLISHER='port_station/achievements.lua'

def config(project):
    aliases={}
    for item in project['achievements']:
        source=item.get('source_id',item['id']);target=item['id']
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,63}',source) or '..'in source:
            raise ProjectError('A ponte LÖVE requer IDs de origem Steam ASCII com até64 caracteres: '+source)
        aliases[source]=target
    if not aliases:raise ProjectError('A ponte LÖVE precisa de um catálogo.')
    return {'gameId':project['game_id'],'aliases':aliases}

def lua_config(value):
    # Both ID namespaces are validated ASCII. JSON quoting matches Lua here.
    return '{gameId='+json.dumps(value['gameId'])+',aliases={'+','.join('['+json.dumps(k)+']='+json.dumps(v)for k,v in sorted(value['aliases'].items()))+'}}'

def wrapper(value):
    return ('''-- Port Station owned module adapter; original game bytes stay in the local build.
local function pack(...) return {n=select('#',...),...} end
local original=assert(love.filesystem.load("'''+ORIGINAL+'''"))
setfenv(original,getfenv(1))
local result=pack(original(...))
local ok,why=pcall(function()
  local publisher=assert(love.filesystem.load("'''+PUBLISHER+'''"))
  setfenv(publisher,getfenv(1))
  publisher()('''+lua_config(value)+''')
end)
if not ok then print("PA_LOVE adapter unavailable: "..tostring(why)) end
return unpack(result,1,result.n)
''').encode('utf-8')

def integrate(project,executable):
    value=config(project);path=Path(executable)
    publisher=(WORKSPACE/'port_station/templates/love_achievements.lua').read_bytes()
    with zipfile.ZipFile(path)as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ProjectError('ZIP do jogo com nomes duplicados.')
        original=z.read(MODULE)
        if hashlib.sha256(original).hexdigest()!=MODULE_SHA:raise ProjectError('Módulo de plataforma LÖVE diferente da revisão verificada.')
        if ORIGINAL in z.namelist()or PUBLISHER in z.namelist():raise ProjectError('O jogo já contém uma ponte; use os arquivos de origem.')
        entries={i.filename:(i.CRC,i.file_size,i.compress_size,i.header_offset)for i in z.infolist()}
        info=copy.copy(z.getinfo(MODULE))
    with zipfile.ZipFile(path,'a')as z:
        z.filelist=[x for x in z.filelist if x.filename!=MODULE];del z.NameToInfo[MODULE]
        z.writestr(info,wrapper(value))
        for name,b in ((ORIGINAL,original),(PUBLISHER,publisher)):
            entry=zipfile.ZipInfo(name,(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,b)
    with zipfile.ZipFile(path)as z:
        if len(z.namelist())!=len(set(z.namelist()))or z.testzip()is not None:raise ProjectError('Integridade ZIP da ponte LÖVE inválida.')
        for name,wanted in entries.items():
            if name==MODULE:continue
            i=z.getinfo(name)
            if (i.CRC,i.file_size,i.compress_size,i.header_offset)!=wanted:raise ProjectError('Outro recurso foi alterado ao instalar a ponte.')
        if z.read(ORIGINAL)!=original:raise ProjectError('Módulo original não foi preservado.')
    return {'kind':'love-platform-setachievement-v1','module':MODULE,'original_module_sha256':MODULE_SHA,'publisher_sha256':hashlib.sha256(publisher).hexdigest(),'mapped_ids':len(value['aliases']),'conditions_modified':False}
