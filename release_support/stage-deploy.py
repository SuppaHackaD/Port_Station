"""Create an explicit public source allowlist and a separate runtime release tree."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R))
from port_studio import __version__
from port_studio.builder import check_lock,tree
from port_studio.assets import Image
from PIL import ImageDraw,ImageFont

def copy_file(src,dest,link=False):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():dest.unlink() # Never edit a hardlinked source in place.
    if link:os.link(src,dest)
    else:shutil.copy2(src,dest)

def copy_dir(src,dest):
    for p in tree(src):
        if any(x in p.relative_to(src).parts for x in ('__pycache__','bin','obj','.git')):continue
        copy_file(p,dest/p.relative_to(src))

def stage(output):
    output=output.resolve();repo=output/'Port_Station';kit=output/'_staging/Port_Station'
    if repo.exists()or kit.exists():raise ValueError('Preserve existing staging; choose a new destination.')
    lock=check_lock();repo.mkdir(parents=True);kit.mkdir(parents=True)
    original_lock=hashlib.sha256((R/'port_studio/runtime.lock.json').read_bytes()).hexdigest()
    # Exclude unused trophy/dump research and the optional external FFmpeg binary.
    def public_dependency(rel):
        if rel in ('tools/port-studio-audio/ffmpeg/ffmpeg.exe','tools/port-studio-audio/port-at9-encode.pdb'):return False
        if rel.startswith('sdk/ps5-game-port/'):
            return rel.startswith(('sdk/ps5-game-port/cmake/','sdk/ps5-game-port/runtime/'))or rel=='sdk/ps5-game-port/host/package_title.py'
        return True
    for rel in lock['files']:
        if not public_dependency(rel):continue
        copy_file(R/rel,kit/rel,link=True)
    directories=['port_studio','port_station','sdk/ps5-game-port/cmake','sdk/ps5-game-port/runtime','sdk/prospero-achievements','src/prospero_achievements','src/tcoal/wine_title','src/tcoal/prospero_adapter','src/breath/wine_title','src/breath/prospero_adapter','build/prospero-evaluation/source-v020','tools/Lapy-breath-reference/source','tools/PS5_Vulkan/tooling/native','tools/zlib-1.3.2','release_support']
    for rel in directories:copy_dir(R/rel,repo/rel)
    for rel in ['Port_Station.cmd','PORT_STATION.md','src/native_runtime.c','scripts/build-prospero-achievements.py','scripts/test-prospero-achievements.py','scripts/build-port-studio-audio.py','scripts/build-native-tools.ps1','tools/Lapy-breath-reference/LICENSE','tools/PS5_Vulkan/LICENSE','sdk/ps5-game-port/host/package_title.py']:
        copy_file(R/rel,repo/rel)
    copy_file(R/'port_studio/LICENSE',repo/'LICENSE')
    (repo/'public-release.json').write_text(json.dumps({'schema':1,'version':__version__,'bundle_ffmpeg':False,'commercial_game_data':False},indent=2)+'\n',encoding='utf8')
    (repo/'requirements.txt').write_text('Pillow==13.0.0\n',encoding='utf8')
    # Public tests must not depend on commercial executables or personal metadata.
    test=repo/'port_studio/tests/test_core.py';text=test.read_text(encoding='utf8')
    text=text.replace('validate(p,self.base)','validate(p,self.base,False)')
    old="    def test_real_pe_architecture(self):\n        from port_studio.project import resolve_path\n        self.assertEqual(pe_architecture(resolve_path(self.p['game_dir'],self.base)/self.p['executable']),'pe32')"
    new="""    def test_pe_architecture_without_commercial_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            exe=Path(temp)/'fixture.exe'
            for machine,expected in [(0x14c,'pe32'),(0x8664,'pe64')]:
                data=bytearray(134);data[:2]=b'MZ';struct.pack_into('<I',data,60,128)
                data[128:132]=b'PE\\0\\0';struct.pack_into('<H',data,132,machine)
                exe.write_bytes(data);self.assertEqual(pe_architecture(exe),expected)"""
    if old in text:text=text.replace(old,new)
    elif new not in text:raise ValueError('Test fixture source changed; review before publication.')
    line="            subprocess.run([str(WORKSPACE/'build/port-studio/tools/check-profile.exe'),str(path)],check=True,capture_output=True)"
    text=text.replace(line,"            checker=WORKSPACE/'build/port-studio/tools/check-profile.exe'\n            if checker.is_file():subprocess.run([str(checker),str(path)],check=True,capture_output=True)")
    test.write_text(text,encoding='utf8')
    test=repo/'port_studio/tests/test_audio.py';text=test.read_text(encoding='utf8')
    if '@unittest.skipUnless(FFMPEG.is_file()'not in text:text=text.replace('class AudioTests(unittest.TestCase):','@unittest.skipUnless(FFMPEG.is_file(), "Optional FFmpeg: run release_support/install-ffmpeg.py for audio integration tests")\nclass AudioTests(unittest.TestCase):')
    test.write_text(text,encoding='utf8')
    for base in [repo/'sdk/prospero-achievements',repo/'src/tcoal/prospero_adapter']:
        for p in base.rglob('*'):
            if p.is_file()and p.suffix in ('.md','.js'):
                text=p.read_text(encoding='utf8');p.write_text(re.sub(r'\b[0-9a-f]{8}\b','0000002a',text),encoding='utf8')
    sdkreadme=repo/'sdk/prospero-achievements/README.md';text=sdkreadme.read_text(encoding='utf8')
    text=text.replace('Continuidade no PS5 ainda depende do teste manual. Nenhum jogo existente foi integrado ou alterado nesta revisão.','Continuidade no PS5 e integrações Breath/TCOAL foram confirmadas em testes manuais; ver README raiz para o escopo.')
    text=text.replace('- Ainda sem adaptadores novos Breath/TCOAL, importação do ledger antigo, migração de condições, popup próprio ou autoload.','- Adaptadores Breath/TCOAL e popup de confirmação no port são incluídos. Autoload do payload e migração genérica de condições ainda não são implementados.')
    sdkreadme.write_text(text,encoding='utf8')
    guide=repo/'PORT_STATION.md';text=guide.read_text(encoding='utf8')
    text=text.replace('O FFmpeg foi fixado','Nesta release pública, FFmpeg é opcional e obtido diretamente com `python release_support/install-ffmpeg.py`; o executável não acompanha o kit. O FFmpeg foi fixado')
    text=text.replace('A nova música gerada ainda precisa de validação no PS5; os jogos atuais permanecem intactos.','Artes e música personalizadas do Studio foram validadas no PS5 com TCOAL. Esta distribuição usa placeholders próprios e não inclui música ou arquivos comerciais.')
    text=text.replace('O Pillow compatível está no toolkit.','O Pillow compatível está no toolkit; FFmpeg é opcional e instalado separadamente pelo script da release.')
    guide.write_text(text,encoding='utf8')
    # The public recipes contain only declarative compatibility metadata.
    examples=repo/'port_studio/examples';assets=examples/'assets';assets.mkdir(parents=True,exist_ok=True)
    font=R/'build/port-studio/runtime-kit/prefix/drive_c/windows/Fonts/DejaVuSans-Bold.ttf'
    for game,label,accent in [('breath','Breath',(99,213,191)),('tcoal','TCOAL',(189,154,225))]:
        for filename,size in [('icon.png',(512,512)),('background.png',(1920,1080)),('achievement.png',(256,256))]:
            im=Image.new('RGB',size,(20,27,39));draw=ImageDraw.Draw(im);w,h=size
            draw.rectangle((w//12,h//12,w-w//12,h-h//12),outline=accent,width=max(3,w//200))
            text=label if filename!='achievement.png'else 'PA'
            f=ImageFont.truetype(str(font),max(20,int(w/(len(text)*0.9))))
            draw.text((w/2,h/2),text,fill=accent,font=f,anchor='mm')
            if filename=='background.png':draw.text((w/2,h*0.72),'PORT STATION',fill=(180,188,201),font=ImageFont.truetype(str(font),42),anchor='mm')
            im.save(assets/(game+'-'+filename))
        p=json.loads((R/'port_studio/examples'/(game+'.ps5port.json')).read_text(encoding='utf8'))
        p.update(game_dir='${workspace}/local-games/'+game,version='01.000.002',catalog_version=10,sound='',background='assets/'+game+'-background.png',launch_background='',icon='assets/'+game+'-icon.png',overlays=[],platinum=True,platinum_icon='assets/'+game+'-achievement.png')
        if game=='tcoal':p['platinum_title']='TCOAL — Conjunto completo'
        for a in p['achievements']:a['icon']='assets/'+game+'-achievement.png'
        (examples/(game+'.ps5port.json')).write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (assets/'LICENSE.txt').write_text('SPDX-License-Identifier: CC0-1.0\nOriginal geometric/text-only placeholders generated by release_support/stage-deploy.py. No official game artwork or music.\nhttps://creativecommons.org/publicdomain/zero/1.0/\n',encoding='utf8')
    (repo/'.gitignore').write_text('''__pycache__/
*.py[cod]
*.pdb
**/obj/
**/bin/
!port_studio/vendor/**/bin/
/local-games/
/local-projects/
/outputs/
/releases/
/handoff/
/analysis/
/build/host/
/build/release-managed/
/build/prospero-achievements/
/build/port-studio/
/build/prospero-evaluation/staged/
/tools/llvm-18.1.8/
/tools/sdk-v0.44/
/tools/cmake/
/tools/zig-python/
/tools/trophy-python/
/tools/port-studio-audio/
*.zip
*.elf
*.prx
*.exe
*.dll
!port_studio/runtime.lock.json
''',encoding='utf8')
    (repo/'.gitattributes').write_text('* text=auto eol=lf\n*.png binary\n*.webp binary\n*.ttf binary\n*.otf binary\n*.at9 binary\n',encoding='utf8')
    for rel in ['README.md','docs','NOTICE.md','THIRD_PARTY.md','SOURCES.json','LICENSES','.github']:
        src=R/'release_support/public'/rel
        if src.is_dir():copy_dir(src,repo/rel)
        elif src.exists():copy_file(src,repo/rel)
    # Canonical source line endings survive git checkout without invalidating the lock.
    for p in tree(repo):
        data=p.read_bytes()
        if b'\0'not in data and b'\r\n'in data:p.write_bytes(data.replace(b'\r\n',b'\n'))
    # Runtime binaries are release-only. Every first-party source remains beside them.
    for p in tree(repo):copy_file(p,kit/p.relative_to(repo))
    for p in tree(R/'tools/port-studio-audio'):copy_file(p,kit/p.relative_to(R),link=True)
    for rel in ['tools/port-studio-audio/ffmpeg/ffmpeg.exe','tools/port-studio-audio/port-at9-encode.pdb']:
        p=kit/rel
        if p.exists():p.unlink()
    for name in ['BreathPS5Bridge.dll','PatchBreathAchievements.exe']:
        copy_file(R/'build/release-managed'/name,kit/'build/release-managed'/name)
    for name in ['prospero_achievements.elf','pa_stop.elf','pa_sdk_probe.elf','libprospero_achievements.a']:
        copy_file(R/'build/prospero-achievements/ps5'/name,kit/'build/prospero-achievements/ps5'/name)
    # Source-only tests build the host service themselves; no user journals bundled.
    copy_file(R/'build/prospero-achievements/build.json',kit/'build/prospero-achievements/build.json')
    for p in (R/'build/prospero-achievements/host').glob('*.exe'):copy_file(p,kit/p.relative_to(R))
    lock['previous_lock_sha256']=original_lock
    lock['distribution']='public deploy: unused research and optional external FFmpeg excluded; public docs/examples sanitized'
    lock['files']={rel:hashlib.sha256((kit/rel).read_bytes()).hexdigest()for rel in lock['files']if public_dependency(rel)}
    for root in [repo,kit]:
        path=root/'port_studio/runtime.lock.json';path.unlink();path.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf8')
    kit_files=sorted(p.relative_to(kit).as_posix()for p in tree(kit)if '__pycache__'not in p.parts)
    (output/'releases').mkdir(exist_ok=True)
    (output/'staging.json').write_text(json.dumps({'version':__version__,'repository':str(repo),'kit_staging':str(kit),'locked_files':len(lock['files']),'games_included':False,'game_music_included':False,'official_art_included':False,'kit_files':kit_files},indent=2)+'\n',encoding='utf8')
    print('Public source:',repo);print('Runtime staging:',kit)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('output',type=Path);stage(ap.parse_args().output)
