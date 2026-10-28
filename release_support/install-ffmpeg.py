"""Optional, explicit download from the upstream binary distributor; no game data."""
from pathlib import Path
import hashlib,io,os,sys,tempfile,urllib.request,zipfile
R=Path(__file__).resolve().parents[1]
URL='https://github.com/GyanD/codexffmpeg/releases/download/2026-10-22-git-bf0e831606/ffmpeg-2026-10-22-git-bf0e831606-essentials_build.zip'
EXPECTED='966294d1e6c44e98c523f0c0e93d0c7f2a9c682d4b990621dd0b8aa7ab6228f3'
OUT=R/'tools/port-studio-audio/ffmpeg/ffmpeg.exe'
def sha(b):return hashlib.sha256(b).hexdigest()
def install(out=OUT,log=print):
    out=Path(out)
    if out.exists():
        if not out.is_file()or sha(out.read_bytes())!=EXPECTED:
            raise ValueError('FFmpeg existente difere da versão verificada. Preserve/renomeie o arquivo antes de instalar: '+str(out))
        log('FFmpeg já instalado e verificado.');return out
    log('Baixando FFmpeg opcional diretamente de GyanD. Versão, licença e fontes: tools/port-studio-audio/ffmpeg/README.txt')
    req=urllib.request.Request(URL,headers={'User-Agent':'Port-Station'})
    with urllib.request.urlopen(req,timeout=180)as f:data=f.read(250*1024*1024+1)
    if len(data)>250*1024*1024:raise ValueError('Arquivo de download maior que o limite.')
    with zipfile.ZipFile(io.BytesIO(data))as z:
        matches=[x for x in z.infolist()if x.filename.endswith('/bin/ffmpeg.exe')and x.file_size<200*1024*1024]
        if len(matches)!=1:raise ValueError('Estrutura inesperada no download do FFmpeg.')
        binary=z.read(matches[0])
    if sha(binary)!=EXPECTED:raise ValueError('SHA-256 do FFmpeg diferente do esperado; nada foi instalado.')
    out.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=out.parent,prefix='.ffmpeg-',suffix='.download',delete=False)as f:
            temporary=Path(f.name);f.write(binary);f.flush();os.fsync(f.fileno())
        if out.exists():
            if not out.is_file()or sha(out.read_bytes())!=EXPECTED:raise ValueError('Outro arquivo apareceu no destino; foi preservado.')
        elif os.name=='nt':
            temporary.rename(out)  # Windows rename refuses to replace a concurrently created destination.
        else:
            os.link(temporary,out)  # Atomic no-replace publication on other hosts.
        log('FFmpeg instalado e verificado. O encoder ATRAC9 já acompanha o kit.')
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return out

def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',line_buffering=True)
    try:install();return 0
    except (OSError,ValueError,zipfile.BadZipFile)as e:
        print('ERRO: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
