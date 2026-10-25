"""Build host programs, SDK archive, embedded web assets and PS5 payloads."""
from pathlib import Path
import argparse,binascii,hashlib,json,os,struct,subprocess,zlib
R=Path(__file__).resolve().parents[1];S=R/'src/prospero_achievements';W=R/'build/prospero-achievements'
G=W/'generated';G.mkdir(parents=True,exist_ok=True)
SDK=R/'sdk/prospero-achievements'
def array(name,data,terminate=False):
    if terminate:data+=b'\0'
    return 'static const unsigned char '+name+'[] = {'+','.join(str(x) for x in data)+'};\n'
text='/* Generated from the exact local web source. */\n'
for name,p in [('index','index.html'),('css','app.css'),('js','app.js')]:text+=array('pa_web_'+name,(S/'web'/p).read_bytes(),True)
(G/'pa_web_assets.h').write_text(text,encoding='ascii')
def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',binascii.crc32(t+b)&0xffffffff)
# An original code-drawn PA monogram used only by the diagnostic catalog.
letters=['111101110','100101001','111101111','100001001','100001001']
rows=[]
for y in range(64):
    row=bytearray([0])
    for x in range(64):
        on=14<=x<50 and 22<=y<42 and letters[(y-22)//4][(x-14)//4]=='1'
        row.extend((142,224,206,255)if on else(20,36,55,255))
    rows.append(row)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',64,64,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows),9))+chunk(b'IEND',b'')
(W/'sdk-test-icon.png').write_bytes(png);(G/'pa_probe_assets.h').write_text(array('pa_probe_icon',png),encoding='ascii')
ap=argparse.ArgumentParser();ap.add_argument('--ps5',action='store_true');a=ap.parse_args()
includes=['-I'+str(S),'-I'+str(G),'-I'+str(SDK/'include')]
flags=['-std=c11','-O2','-Wall','-Wextra','-Werror','-DCJSON_NESTING_LIMIT=32',*includes]
common=[S/'pa_common.c',S/'vendor/cJSON.c',S/'vendor/sha256.c']
client=[SDK/'src/pa_sdk.c',S/'pa_probe.c',*common]
server=[S/'pa_server.c',S/'pa_model.c',*common]
host=W/'host';host.mkdir(exist_ok=True)
zig=R/'tools/zig-python/ziglang/zig.exe'
for name,files in [('prospero_achievements',server),('pa_sdk_probe',client),('pa_directory_test',[S/'tests/pa_directory_test.c',*common])]:
    subprocess.run([str(zig),'cc','-target','x86_64-windows-gnu',*flags,*map(str,files),'-lws2_32','-o',str(host/(name+'.exe'))],check=True)
    print('Host built:',name,flush=True)
if a.ps5:
    out=W/'ps5';out.mkdir(exist_ok=True);env=dict(os.environ)
    env['PATH']=str(R/'tools/llvm-18.1.8/bin')+os.pathsep+env['PATH']
    compiler=R/'tools/sdk-v0.44/ps5-payload-sdk/win/prospero-clang.cmd'
    for name,files in [('prospero_achievements',server),('pa_sdk_probe',client),('pa_stop',[S/'pa_stop.c',*common])]:
        subprocess.run([str(compiler),*flags,'-Wno-unreachable-code-generic-assoc','-DPA_PS5',*map(str,files),'-lkernel','-o',str(out/(name+'.elf'))],check=True,env=env)
        print('PS5 ELF built:',name,flush=True)
    # Static SDK library: the client includes its required common/JSON/hash code.
    objects=[]
    for p in [SDK/'src/pa_sdk.c',*common]:
        obj=out/(p.stem+'.o');subprocess.run([str(compiler),*flags,'-Wno-unreachable-code-generic-assoc','-DPA_PS5','-c',str(p),'-o',str(obj)],check=True,env=env);objects.append(obj)
    subprocess.run([str(R/'tools/llvm-18.1.8/bin/llvm-ar.exe'),'rcs',str(out/'libprospero_achievements.a'),*map(str,objects)],check=True)
receipt={'version':'0.1.0','sdk_version':'0.1.2','api_major':1,'sources':{},'host_built':True,'ps5_built':a.ps5}
for base in [S,SDK]:
    for p in sorted(base.rglob('*')):
        if p.is_file():receipt['sources'][p.relative_to(R).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
receipt['host_artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in host.glob('*.exe')}
if a.ps5:receipt['ps5_artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (W/'ps5').glob('*')if p.suffix in ['.elf','.a']}
(W/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
