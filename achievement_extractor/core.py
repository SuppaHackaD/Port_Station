"""Local scan, evidence merge and Port Station JSON export. Standard library only."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
from . import __version__
from .official import FALLBACK,confirmed_ids
from .love import archive_members,luajit_strings
from .unity import il2cpp_literals,serialized_candidates
import zipfile
from .formats import read_metadata, definitions, localized, javascript_calls, native_candidates

HERE = Path(__file__).resolve().parent
MAX_FILE = 8*1024*1024
MAX_TOTAL = 128*1024*1024
MAX_FILES = 12000
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z')


class ExtractionError(ValueError): pass


def digest(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def validate_input(folder, executable):
    root = Path(folder).resolve()
    exe = Path(executable)
    exe = (root/exe).resolve() if not exe.is_absolute() else exe.resolve()
    if not root.is_dir() or not exe.is_file() or not exe.is_relative_to(root):
        raise ExtractionError('Selecione a pasta do jogo e um .exe dentro dela.')
    if exe.suffix.lower()!='.exe': raise ExtractionError('Selecione um executável Windows .exe.')
    with exe.open('rb') as f:
        b=f.read(64)
        if len(b)<64 or b[:2]!=b'MZ': raise ExtractionError('Executável sem cabeçalho PE Windows.')
        f.seek(struct.unpack_from('<I',b,60)[0]);header=f.read(6)
    if len(header)!=6 or header[:4]!=b'PE\0\0': raise ExtractionError('Cabeçalho PE inválido.')
    return root,exe


def managed_pe(path):
    try:
        with Path(path).open('rb') as f:
            b=f.read(64)
            if len(b)<64 or b[:2]!=b'MZ':return False
            f.seek(struct.unpack_from('<I',b,60)[0]+24);header=f.read(240)
        magic=struct.unpack_from('<H',header,0)[0];offset=112 if magic==0x20b else 96 if magic==0x10b else -1
        return offset>=0 and len(header)>=offset+15*8 and struct.unpack_from('<II',header,offset+14*8)[0]!=0
    except (OSError,struct.error):return False


def scan(folder, executable, language='brazilian', metadata=None, log=lambda _:None, cancel=None):
    root,exe=validate_input(folder,executable)
    result={'_source_root':str(root),'extractor_version':__version__,'executable':exe.relative_to(root).as_posix(),'executable_sha256':digest(exe),
            'language':language,'entries':[],'warnings':[],'inputs':{},'constant_candidates':{},'coverage':{'files_seen':0,'bytes_read':0,'parse_failures':0,'unresolved_managed_calls':0,'bounded_scan':True,'truncated':False,'luajit_members':0}}
    entries={};assemblies=[exe] if managed_pe(exe) else [];paths=[]
    def warn(s):result['warnings'].append(s);log(s)
    def label(path):
        return path.relative_to(root).as_posix() if path.is_relative_to(root) else 'external/'+path.name
    def add(source, kind, path, title='', description='', hidden=None, icon='', **location):
        if not isinstance(source,str) or not source or len(source.encode('utf-8'))>256 or any(ord(c)<32 for c in source): return
        rank=3 if kind=='catalog' else 1 if kind in ('native-candidate','luajit-constant','il2cpp-literal','unity-serialized-candidate') else 2
        evidence={'kind':kind,'file':label(path),**location}
        record=entries.setdefault(source,{'source_id':source,'title':'','description':'','hidden':None,'icon':'','evidence':[],'rank':0,'conflicts':[]})
        record['evidence'].append(evidence)
        for key,value in [('title',title),('description',description),('hidden',hidden),('icon',icon)]:
            if value is None or value=='':continue
            if record[key] not in (None,'') and record[key]!=value and rank==record['rank']:
                record['conflicts'].append(key)
            if record[key] in (None,'') or rank>record['rank']:record[key]=value
        record['rank']=max(rank,record['rank'])
    def lua(data,path,member=None):
        if not data.startswith(b'\x1bLJ'):return
        constants=luajit_strings(data);result['coverage']['luajit_members']+=1
        for source,offset in constants:
            pool=result['constant_candidates']
            if source not in pool and len(pool)>=65536:result['coverage']['truncated']=True;continue
            evidence={'kind':'luajit-constant','file':label(path),'offset':offset}
            if member:evidence['member']=member
            origins=pool.setdefault(source,[])
            if len(origins)<2:origins.append(evidence)
            if 'achiev'in (member or path.name).lower() and re.fullmatch('[A-Z][A-Z0-9_]{2,63}',source):
                add(source,'luajit-constant',path,offset=offset,**({'member':member}if member else{}))
    for base,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted((d for d in dirs if d.lower() not in ('.git','node_modules','cache','logs','saves','save','userdata','__pycache__') and not (Path(base)/d).is_symlink() and not (Path(base)/d).is_junction()),
                       key=lambda d:(d.casefold()!=(exe.stem+'_Data').casefold(),d.casefold()))
        for name in sorted(files):
            path=Path(base)/name;result['coverage']['files_seen']+=1
            if result['coverage']['files_seen']>MAX_FILES:
                result['coverage']['truncated']=True;warn('Limite de arquivos atingido; busca parcial.');break
            if path.is_symlink() or not path.resolve().is_relative_to(root): continue
            paths.append(path)
        if result['coverage']['truncated']:break
    if metadata:
        extra=Path(metadata).resolve()
        if not extra.is_file():raise ExtractionError('Arquivo extra de metadados não encontrado.')
        if extra not in paths:paths.insert(0,extra)
    # A large ancillary content folder must not starve the executable's
    # metadata; prioritize IL2CPP tables before large serialized assets.
    paths.sort(key=lambda p:(0 if p.name.lower()=='global-metadata.dat' else 1 if p.name.lower()=='resources.assets' else 2,str(p)))
    for path in paths:
        if cancel and cancel.is_set(): raise ExtractionError('Extração cancelada.')
        suffix=path.suffix.lower();name=path.name.lower()
        if name=='global-metadata.dat' and path.parent.name.lower()=='metadata':
            size=path.stat().st_size
            if size>MAX_FILE or result['coverage']['bytes_read']+size>MAX_TOTAL:
                result['coverage']['truncated']=True;warn('Limite de leitura IL2CPP: '+label(path));continue
            data=path.read_bytes();result['coverage']['bytes_read']+=len(data)
            result['inputs'][label(path)]=hashlib.sha256(data).hexdigest()
            try:
                # Complete parsing first: do not retain candidates from malformed metadata.
                for source,offset,index in list(il2cpp_literals(data)):
                    pool=result['constant_candidates']
                    if source not in pool and len(pool)>=65536:result['coverage']['truncated']=True;continue
                    evidence={'kind':'il2cpp-literal','file':label(path),'offset':offset,'index':index}
                    origins=pool.setdefault(source,[])
                    if len(origins)<2:origins.append(evidence)
                    if re.match(r'^(?:ACHI_|ACH_|ACHIEVEMENT_|ACHV_|TROPHY_)',source):
                        add(source,'il2cpp-literal',path,offset=offset,index=index)
                warn('IL2CPP: constantes recuperadas; não comprovam chamadas de desbloqueio. Cruze as IDs oficiais e revise a ponte separadamente.')
            except (ValueError,UnicodeError,struct.error) as error:
                result['coverage']['parse_failures']+=1;warn(label(path)+': '+str(error))
            continue
        if suffix=='.assets' and path.parent.name.lower().endswith('_data'):
            remaining=MAX_TOTAL-result['coverage']['bytes_read'];size=path.stat().st_size
            if remaining<48:result['coverage']['truncated']=True;continue
            with path.open('rb')as stream:
                for source,offset in serialized_candidates(stream,size,max_bytes=remaining):
                    add(source,'unity-serialized-candidate',path,offset=offset)
                read=stream.tell()
            result['coverage']['bytes_read']+=read
            if read<size:result['coverage']['truncated']=True
            if read>48:result['inputs'][label(path)]=digest(path)
            continue
        if suffix=='.dll' and path.parent.name.lower()=='managed' and not name.startswith(('system','unity','mono','mscorlib','netstandard','microsoft.')):
            if path.stat().st_size<=32*1024*1024:assemblies.append(path)
        is_meta=suffix in ('.json','.vdf') or suffix=='.bin' and ('schema' in name or 'achiev' in name) or metadata and path==Path(metadata).resolve()
        is_js=suffix in ('.js','.cjs','.mjs')
        is_lua=suffix=='.lua'
        if not is_meta and not is_js and not is_lua:continue
        size=path.stat().st_size
        if size>MAX_FILE or result['coverage']['bytes_read']+size>MAX_TOTAL:
            result['coverage']['truncated']=True;warn('Limite de leitura: '+label(path));continue
        data=path.read_bytes();result['coverage']['bytes_read']+=len(data)
        result['inputs'][label(path)]=hashlib.sha256(data).hexdigest()
        try:
            if is_lua:lua(data,path)
            if is_meta:
                value=read_metadata(data,suffix=='.bin')
                context='achiev' in name or bool(metadata and path==Path(metadata).resolve())
                for row in definitions(value,context):
                    source=next((row[k] for k in ('source_id','api_name','apiName','id','name') if k in row and row[k] is not None),'')
                    source=str(source) if isinstance(source,(str,int)) and not isinstance(source,bool) else ''
                    title,title_lang=localized(row.get('title',row.get('displayName','')),language)
                    desc,desc_lang=localized(row.get('description',row.get('desc','')),language)
                    hidden=row.get('hidden');hidden=None if hidden is None else str(hidden).lower() in ('true','1')
                    icon=row.get('icon','');icon_path=''
                    if isinstance(icon,str) and icon:
                        if '://' in icon:warn('Ícone remoto não baixado: '+source)
                        elif not any(x in icon for x in (':','\\')) and not icon.startswith('/') and '..' not in Path(icon).parts:
                            p=(path.parent/icon).resolve()
                            if p.is_relative_to(root) or p.is_relative_to(path.parent) and not path.is_relative_to(root):
                                if p.is_file():icon_path=str(p)
                    add(source,'catalog',path,title,desc,hidden,icon_path,title_language=title_lang,description_language=desc_lang)
            if is_js:
                for source,offset in javascript_calls(data.decode('utf-8-sig')):add(source,'javascript-api-literal',path,offset=offset)
        except (ValueError,UnicodeError,RecursionError,OverflowError) as error:
            result['coverage']['parse_failures']+=1
            if is_lua:result['coverage']['truncated']=True
            if is_lua or is_js or is_meta and ('achiev' in name or suffix in ('.vdf','.bin') or metadata and path==Path(metadata).resolve()):warn(label(path)+': '+str(error))
    carriers=[exe]+[p for p in paths if p.suffix.lower()=='.love' and p!=exe]
    for carrier in carriers[:8]:
        if cancel and cancel.is_set():raise ExtractionError('Extração cancelada.')
        try:
            for member,data in archive_members(carrier,max_entries=MAX_FILES,max_total=max(0,MAX_TOTAL-result['coverage']['bytes_read'])):
                if cancel and cancel.is_set():raise ExtractionError('Extração cancelada.')
                result['coverage']['bytes_read']+=len(data)
                result['inputs'][label(carrier)+'!/'+member]=hashlib.sha256(data).hexdigest()
                suffix=Path(member).suffix.lower()
                if suffix=='.lua':lua(data,carrier,member)
                elif suffix in ('.js','.cjs','.mjs'):
                    for source,offset in javascript_calls(data.decode('utf-8-sig')):
                        add(source,'javascript-api-literal',carrier,member=member,offset=offset)
                elif suffix in ('.json','.vdf'):
                    for row in definitions(read_metadata(data),'achiev'in member.lower()):
                        source=next((row[k]for k in ('source_id','api_name','apiName','id','name')if row.get(k)is not None),'')
                        title,lang=localized(row.get('title',row.get('displayName','')),language)
                        desc,dlang=localized(row.get('description',row.get('desc','')),language)
                        add(source,'catalog',carrier,title,desc,member=member,title_language=lang,description_language=dlang)
            if carrier!=exe:result['inputs'][label(carrier)]=digest(carrier)
        except ExtractionError:raise
        except (ValueError,UnicodeError,zipfile.BadZipFile,NotImplementedError) as error:
            result['coverage']['parse_failures']+=1;result['coverage']['truncated']=True;warn(label(carrier)+': '+str(error))
    helper=HERE/'bin/AchievementScanner.exe';lock=HERE/'bin/helper.lock.json'
    if assemblies:
        log('Analisando metadados gerenciados…')
        if helper.is_file() and lock.is_file():
            expected=json.loads(lock.read_text(encoding='utf-8'))['sha256']
            if digest(helper)!=expected:raise ExtractionError('O scanner gerenciado diverge do hash do pacote. Reinstale ou recompile a ferramenta.')
            selected=sorted(assemblies,key=lambda p:(not p.name.startswith('Assembly-CSharp'),str(p)))[:32]
            if len(assemblies)>32:result['coverage']['truncated']=True
            try:
                completed=subprocess.run([str(helper),*map(str,selected)],capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if completed.returncode:raise ExtractionError('Scanner gerenciado falhou: '+completed.stderr.decode('utf-8','replace')[:800])
                managed=json.loads(completed.stdout)
                result['coverage']['unresolved_managed_calls']=managed['unresolved_calls']
                result['coverage']['truncated']|=managed['truncated']
                for row in managed['rows']:
                    path=Path(row['path']).resolve()
                    if path not in selected:raise ExtractionError('Scanner retornou uma origem inesperada.')
                    result['inputs'][label(path)]=digest(path)
                    add(row['id'],row['kind'],path,method=row['method'],token=row['token'],il_offset=row['il_offset'])
                for error in managed['errors']:warn(label(Path(error['path']))+': '+error['error'])
            except subprocess.TimeoutExpired:warn('Tempo limite do scanner gerenciado; extração parcial.');result['coverage']['truncated']=True
        else:warn('Scanner gerenciado ausente. Use o pacote Windows ou compile managed/Scanner.csproj.');result['coverage']['truncated']=True
    # Native strings have no proven call relationship: review-only, never selected by default.
    from .formats import native_candidate_stream
    with exe.open('rb')as stream:
        for source,offset in native_candidate_stream(stream):add(source,'native-candidate',exe,offset=offset)
    if exe.stat().st_size>512*1024*1024:warn('Busca nativa limitada aos primeiros 512 MiB.');result['coverage']['truncated']=True
    for source,row in sorted(entries.items()):
        missing=[key for key in ('title','description','hidden','icon') if row[key] in ('',None)]
        row['review']=sorted(set(missing+['conflict:'+k for k in row['conflicts']]))
        row['selected']=row['rank']>=2
        row['title']=row['title'] or source;row['hidden']=bool(row['hidden'])
        result['entries'].append(row)
    if not entries and result['constant_candidates']:warn('Constantes recuperadas. Consulte o AppID Steam para cruzar as IDs oficiais; constantes não comprovam chamadas de desbloqueio.')
    elif not entries:warn('Nenhuma definição recuperada nas fontes suportadas. Forneça um schema local adicional ou revise a integração manualmente.')
    elif not any(row['rank']==3 for row in entries.values()):warn('IDs extraídas do código; nomes, descrições e ícones podem não estar presentes. Revise os campos marcados.')
    log(f'{len(result["entries"])} IDs encontradas; {sum(r["selected"] for r in result["entries"])} selecionadas por padrão.')
    return result


def canonical_id(source,reserved,used):
    if ID.fullmatch(source) and '..' not in source and source not in used:return source
    base=re.sub(r'[^A-Za-z0-9_-]+','_',source).strip('_-')[:48] or 'ACH'
    number=0
    while True:
        suffix=hashlib.sha256((source+'\0'+str(number)).encode('utf-8')).hexdigest()[:12]
        candidate=base+'_'+suffix
        if candidate not in reserved and candidate not in used:return candidate
        number+=1


def _new_destination(result, path):
    dest=Path(path).resolve()
    if result.get('_source_root') and dest.is_relative_to(Path(result['_source_root'])):raise ExtractionError('A saída deve ficar fora da pasta do jogo.')
    if dest.exists():raise ExtractionError('Escolha uma pasta de saída nova.')
    return dest


def write_report(result,dest):
    path=dest/'extraction-report.json'
    path.write_text(json.dumps({k:v for k,v in result.items() if not k.startswith('_')},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return path


def save_report(result, path):
    dest=_new_destination(result,path);dest.mkdir(parents=True)
    return write_report(result,dest)


def export(result, destination, official_only=False, steam_app_id=None):
    selected=[r for r in result['entries'] if r['selected']]
    if official_only:
        allowed=confirmed_ids(result,steam_app_id)
        selected=[r for r in selected if r['source_id'] in allowed]
    if not selected:raise ExtractionError('Nenhuma conquista selecionada para exportação.')
    if len(selected)>256:raise ExtractionError('Port Station aceita no máximo 256 conquistas; reserve uma vaga se acrescentar platina.')
    dest=_new_destination(result,destination)
    # Validate all editable fields before creating output or copying assets.
    if len({r['source_id'] for r in selected})!=len(selected):raise ExtractionError('IDs de origem duplicadas.')
    for row in selected:
        if not isinstance(row['title'],str) or not row['title'].strip() or len(row['title'].encode('utf-8'))>256 or '\0' in row['title'] or not isinstance(row['description'],str) or len(row['description'].encode('utf-8'))>2048:
            raise ExtractionError('Revise nome/descrição antes de exportar: '+row['source_id'])
    dest.mkdir(parents=True);items=[];used=set();reserved={r['source_id'] for r in selected}
    for row in selected:
        source=row['source_id'];ident=canonical_id(source,reserved,used);used.add(ident)
        if not row['title'].strip() or len(row['title'].encode('utf-8'))>256 or len(row['description'].encode('utf-8'))>2048:
            raise ExtractionError('Revise nome/descrição antes de exportar: '+source)
        icon=''
        if row['icon']:
            original=Path(row['icon']);data=original.read_bytes() if original.is_file() and original.stat().st_size<=4*1024*1024 else b''
            ext='.png' if data.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if data.startswith(b'\xff\xd8\xff') else None
            if ext and len(data)<=4*1024*1024:
                icon='assets/'+hashlib.sha256(data).hexdigest()+ext
                (dest/'assets').mkdir(exist_ok=True);(dest/icon).write_bytes(data)
        items.append({'id':ident,'source_id':source,'title':row['title'],'description':row['description'].strip() or FALLBACK,'hidden':row['hidden'],'target':1,'icon':icon})
    catalog={'schema':1,'achievements':items}
    if official_only:
        catalog['official_match']={'provider':'steam','appid':result['official_lookup']['appid'],
            'rule':'exact-source-id-intersection','count':len(items)}
    (dest/'achievements.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_report(result,dest)
    (dest/'IMPORTAR.txt').write_text('Port Station → Conquistas → Importar catálogo JSON → achievements.json.\nRevise os campos ausentes indicados em extraction-report.json. Configure o adaptador de eventos; a lista não implementa condições de desbloqueio. A platina pode ser acrescentada no Port Station.\n',encoding='utf-8')
    return dest/'achievements.json'
