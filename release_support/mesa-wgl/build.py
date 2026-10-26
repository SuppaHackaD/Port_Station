"""Build a diagnostic Windows x64 WGL/Zink provider from pinned public sources.

The cross-build flags follow prospero-win/tools/build_mesa_zink.sh (LGPL-2.1+).
This diagnostic orchestration and added logging are MIT; Mesa's notices remain.
No game installation, firmware dump, console account or proprietary SDK is used.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tarfile,urllib.request
from diagnostics import instrument

REPO=Path(__file__).resolve().parents[2]
COMPILER_URL='https://github.com/mstorsjo/llvm-mingw/releases/download/20260922/llvm-mingw-20260922-ucrt-ubuntu-22.04-x86_64.tar.xz'
COMPILER_SHA='bb7bb7654b33d5aa8712acb837c963b2e0c56352560c76105270a3268c665c21'

def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def fetch(url,wanted,path):
    request=urllib.request.Request(url,headers={'User-Agent':'Port-Station-public-source-build'})
    with urllib.request.urlopen(request,timeout=120)as response,path.open('wb')as out:
        shutil.copyfileobj(response,out,1024*1024)
    if sha(path)!=wanted:raise ValueError('Archive digest mismatch: '+path.name)

def extract(archive,destination):
    destination.mkdir()
    with tarfile.open(archive)as t:t.extractall(destination,filter='data')
    children=list(destination.iterdir())
    if len(children)!=1 or not children[0].is_dir():raise ValueError('Unexpected archive root')
    return children[0]

def run(*args):
    print('>',*map(str,args),flush=True);subprocess.run(list(map(str,args)),check=True)

def build(work,jobs):
    if os.name!='posix':raise ValueError('Run the cross-build on Linux or the repository CI')
    work=work.resolve();work.mkdir(parents=True,exist_ok=False)
    pins=json.loads((REPO/'SOURCES.json').read_text(encoding='utf-8'))['archives']
    mesa=next(p for p in pins if p['name']=='mesa-zink')
    if 'e4607ef697fe3df8d1ebc329bf1917d041843306'not in mesa['url']:raise ValueError('Unexpected Mesa revision')
    source_archive=work/'mesa.tar.gz';compiler_archive=work/'compiler.tar.xz'
    print('Fetching hash-pinned Mesa and llvm-mingw',flush=True)
    fetch(mesa['url'],mesa['sha256'],source_archive);fetch(COMPILER_URL,COMPILER_SHA,compiler_archive)
    source=extract(source_archive,work/'source');compiler=extract(compiler_archive,work/'compiler')
    if (source/'VERSION').read_text().strip()!='26.2.0':raise ValueError('Mesa version mismatch')
    patches=instrument(source);(work/'patches.json').write_text(json.dumps(patches,indent=2)+'\n')
    cross=work/'cross.ini'
    cross.write_text(f'''[binaries]
c = '{compiler}/bin/x86_64-w64-mingw32-clang'
cpp = '{compiler}/bin/x86_64-w64-mingw32-clang++'
ar = '{compiler}/bin/llvm-ar'
strip = '{compiler}/bin/llvm-strip'
windres = '{compiler}/bin/llvm-windres'
pkg-config = 'false'
[host_machine]
system = 'windows'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
[properties]
needs_exe_wrapper = true
''')
    options=['platforms=windows','gallium-drivers=zink','vulkan-drivers=','opengl=true',
             'egl=disabled','gbm=disabled','glx=disabled','gles1=disabled','gles2=disabled',
             'llvm=disabled','zlib=disabled','zstd=disabled','shader-cache=disabled',
             'xmlconfig=disabled','expat=disabled','libunwind=disabled','valgrind=disabled',
             'video-codecs=','build-tests=false','tools=','gallium-va=disabled','gallium-rusticl=false']
    run('meson','setup',work/'build',source,'--cross-file',cross,'--wrap-mode=nofallback',
        '--buildtype=release','--default-library=static',*['-D'+s for s in options])
    run('ninja','-C',work/'build','-j',jobs,'src/gallium/targets/libgl-gdi/opengl32.dll','src/gallium/targets/wgl/libgallium_wgl.dll')
    artifacts=work/'artifacts';output=artifacts/'x86_64-windows';output.mkdir(parents=True)
    for target in ('libgl-gdi/opengl32.dll','wgl/libgallium_wgl.dll'):
        p=work/'build/src/gallium/targets'/target
        run(compiler/'bin/llvm-strip','--strip-debug','-o',output/p.name,p)
    pending=list(output.glob('*.dll'));seen=set();imports={}
    while pending:
        p=pending.pop()
        if p.name in seen:continue
        seen.add(p.name)
        text=subprocess.check_output([str(compiler/'bin/llvm-readobj'),'--coff-imports',str(p)],text=True)
        names=re.findall(r'(?m)^\s*Name: (.+)$',text);imports[p.name]=names
        for n in names:
            if n.lower() in ('libc++.dll','libunwind.dll','libwinpthread-1.dll') and not(output/n).exists():
                shutil.copy2(compiler/'x86_64-w64-mingw32/bin'/n,output/n);pending.append(output/n)
    licenses=artifacts/'LICENSES';licenses.mkdir()
    shutil.copy2(source/'docs/license.rst',licenses/'Mesa-license.rst')
    shutil.copytree(source/'licenses',licenses/'Mesa')
    shutil.copy2(compiler/'LICENSE.TXT',licenses/'llvm-mingw-LICENSE.TXT')
    shutil.copytree(compiler/'x86_64-w64-mingw32/share/mingw32',licenses/'mingw32')
    modified=artifacts/'diagnostic-source'
    for name in patches:
        p=modified/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,p)
    for p in Path(__file__).parent.glob('*.py'):shutil.copy2(p,modified/p.name)
    shutil.copy2(Path(__file__).with_name('README.md'),artifacts/'README.md')
    manifest={'variant':'wgl-lifecycle-diagnostic-1','mesa_source':mesa,'compiler_url':COMPILER_URL,
              'compiler_sha256':COMPILER_SHA,'console_validated':False,'behavior_patch':False,
              'source_changes':patches,'build_script_sha256':sha(__file__),
              'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size,'imports':imports[p.name]}for p in output.glob('*.dll')}}
    (artifacts/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Diagnostic provider and source association ready:',artifacts,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--jobs',type=int,default=2)
    args=parser.parse_args()
    if not 1<=args.jobs<=8:parser.error('--jobs must be between 1 and 8')
    build(args.work,args.jobs)
