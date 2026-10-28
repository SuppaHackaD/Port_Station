"""NW.js/Wine compatibility applied to the package copy, never to PC originals."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import zlib
from .assets import Image
from PIL import ImageFont
from .project import ProjectError

TC_IDS={'EP1_CLEAR','HITMAN_WINS','VISION_WATCHER','PRESENT','SUMMON_LU','EP2_CLEAR','WARDEN_WINS','TIME_CAPSULE','UNDETECTED','NO_WITNESSES','HAPPY_END','PROPHECY_FULFILLER','LEYLEYWINS_END','FULL_MARKS','SISTER_SLAUGHTERER','SPLAT','SHOTSEND','MATH','EP3D_CLEAR','TRUEEND'}
FONT_SECTIONS=[r'Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts',r'Software\\Wow6432Node\\Microsoft\\Windows NT\\CurrentVersion\\Fonts',r'Software\\Microsoft\\Windows\\CurrentVersion\\Fonts']
TC_LANGUAGE='www/data/9c7050ae76645487'
TC_LANGUAGE_SHA256='8322e3d5da5525f16bc0ff3ce050664562260dc2557bcef9291686e4ce0787dc'


def is_tcoaal(game):
    try:package=json.loads((Path(game)/'package.json').read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return False
    return package.get('name')=='The Coffin of Andy and Leyley'and package.get('main')=='www/index.html'


def language_asset(game):
    """Recognize the tested revision; never guess names for other games/versions."""
    game=Path(game)
    if not is_tcoaal(game):return None
    try:main=(game/'www/js/main.js').read_text(encoding='utf-8-sig')
    except OSError:return None
    if not re.search(r'\bGAME_VERSION\s*=\s*[\'"]3\.0\.13[\'"]',main):return None
    canonical=game/TC_LANGUAGE
    source=canonical if canonical.is_file()else canonical.with_suffix('.txt')
    if not source.is_file():
        raise ProjectError('TCOAAL: base de idioma ausente: '+TC_LANGUAGE+'. Restaure os arquivos da sua cópia do jogo.')
    if not 8<source.stat().st_size<=4*1024*1024:raise ProjectError('TCOAAL: tamanho inválido da base de idioma.')
    data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
    if source!=canonical and digest!=TC_LANGUAGE_SHA256:
        raise ProjectError('TCOAAL: a base de idioma está com extensão .txt e difere da revisão verificada. Restaure o arquivo original sem extensão: '+TC_LANGUAGE)
    try:
        if not data.startswith(b'LANGDATA'):raise ValueError('header')
        catalog=json.loads(data[8:])
        if not isinstance(catalog,dict)or not isinstance(catalog.get('linesLUT'),dict)or not isinstance(catalog.get('labelLUT'),dict):raise ValueError('schema')
    except (ValueError,UnicodeError)as error:raise ProjectError('TCOAAL: base de idioma inválida: '+str(source))from error
    return source,data,digest


def validate_inputs(project,game):
    if project['profile']!='nwjs-canvas':return
    language_asset(game)
    if is_tcoaal(game)and project['adapter']=='nwjs-steam':
        from .project import BREATH_IDS
        if {a['id']for a in project['achievements']}==BREATH_IDS and all(a.get('source_id',a['id'])==a['id']for a in project['achievements']):
            raise ProjectError('TCOAAL: o catálogo selecionado contém as 11 conquistas de Breath. Importe a lista do TCOAAL na aba Conquistas antes de compilar.')


def prepare_language_assets(game,out):
    asset=language_asset(game)
    if asset is None:return {},{}
    source,data,digest=asset;target=Path(out)/TC_LANGUAGE
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return {TC_LANGUAGE:target},{'source':source.relative_to(game).as_posix(),'destination':TC_LANGUAGE,
                                'sha256':digest,'bytes':len(data),'restored_name':source.name!=target.name,'source_modified':False}

def register_font(reg,display,filename):
    def quoted(s):return ('"'+s.replace('\\','\\\\').replace('"','\\"')+'"').encode('utf8')
    key=quoted(display+' (TrueType)');entry=key+b'='+quoted(filename)+b'\n'
    for section in FONT_SECTIONS:
        header=b'['+section.encode('ascii')+b']'
        matches=list(re.finditer(rb'(?m)^'+re.escape(header)+rb'[^\n]*\n',reg))
        if len(matches)>1:raise ProjectError('Registro Wine contém seções de fonte duplicadas.')
        if not matches:reg+=b'\n'+header+b'\n'+entry;continue
        start=matches[0].end();end=reg.find(b'\n[',start);end=len(reg)if end<0 else end
        block=reg[start:end];lines=list(re.finditer(rb'(?m)^'+re.escape(key)+rb'=[^\n]*(?:\n|$)',block))
        if len(lines)>1:raise ProjectError('Registro Wine contém a mesma fonte repetida.')
        if lines:
            m=lines[0];block=block[:m.start()]+entry+block[m.end():];reg=reg[:start]+block+reg[end:]
        else:reg=reg[:start]+entry+reg[start:]
    return reg

def prepare_fonts(game,prefix):
    game=Path(game).resolve();prefix=Path(prefix);system=prefix/'system.reg'
    reg=system.read_bytes();report={'fonts':[],'css':[]};installed={}
    fonts=prefix/'drive_c/windows/Fonts';fonts.mkdir(parents=True,exist_ok=True)
    for css in sorted((game/'www').rglob('*.css')):
        original=css.read_bytes()
        try:text=original.decode('utf8')
        except UnicodeDecodeError:continue
        def face(match):
            nonlocal reg
            block=match.group(0)
            source=re.search(r'\bsrc\s*:\s*([^;]+);',block,re.I)
            if not source:return block
            has_local=bool(re.search(r'\blocal\s*\(',source.group(1),re.I))
            for url in re.finditer(r'url\(\s*([\'"]?)([^)\'"\s]+)\1\s*\)',source.group(1),re.I):
                relative=url.group(2)
                if ':'in relative or '?'in relative or '#'in relative:continue
                path=(css.parent/relative).resolve()
                if not path.is_relative_to(game)or path.suffix.lower()not in ('.ttf','.otf')or not path.is_file():continue
                try:family,style=ImageFont.truetype(str(path),16).getname()
                except OSError as e:raise ProjectError('Não foi possível ler a fonte NW.js: '+str(path))from e
                full=(family+' '+style).strip()
                if any(ord(c)<32 for c in full):raise ProjectError('Nome de fonte inválido.')
                data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();filename=path.name
                if (fonts/filename).exists()and (fonts/filename).read_bytes()!=data:filename='portstudio-'+digest[:16]+path.suffix.lower()
                (fonts/filename).write_bytes(data);reg=register_font(reg,full,filename)
                if digest not in installed:
                    installed[digest]=True;report['fonts'].append({'source':path.relative_to(game).as_posix(),'destination':'drive_c/windows/Fonts/'+filename,'family':family,'full_name':full,'sha256':digest})
                if has_local:return block
                names=list(dict.fromkeys([full,family]));local=', '.join('local('+json.dumps(n,ensure_ascii=False)+')'for n in names)+', '
                value=source.group(1);pos=source.start(1)+len(value)-len(value.lstrip())
                return block[:pos]+local+block[pos:]
            return block
        updated=re.sub(r'@font-face\s*\{[^{}]*\}',face,text,flags=re.I).encode('utf8')
        if updated!=original:
            css.write_bytes(updated);report['css'].append({'path':css.relative_to(game).as_posix(),'before_size':len(original),'before_crc':zlib.crc32(original),'after_size':len(updated),'after_crc':zlib.crc32(updated),'before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':hashlib.sha256(updated).hexdigest()})
    if reg!=system.read_bytes():system.write_bytes(reg)
    return report

def achievement_aliases(project,game):
    aliases={a.get('source_id',a['id']):a['id']for a in project['achievements']}
    try:package=json.loads((Path(game)/'package.json').read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return aliases
    if package.get('name')=='The Coffin of Andy and Leyley'and package.get('main')=='www/index.html':
        for a in project['achievements']:
            if a['id']in TC_IDS:
                source=a['id'].lower()
                if source in aliases and aliases[source]!=a['id']:raise ProjectError('Alias TCOAL conflitante: '+source)
                aliases[source]=a['id']
    return aliases
