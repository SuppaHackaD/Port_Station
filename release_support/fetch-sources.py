"""Fetch immutable upstream source archives for the public release; record SHA-256."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,shutil,urllib.request,time
ENTRIES=[
('prospero-win','https://codeload.github.com/mpereiraesaa/prospero-win/tar.gz/644e32e400c555e340d507383398c5d21b39b0b0'),
('wine','https://codeload.github.com/wine-mirror/wine/tar.gz/490f6d5dcbb2a5047345b8af88d114bbcaad69a8'),
('native-boilerplate-title','https://codeload.github.com/mpereiraesaa/ps5-native-app-boilerplate/tar.gz/9c0b994a048521af6fb84c73ded364504fe250e9'),
('native-boilerplate-modules','https://codeload.github.com/mpereiraesaa/ps5-native-app-boilerplate/tar.gz/30597512539e7edfde079cbcaf4a626bc0a948c5'),
('payload-sdk-v044','https://codeload.github.com/ps5-payload-dev/sdk/tar.gz/refs/tags/v0.44'),
('mesa-radv','https://codeload.github.com/mpereiraesaa/PS5_Mesa/tar.gz/01d70579b8d410d6a482e36c6f184798ae4c83ad'),
('mesa-zink','https://codeload.github.com/mpereiraesaa/PS5_Mesa/tar.gz/e4607ef697fe3df8d1ebc329bf1917d041843306'),
('ps5-vulkan','https://codeload.github.com/mpereiraesaa/PS5_Vulkan/tar.gz/8aee3afb37bcfad06f0c7d263b901040f08ebbd0'),
('radv-payload-sdk','https://codeload.github.com/mihawk-99/PS5_PayloadSDK/tar.gz/95c08f27386fc698f6bbe21dde3030140a41d10b'),
('ffmpeg','https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/bf0e831606938f530326c9679591109407fa8d0d'),
('freetype-2.13.3','https://download.savannah.gnu.org/releases/freetype/freetype-2.13.3.tar.xz'),
('gnutls-3.8.13','https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-3.8.13.tar.xz'),
('nettle-3.10.2','https://ftp.gnu.org/gnu/nettle/nettle-3.10.2.tar.gz'),
('dxvk-2.6.2','https://codeload.github.com/doitsujin/dxvk/tar.gz/refs/tags/v2.6.2'),
('mono-cecil-0.11.6','https://codeload.github.com/jbevain/cecil/tar.gz/refs/tags/0.11.6'),
('lapy-local-base','https://codeload.github.com/mpereiraesaa/PS5-Lapy-JB-Daemon/tar.gz/b48b7d7236eca25c7b9dfd6c040c763ae05dde80'),
]

def fetch(item,root,expected=None):
    name,url=item;suffix='.tar.xz'if url.endswith('.xz')else'.tar.gz';p=root/(name+suffix)
    if not p.exists():
        for attempt in range(3):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'Port-Studio-open-source-release'})
                with urllib.request.urlopen(req,timeout=120)as src,p.with_suffix(p.suffix+'.partial').open('wb')as dest:shutil.copyfileobj(src,dest,1<<20)
                p.with_suffix(p.suffix+'.partial').replace(p);break
            except Exception:
                if attempt==2:raise
                time.sleep(2)
    with p.open('rb')as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    if expected and digest!=expected:raise ValueError('Source checksum differs: '+name)
    print(name,p.stat().st_size,digest,flush=True)
    return {'name':name,'url':url,'file':p.name,'sha256':digest,'bytes':p.stat().st_size}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('output',type=Path);ap.add_argument('--lock',type=Path)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    entries=ENTRIES if not a.lock else [(x['name'],x['url'])for x in json.loads(a.lock.read_text())['archives']]
    wanted={}if not a.lock else{x['name']:x['sha256']for x in json.loads(a.lock.read_text())['archives']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
        futures=[pool.submit(fetch,x,a.output,wanted.get(x[0]))for x in entries]
        results=[f.result()for f in futures]
    (a.output/'sources.lock.json').write_text(json.dumps({'schema':1,'archives':results},indent=2)+'\n',encoding='utf8')
