"""Bundled, offline transcoding into the PS5 selection-music profile."""
from pathlib import Path
import hashlib
import json
import math
import tempfile
from .project import WORKSPACE, ProjectError

TOOLS=WORKSPACE/'tools/port-studio-audio'
FFMPEG=TOOLS/'ffmpeg/ffmpeg.exe'
ENCODER=TOOLS/'port-at9-encode.exe'

def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def validate_options(start,duration):
    for value,label in [(start,'Início'),(duration,'Duração')]:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ProjectError(label+': informe segundos em formato numérico.')
    if not 0<=start<=86400:raise ProjectError('Início do áudio: use de 0 a 86400 segundos.')
    if not 0.1<=duration<=87.3:raise ProjectError('Duração do áudio: use de 0,1 a 87,3 segundos (limite de 2 MiB a 192 kb/s).')

def check_tools():
    receipt=TOOLS/'build.json'
    try:
        data=json.loads(receipt.read_text(encoding='utf8'))
        if not isinstance(data,dict)or not isinstance(data.get('files'),dict):raise ValueError('files')
    except (OSError,ValueError)as e:
        raise ProjectError('Manifesto das ferramentas de áudio ausente ou inválido. Restaure tools/port-studio-audio do kit Windows.')from e
    for path in [FFMPEG,ENCODER]:
        expected=data['files'].get(path.relative_to(WORKSPACE).as_posix())
        if not isinstance(expected,str)or len(expected)!=64:raise ProjectError('Manifesto de áudio incompleto. Restaure tools/port-studio-audio do kit Windows.')
        if not path.is_file():
            if path==FFMPEG:
                raise ProjectError('FFmpeg opcional não instalado. Na aba Áudio, clique em “Instalar FFmpeg…” ou execute python release_support/install-ffmpeg.py na pasta do kit.')
            raise ProjectError('Encoder ATRAC9 ausente. Restaure tools/port-studio-audio do kit Windows: '+str(path))
        if sha(path)!=expected:
            if path==FFMPEG:
                raise ProjectError('O FFmpeg instalado difere da versão verificada. Preserve/renomeie esse arquivo e instale a versão indicada por release_support/install-ffmpeg.py: '+str(path))
            raise ProjectError('Encoder ATRAC9 diferente do build verificado. Restaure o arquivo do kit Windows: '+str(path))
    return data

def transcode(source,destination,run,log=print,start=0,duration=15):
    """Prepare a bounded clip, validate it, then publish it without replacing files."""
    from .assets import validate_at9
    source=Path(source).resolve();destination=Path(destination).resolve()
    validate_options(start,duration)
    if not source.is_file():raise ProjectError('Arquivo de áudio não encontrado.')
    if source==destination or destination.exists():raise ProjectError('Escolha um novo arquivo .at9 de saída; arquivos existentes são preservados.')
    if destination.suffix.lower()!='.at9':raise ProjectError('O arquivo de saída deve terminar em .at9.')
    original_hash=sha(source)
    if source.suffix.lower()=='.at9':
        data=source.read_bytes();validate_at9(data)
        report={'mode':'validated copy','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'final_lufs':None,'clip_options_applied':False}
    else:
        tools=check_tools()
        with tempfile.TemporaryDirectory(prefix='port-studio-audio-')as temp:
            temp=Path(temp);pcm=temp/'clip.f64';encoded=temp/'snd0.at9';metadata=temp/'encoder.json'
            log(f'Áudio: selecionando até {duration:g} s a partir de {start:g} s…')
            run([FFMPEG,'-hide_banner','-loglevel','error','-nostdin','-y','-protocol_whitelist','file,pipe','-ss',format(start,'.9g'),'-i',source,'-t',format(duration,'.9g'),'-map','0:a:0','-vn','-sn','-dn','-map_metadata','-1','-af','asetpts=PTS-STARTPTS','-ar','48000','-ac','2','-c:a','pcm_f64le','-f','f64le',pcm])
            size=pcm.stat().st_size
            if not size or size%16 or size>round(87.3*48000)*16:raise ProjectError('Trecho vazio, incompleto ou maior que o limite. Confira o início e a duração.')
            log('Áudio: normalização, fades e encoder ATRAC9 local…')
            run([ENCODER,pcm,encoded,metadata])
            report=json.loads(metadata.read_text(encoding='utf8'));data=encoded.read_bytes();validate_at9(data)
            report.update(mode='transcoded',start_seconds=start,requested_duration=duration,clip_options_applied=True,encoder_revision=tools['encoder']['revision'],encoder_sha256=tools['files'][ENCODER.relative_to(WORKSPACE).as_posix()],ffmpeg_sha256=tools['files'][FFMPEG.relative_to(WORKSPACE).as_posix()],sha256=hashlib.sha256(data).hexdigest())
    if sha(source)!=original_hash:raise ProjectError('O áudio de origem mudou durante a conversão. Tente novamente com um arquivo estável.')
    report['source_sha256']=original_hash
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:
        with destination.open('xb')as out:out.write(data)
    except FileExistsError as e:raise ProjectError('O arquivo de saída já existe; nenhum arquivo foi substituído.')from e
    log(f'Áudio pronto: {len(data):,} bytes, loop ATRAC9 validado.')
    return report

def apply_metadata(param,report):
    if report and isinstance(report.get('final_lufs'),(int,float)) and math.isfinite(report['final_lufs']):
        param.setdefault('pubtools',{})['loudnessSnd0']=format(report['final_lufs'],'.2f')
