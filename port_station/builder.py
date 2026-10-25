"""Offline build orchestration, locked dependencies, receipts and immutable output."""
from __future__ import annotations
from pathlib import Path
import configparser
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile
import zlib
from . import __version__, assets, native
from .project import WORKSPACE as R, ProjectError, resolve_path, relative_file, validate, pe_architecture, runtime_id

KIT=R/'build/port-studio/runtime-kit'
LOCK=R/'port_station/runtime.lock.json'
UPSTREAM=R/'build/prospero-evaluation/source-v020'
RELEASE=R/'build/prospero-evaluation/staged/PPSA99995'
CMAKE=R/'tools/cmake/cmake-4.4.4-windows-x86_64/bin/cmake.exe'
NINJA=R/'tools/sdk-v0.44/ps5-payload-sdk/win/ninja.exe'
SDK=R/'tools/sdk-v0.44/ps5-payload-sdk'

class Cancelled(ProjectError): pass

def digest(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def tree(root):
    """No symlinks/junctions, case collisions, traversal or ambiguous Windows names."""
    seen=set();root=Path(root)
    for folder,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            path=Path(folder)/name
            if path.is_symlink() or path.is_junction(): raise ProjectError(f'Link não permitido no pacote: {path}')
            rel=path.relative_to(root).as_posix();relative_file(rel)
            key=rel.casefold()
            if key in seen:raise ProjectError(f'Colisão de nomes no Windows: {rel}')
            seen.add(key)
        for name in sorted(files):yield Path(folder)/name

def doctor():
    required=[CMAKE,NINJA,R/'tools/llvm-18.1.8/bin/clang.exe',SDK/'win/prospero-clang.cmd',R/'build/host/ps5-native-tool.exe',R/'build/host/libc.prx',UPSTREAM/'native/wine64_main.c',RELEASE/'win',KIT/'prefix',LOCK,R/'build/port-studio/tools/check-profile.exe']
    return {'version':__version__,'workspace':str(R),'dependencies':[{'path':str(p),'present':p.exists()}for p in required],
            'bc7_encoder':(R/'build/port-studio/tools/make-app-assets.exe').exists(),'atrac9':{'encoder':(R/'tools/port-studio-audio/port-at9-encode.exe').exists(),'ffmpeg':(R/'tools/port-studio-audio/ffmpeg/ffmpeg.exe').exists(),'mode':'local 48 kHz stereo 192 kb/s; trim, loudness, loop'},'console_modified':False}

def build_profile_checker(log=print):
    log('Compilando validador de perfil com o parser real do runtime…')
    target=R/'build/port-studio/tools/check-profile.exe';target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(R/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-I'+str(UPSTREAM/'src'),'-I'+str(UPSTREAM/'include'),str(R/'port_station/templates/check_profile.c'),str(UPSTREAM/'src/pw_game_profile.c'),str(UPSTREAM/'src/pw_app_profile.c'),str(UPSTREAM/'src/pw_result.c'),'-o',str(target)],check=True)

def refresh_lock(log=print):
    """Explicit acceptance of a new local baseline; preserve the preceding lock."""
    if not LOCK.is_file():raise ProjectError('Instale o kit Windows antes de atualizar o lock.')
    value=json.loads(LOCK.read_text(encoding='utf8'));previous=digest(LOCK)
    backup=R/'build/port-studio/locks'/(previous+'.json');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(LOCK,backup)
    paths=[R/n for n in value['files']]
    for folder in [SDK/'target',SDK/'win',SDK/'ldscripts',R/'tools/llvm-18.1.8',CMAKE.parent.parent,R/'tools/zig-python/ziglang',R/'src/prospero_achievements',R/'tools/trophy-python',R/'tools/port-studio-audio']:
        paths.extend(p for p in tree(folder)if '__pycache__'not in p.parts)
    paths+=[R/'build/port-studio/tools/check-profile.exe',R/'src/native_runtime.c',R/'scripts/build-prospero-achievements.py']
    value['files']={p.relative_to(R).as_posix():digest(p)for p in sorted(set(paths))}
    value['previous_lock_sha256']=previous
    write_json(LOCK,value);log(f'Baseline aceita explicitamente: {len(value["files"])} arquivos. Lock anterior preservado em {backup}.')

def check_lock(log=print, cancel=None, full=True):
    if not LOCK.is_file():raise ProjectError('O runtime está ausente. Extraia o kit Windows da release antes de compilar.')
    lock=json.loads(LOCK.read_text(encoding='utf8'))
    files=lock['files']
    if not full:
        # Zig is only needed to rebuild host tools/SDK; CMake help/docs are never
        # consumed by a game build. Full audit/export still verifies every file.
        files={k:v for k,v in files.items()if not k.startswith('tools/zig-python/') and not (k.startswith('tools/cmake/')and any(part in ('Help','html','doc')for part in Path(k).parts))}
    for i,(rel,wanted)in enumerate(files.items()):
        if cancel and cancel.is_set():raise Cancelled('Cancelado.')
        path=R/rel
        if not path.is_file() or digest(path)!=wanted:raise ProjectError(f'Dependência diverge do runtime.lock.json: {rel}')
        if i%500==0:log(f'Conferindo dependências: {i}/{len(files)}')
    return lock

def make_profile(p, architecture):
    slug=runtime_id(p);folder='C:\\Games\\'+slug
    options={'application':dict(id=slug,name=p['title'],executable=folder+'\\'+p['executable'].replace('/','\\'),working_directory=folder+('\\'+str(Path(p['executable']).parent).replace('/','\\')if '/'in p['executable']else''),arguments=p['arguments'],prefix=slug,runtime='wine-wow64',architecture=architecture,graphics='dxvk'if p['profile']=='dxvk-xinput'else'gdi'),
        'display':dict(desktop='1280x720',scaling='fit',view='window',show_fps='false'),
        'input':dict(mode='xinput'if p['profile']=='dxvk-xinput'else'keyboard',mouse='none'),
        'runtime':dict(thread_scheduling='true',cpu='native'),'debug':dict(winedebug='err+all')}
    if p['profile']=='dxvk-xinput':options['application']['dll_overrides']='dxgi,d3d11,d3d10core,d3d9,d3d8=n,b'
    if p['profile']!='dxvk-xinput':options['input'].update(dict(cross='enter',circle='escape',square='shift',triangle='x',l1='pageup',r1='pagedown',up='up',down='down',left='left',right='right',options='escape',create='none',touchpad='space'))
    if p['profile']=='nwjs-canvas':
        extra='--single-process --no-sandbox --disable-breakpad --disable-crash-handler=true --in-process-gpu --disable-gpu --disable-software-rasterizer --disable-gpu-compositing --no-proxy-server --user-data-dir=C:/PortStudioNW --disable-background-networking'
        options['application']['arguments']='canvas '+extra+(' '+p['arguments']if p['arguments']else'')
    for section,fields in p['profile_options'].items():options[section].update(fields)
    return ''.join('['+section+']\n'+''.join(f'{k} = {v}\n'for k,v in fields.items())+'\n'for section,fields in options.items())

class Builder:
    def __init__(self,log=print,cancel=None):
        self.log=log;self.cancel=cancel or threading.Event();self.process=None;self.logfile=None

    def emit(self,message):
        self.log(message)
        if self.logfile:self.logfile.write(message+'\n');self.logfile.flush()

    def checkpoint(self):
        if self.cancel.is_set():raise Cancelled('Build cancelada; saída parcial preservada para diagnóstico.')

    def run(self,args,env=None):
        self.checkpoint();self.emit('> '+' '.join(map(str,args)))
        self.process=subprocess.Popen(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        # Drain in a reader so cancellation works even when a tool emits no output.
        import queue
        q=queue.Queue()
        def reader():
            for line in self.process.stdout:q.put(line.rstrip())
        proc=self.process;t=threading.Thread(target=reader,daemon=True);t.start()
        try:
            while proc.poll() is None or t.is_alive() or not q.empty():
                if self.cancel.is_set():
                    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    raise Cancelled('Compilação cancelada.')
                try:self.emit(q.get(timeout=.1))
                except queue.Empty:pass
            if proc.returncode:raise ProjectError(f'Ferramenta terminou com código {proc.returncode}. Veja build.log.')
        finally:
            if proc.poll() is None:proc.kill()
            proc.wait();proc.stdout.close();self.process=None

    def copy(self,source,destination,skip_python_cache=False):
        for path in tree(source):
            if skip_python_cache and ('__pycache__'in path.parts or path.suffix=='.pyc'):continue
            self.checkpoint();dest=destination/path.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)

    def build(self,p,base,output,archive=True,prepare_only=False):
        p=copy.deepcopy(p);base=Path(base).resolve();validate(p,base)
        output=Path(output).resolve();game=resolve_path(p['game_dir'],base)
        if output.exists():raise ProjectError('Escolha uma pasta de saída nova: builds existentes não são substituídas.')
        for source in [game,R/'port_station',R/'tools',R/'src',R/'sdk',RELEASE,KIT]:
            if output.is_relative_to(source)or source.is_relative_to(output):raise ProjectError('Saída sobrepõe um diretório de entrada/dependência.')
        architecture=pe_architecture(game/p['executable']);list(tree(game))
        output.mkdir(parents=True);self.logfile=(output/'build.log').open('w',encoding='utf8')
        try:
            self.emit('Port Station '+__version__+' — verificando entradas')
            lock=check_lock(self.emit,self.cancel,full=False)
            inputs={x.relative_to(game).as_posix():digest(x)for x in sorted(tree(game))}
            if p['adapter']=='breath':
                from . import breath
                breath.inspect(game,self.run)
            write_json(output/'project.json',p)
            generated=output/'generated';catalog=resources=blob=None
            if p['adapter']!='none':catalog,resources,blob=assets.make_catalog(p,base,output/'achievements')
            native.generate(p,generated,catalog,resources,blob)
            (output/'CMakeLists.txt').write_text(native.cmake(p,generated),encoding='utf8',newline='\n')
            profile=make_profile(p,architecture);(output/'game.profile').write_text(profile,encoding='utf8',newline='\n')
            self.run([R/'build/port-studio/tools/check-profile.exe',output/'game.profile'])
            art=output/'presentation';audio_report=assets.prepare_presentation(p,base,art,self.run,self.emit)
            if prepare_only:
                write_json(output/'result.json',{'status':'prepared; not compiled','architecture':architecture,'output':str(output)});return output
            self.emit('Compilando launcher e helper próprios do título…')
            self.compile(p,output)
            dist=output/'native/dist'/p['title_id']
            if (dist/'eboot.bin').read_bytes()[:4]!=bytes.fromhex('4f153d1d'):raise ProjectError('Eboot não é FSELF esperado.')
            for folder in ['win','LICENSES']:self.copy(RELEASE/folder,dist/folder)
            for name in ['LICENSE','SOURCES.txt','THIRD_PARTY.md','mesa-zink-manifest.json']:shutil.copy2(RELEASE/name,dist/name)
            shutil.copy2(output/'helper/lapy.elf',dist/'lapy.elf')
            shutil.copy2(R/'tools/Lapy-breath-reference/LICENSE',dist/'LICENSES/Lapy-LICENSE.txt')
            slug=runtime_id(p);seed=dist/'seed';prefix=seed/'prefixes'/slug
            self.emit('Copiando prefixo limpo e arquivos do jogo…')
            self.copy(KIT/'prefix',prefix)
            target=prefix/'drive_c/Games'/slug;self.copy(game,target)
            for overlay in p['overlays']:
                self.checkpoint();dest=target/relative_file(overlay['destination']);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(resolve_path(overlay['source'],base),dest)
            if p['adapter']=='breath':
                self.emit('Breath: preparando e verificando a ponte de conquistas na cópia da build…')
                compatibility=breath.prepare(target,self.run)
                write_json(output/'breath-compatibility.json',compatibility)
            if p['profile']=='nwjs-canvas':
                from .nwjs import prepare_fonts
                compatibility=prepare_fonts(target,prefix);write_json(output/'nwjs-compatibility.json',compatibility)
                self.emit(f'NW.js: {len(compatibility["fonts"])} fontes locais; {len(compatibility["css"])} folhas CSS ajustadas.')
            if p['adapter']=='nwjs-steam':self.nw_bridge(p,target)
            profiles=seed/'profiles';profiles.mkdir(parents=True)
            (profiles/(slug+'.profile')).write_text(profile,encoding='utf8',newline='\n');(profiles/'profiles.lst').write_text(slug+'.profile\n',encoding='utf8',newline='\n')
            # Seed checksums cover every copied file, after all intentional modifications.
            rows=[]
            for path in sorted(tree(seed)):
                self.checkpoint();crc=0
                with path.open('rb')as f:
                    for chunk in iter(lambda:f.read(1024*1024),b''):crc=zlib.crc32(chunk,crc)
                rel=path.relative_to(seed).as_posix();rows.append(f'{path.stat().st_size}\t{crc:08x}\t{rel}\n')
            (dist/'seed-files.tsv').write_text(''.join(rows),encoding='utf8',newline='\n')
            self.copy(art,dist/'sce_sys')
            param=json.loads((dist/'sce_sys/param.json').read_text(encoding='utf8'))
            param['contentVersion']=p['version'];param['ageLevel']['default']=p['age']
            param['localizedParameters']['pt-BR']={'titleName':p['title']}
            from .audio import apply_metadata
            apply_metadata(param,audio_report)
            write_json(dist/'sce_sys/param.json',param)
            self.source_bundle(p,output,dist)
            self.emit('Gerando recibos SHA-256…')
            files={x.relative_to(dist).as_posix():digest(x)for x in sorted(tree(dist))}
            game_inputs={x.relative_to(game).as_posix():digest(x)for x in sorted(tree(game))}
            if game_inputs!=inputs:raise ProjectError('O jogo de origem mudou durante a build. Preserve esta saída parcial e gere uma nova.')
            receipt={'status':'built; new shell requires console validation','studio_version':__version__,'title_id':p['title_id'],'game_id':p['game_id'],'architecture':architecture,'runtime_lock_sha256':digest(LOCK),'project_sha256':digest(output/'project.json'),'files':files,'game_inputs':game_inputs,'tool_sources':{x.relative_to(R).as_posix():digest(x)for x in tree(R/'port_station')if '__pycache__'not in x.parts},'overlays':{str(resolve_path(a['source'],base)):digest(resolve_path(a['source'],base))for a in p['overlays']},'data_root':'/data/port-studio/'+p['title_id'].lower(),'exit':'Options + touchpad held 1 second; PS Close inherited from exercised runtime','achievements':len(catalog['achievements'])if catalog else 0,'adapter':p['adapter'],'platinum':p['platinum'],'saves_imported':False,'console_modified':False}
            write_json(output/'manifest.json',receipt)
            if archive:
                archive_path=output/(p['title_id']+'.zip');self.emit('Criando ZIP…')
                with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED,compresslevel=1)as z:
                    for rel in files:
                        self.checkpoint();info=zipfile.ZipInfo(p['title_id']+'/'+rel,(2026,1,1,0,0,0));info.create_system=3;info.external_attr=0o100755<<16;info.compress_type=zipfile.ZIP_DEFLATED;info.compress_level=1
                        with (dist/rel).open('rb')as src,z.open(info,'w',force_zip64=True)as dest:shutil.copyfileobj(src,dest,1024*1024)
                receipt['zip_sha256']=digest(archive_path);write_json(output/'manifest.json',receipt)
            write_json(output/'result.json',{'status':'built','title_folder':str(dist),'manifest':str(output/'manifest.json')})
            self.emit('Build concluída: '+str(dist));return dist
        except Exception as e:
            write_json(output/'result.json',{'status':'cancelled'if isinstance(e,Cancelled)else'failed','error':str(e)})
            raise
        finally:self.logfile.close();self.logfile=None

    def compile(self,p,output):
        helper=output/'helper';helper.mkdir()
        (helper/'owned_identity.h').write_text(f'#define LAPY_OWNED_ID "port-studio-{p["title_id"]}-0.1.0"\n#define TARGET_TITLE "{p["title_id"]}"\n')
        src=R/'tools/Lapy-breath-reference/source';env=os.environ.copy();env['PATH']=str(R/'tools/llvm-18.1.8/bin')+os.pathsep+env['PATH']
        env['PATH']+=os.pathsep+str(SDK/'win')
        self.run([str(R/'tools/llvm-18.1.8/bin/clang.exe'),'--start-no-unused-arguments','-target','x86_64-sie-ps5','-isysroot',SDK,'-isystem',SDK/'target/include','-L',SDK/'target/lib','-L',SDK/'target/user/homebrew/lib','-fno-stack-protector','-fno-plt','-femulated-tls','-lc','-lkernel_web','--end-no-unused-arguments','-std=c11','-O2','-Wall','-Wextra','-Werror','-DLAPY_SERVICE=0','-DLAPY_ELF_HELPER=1','-DLAPY_REQUIRE_CLIENT_RESULT=0','-DLAPY_MAX_REQUESTS=0','-I'+str(UPSTREAM/'native/ps5log'),'-I'+str(helper),'-I'+str(src),src/'owned_root_daemon.c',src/'donor_transaction.c',src/'vnode_ref_probe.c','-o',helper/'lapy.elf','--start-no-unused-arguments',SDK/'target/lib/crt1.o','-lSceLibcInternal','-lSceNet','--end-no-unused-arguments'],env)
        self.run([CMAKE,'-S',output,'-B',output/'native','-G','Ninja','-DCMAKE_TOOLCHAIN_FILE='+str(R/'sdk/ps5-game-port/cmake/toolchain.cmake'),'-DCMAKE_MAKE_PROGRAM='+str(NINJA),'-DGP_PYTHON='+sys.executable,'-DCMAKE_BUILD_TYPE=Release'])
        self.run([CMAKE,'--build',output/'native','--parallel','4'])
        # The SDK creates a temporary native-only zip; keep only the complete studio archive.
        temporary=output/'native/dist'/(p['title_id']+'.zip')
        if temporary.exists():temporary.unlink()
        partial=output/'native/dist'/(p['title_id']+'-manifest.json')
        if partial.exists():partial.unlink()

    def nw_bridge(self,p,target):
        js=target/'www/js';js.mkdir(exist_ok=True)
        self.copy_single(R/'sdk/prospero-achievements/bridge/prospero_file_bridge.js',js/'prospero_file_bridge.js')
        from .nwjs import achievement_aliases
        config={'gameId':p['game_id'],'ids':[a['id']for a in p['achievements']], 'aliases':achievement_aliases(p,target)}
        source=(R/'port_station/templates/nwjs_achievements.js').read_text(encoding='utf8').replace('__CONFIG__',json.dumps(config,ensure_ascii=True))
        (js/'port_studio_achievements.js').write_text(source,encoding='utf8',newline='\n')
        path=target/'www/index.html';index=path.read_bytes()
        if b'port_studio_achievements.js'in index:raise ProjectError('O jogo já contém uma ponte Port Station. Use os arquivos originais.')
        if index.lower().count(b'</body>')!=1:raise ProjectError('NW.js: esperado um único </body> para a ponte.')
        pos=index.lower().index(b'</body>')
        index=index[:pos]+b'<script src="js/prospero_file_bridge.js"></script>\n<script src="js/port_studio_achievements.js"></script>\n'+index[pos:]
        path.write_bytes(index)

    @staticmethod
    def copy_single(source,dest):dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)

    def source_bundle(self,p,output,dist):
        dest=dist/'port-source';self.copy(output/'generated',dest/'generated')
        self.copy(R/'port_station',dest/'port_station',skip_python_cache=True)
        for name in ['native','src','include','wine/ps5']:self.copy(UPSTREAM/name,dest/'prospero-win'/name)
        self.copy(R/'sdk/ps5-game-port',dest/'sdk/ps5-game-port');self.copy(R/'sdk/prospero-achievements',dest/'sdk/prospero-achievements')
        self.copy(R/'tools/Lapy-breath-reference/source',dest/'owned-helper')
        self.copy(R/'tools/PS5_Vulkan/tooling/native',dest/'native-tools')
        for name in ['src/tcoal/wine_title','src/tcoal/prospero_adapter','src/breath/wine_title','src/breath/prospero_adapter']:
            self.copy(R/name,dest/name)
        self.copy_single(output/'CMakeLists.txt',dest/'CMakeLists.txt')
        # Original project paths may identify the workstation; retained locally in build output.
        (dist/'PORT-STATION.txt').write_text('Port Station '+__version__+'\nWindows game + Wine compatibility runtime; not a native engine recompile.\nOwn achievements service/API1; no Sony trophy service.\nFull build receipt/project/inputs: build output manifest.json and project.json.\nSource adaptations: port-source; upstream runtime notices: SOURCES.txt, THIRD_PARTY.md, LICENSES.\nNo save or achievement state is imported by the tool.\n',encoding='utf8')
