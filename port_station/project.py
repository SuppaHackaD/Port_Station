"""Versioned project model. Paths are relative to the project, not the shell cwd."""
from __future__ import annotations
import copy
import json
import re
from pathlib import Path, PurePosixPath

WORKSPACE = Path(__file__).resolve().parents[1]
PROFILES = ("dxvk-xinput", "opengl-xinput", "nwjs-canvas", "gdi-keyboard")
ADAPTERS = ("none", "file-v1", "file-markers", "unity-mono-steam", "nwjs-steam", "breath")
BREATH_IDS = {"COROA", "OCULOS", "SONIC", "OLHOSARANHA", "ARANHA", "ENGUIA", "MORCEGO", "TARTARUGA", "THEEND", "BUG", "SPEEDRUN"}

class ProjectError(ValueError):
    pass

def default_project():
    return dict(schema=1, title="Meu jogo", title_id="PPSA99410", game_id="meu.jogo",
                version="01.000.001", game_dir="", executable="Game.exe",
                profile="dxvk-xinput", arguments="", display_resolution="auto", adapter="none", catalog_version=1,
                icon="", background="", launch_background="", sound="", audio_start=0.0, audio_duration=15.0,
                platinum=False, platinum_id="PLATINUM", platinum_title="Conjunto completo",
                platinum_description="Obtenha todas as outras conquistas.", platinum_icon="",
                achievements=[], overlays=[], profile_options={}, file_markers={}, file_marker_content='empty', age=0)

def read_project(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as e:
        raise ProjectError(f"Projeto ilegível: {e}") from e
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ProjectError("Formato de projeto desconhecido (schema esperado: 1).")
    result = default_project()
    result.update(value)
    return result

def write_project(path, project):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    temp.replace(path)

def resolve_path(value, base):
    if not value:
        raise ProjectError("Caminho não informado.")
    return Path(value.replace("${workspace}", str(WORKSPACE))).expanduser().resolve() if value.startswith("${workspace}") else (Path(base) / value).resolve()

def relative_file(value):
    """Restrict package paths to portable Windows filenames below the game root."""
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProjectError(f"Use um caminho relativo com /: {value!r}")
    parts = value.split("/")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}
    if '..' in value or any(x in ("", ".", "..") or re.search(r'[<>:"|?*\x00-\x1f]', x) or x.endswith((".", " ")) or x.split(".")[0].upper() in reserved for x in parts):
        raise ProjectError(f"Caminho não portável: {value!r}")
    if len(value.encode("utf8")) > 480:
        raise ProjectError("Caminho longo demais para o bootstrap.")
    return PurePosixPath(value)

def valid_id(value, lower=False):
    return isinstance(value, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}" if lower else r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value)) and ".." not in value

def runtime_id(project):
    """Wine IDs exclude dots; the achievement namespace keeps its original ID."""
    return project['game_id'].replace('.', '-')

def validate_resolution(value):
    if value == 'auto':return value
    if not isinstance(value,str) or not re.fullmatch(r'[1-9][0-9]{2,3}x[1-9][0-9]{2,3}',value):
        raise ProjectError('Resolução: use auto ou largura x altura sem espaços, como 1920x1080.')
    width,height=map(int,value.split('x'))
    if not 320<=width<=3840 or not 200<=height<=2160:
        raise ProjectError('Resolução fora do limite do runtime: 320x200 a 3840x2160.')
    return value

def text(value, label, maximum):
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf8")) > maximum or "\0" in value:
        raise ProjectError(f"{label}: texto vazio ou maior que {maximum} bytes UTF-8.")

def validate(project, base, files=True):
    p = project
    from .audio import validate_options
    validate_options(p.get('audio_start',0),p.get('audio_duration',15))
    if p.get("schema") != 1: raise ProjectError("Schema inválido.")
    if not re.fullmatch(r"PPSA\d{5}", p["title_id"]): raise ProjectError("Title ID deve ser PPSA + 5 dígitos.")
    if not valid_id(p["game_id"], True) or len(p["game_id"]) > 32: raise ProjectError("game_id: 1–32 caracteres minúsculos, números, ponto, _ ou -.")
    text(p["title"], "Título", 256)
    if any(c in p["title"] for c in "\r\n;"): raise ProjectError("Título deve ter uma linha e não conter ponto e vírgula.")
    if not re.fullmatch(r"\d{2}\.\d{3}\.\d{3}", p["version"]): raise ProjectError("Versão deve seguir 01.000.001.")
    if p["profile"] not in PROFILES or p["adapter"] not in ADAPTERS: raise ProjectError("Perfil/adaptador desconhecido.")
    validate_resolution(p.get('display_resolution','auto'))
    if not isinstance(p["age"], int) or not 0 <= p["age"] <= 18: raise ProjectError("Idade deve estar entre 0 e 18.")
    if type(p["catalog_version"]) is not int or p["catalog_version"] < 1: raise ProjectError("Versão do catálogo deve ser um inteiro positivo.")
    if any(c in p["arguments"] for c in "\r\n\0"): raise ProjectError("Argumentos devem ocupar uma linha.")
    exe = relative_file(p["executable"])
    if exe.suffix.lower() != ".exe": raise ProjectError("Selecione um executável Windows .exe.")
    if type(p['platinum']) is not bool: raise ProjectError('platinum deve ser booleano.')
    if not isinstance(p["achievements"], list) or len(p["achievements"]) + bool(p["platinum"]) > 256: raise ProjectError("Máximo: 256 conquistas, incluindo platina.")
    ids = set(); aliases = set()
    for a in p["achievements"]:
        if not valid_id(a.get("id")) or a["id"] in ids: raise ProjectError("IDs de conquista inválidas ou duplicadas.")
        ids.add(a["id"]); text(a.get("title"), "Nome da conquista", 256)
        if not isinstance(a.get("description", ""), str) or len(a.get("description", "").encode("utf8")) > 2048: raise ProjectError("Descrição excede 2048 bytes.")
        if type(a.get('hidden',False)) is not bool:raise ProjectError('hidden deve ser booleano.')
        if type(a.get('target',1)) is not int or a.get("target", 1) != 1: raise ProjectError("Os adaptadores desta versão enviam unlock; use target=1.")
        alias = a.get("source_id", a["id"])
        if not isinstance(alias, str) or not alias or len(alias.encode('utf8'))>256 or any(ord(c)<32 for c in alias) or alias in aliases: raise ProjectError("IDs de origem devem ser únicas, sem controles e até 256 bytes.")
        aliases.add(alias)
    for a in p['achievements']:
        alias=a.get('source_id',a['id'])
        if alias in ids and alias!=a['id']:raise ProjectError('ID de origem colide com a ID canônica de outra conquista.')
    if p["platinum"]:
        if not ids: raise ProjectError("Platina precisa de pelo menos uma conquista regular.")
        if not valid_id(p["platinum_id"]) or p["platinum_id"] in ids: raise ProjectError("ID da platina inválida ou duplicada.")
        text(p["platinum_title"], "Título da platina", 256)
        if len(p["platinum_description"].encode("utf8")) > 2048: raise ProjectError("Descrição da platina longa demais.")
    if p["adapter"] != "none" and not ids: raise ProjectError("O adaptador precisa de um catálogo.")
    if p["adapter"] == "none" and ids: raise ProjectError("Escolha um adaptador para enviar o catálogo/conquistas.")
    if p["adapter"] == "breath" and ids != BREATH_IDS: raise ProjectError("O adaptador Breath requer as 11 IDs originais de conquistas; a ID do jogo pode ser personalizada.")
    if p["adapter"] == "nwjs-steam" and p["profile"] != "nwjs-canvas": raise ProjectError("Adaptador NW.js requer o perfil nwjs-canvas.")
    markers=p.get('file_markers',{})
    if p.get('file_marker_content','empty') not in ('empty','crlf'):
        raise ProjectError('file_marker_content deve ser empty ou crlf.')
    if p.get('file_marker_content','empty')!='empty' and p['adapter']!='file-markers':
        raise ProjectError('file_marker_content exige o adaptador file-markers.')
    if not isinstance(markers,dict):raise ProjectError('file_markers deve mapear IDs para caminhos relativos dentro de drive_c.')
    if p['adapter']=='file-markers':
        if set(markers)!=ids:raise ProjectError('file-markers exige um caminho para cada ID regular do catálogo.')
        paths=set()
        for name in markers.values():
            relative_file(name)
            if name.casefold()in paths:raise ProjectError('Marcadores de conquistas devem ter caminhos distintos.')
            paths.add(name.casefold())
    elif markers:raise ProjectError('file_markers exige o adaptador file-markers.')
    options = p["profile_options"]
    if not isinstance(options, dict): raise ProjectError("profile_options deve ser objeto JSON.")
    allowed = {"application": {"dll_overrides"}, "display": {"desktop", "scaling", "view", "show_fps"}, "input": {"mode", "mouse", "mouse_speed", "left_stick", "cross", "circle", "square", "triangle", "l1", "r1", "l2", "r2", "l3", "r3", "up", "down", "left", "right", "options", "create", "touchpad"}, "runtime": {"thread_scheduling", "cpu"}, "debug": {"winedebug"}}
    for section, fields in options.items():
        if section not in allowed or not isinstance(fields, dict): raise ProjectError(f"Seção de perfil inválida: {section}")
        for key, value in fields.items():
            if key not in allowed[section] or not isinstance(value, str) or any(c in value for c in "\r\n\0"): raise ProjectError(f"Opção de perfil inválida: {section}.{key}")
            if section=='display' and key=='desktop':
                if value=='auto':raise ProjectError('Para resolução automática, remova display.desktop de Avançado e escolha auto na aba Jogo.')
                validate_resolution(value)
    input_options = options.get('input', {})
    if input_options.get('left_stick', 'none') not in ('none', 'dpad'):
        raise ProjectError('input.left_stick deve ser none ou dpad.')
    if input_options.get('left_stick') == 'dpad' and input_options.get('mode') != 'keyboard':
        raise ProjectError('input.left_stick=dpad exige input.mode=keyboard explícito.')
    if not isinstance(p['overlays'],list):raise ProjectError('overlays deve ser uma lista.')
    destinations=set()
    for entry in p["overlays"]:
        relative_file(entry["destination"])
        key=entry['destination'].casefold()
        if key in destinations:raise ProjectError('Overlays com destinos duplicados.')
        destinations.add(key)
        if files and not resolve_path(entry["source"], base).is_file(): raise ProjectError(f"Overlay ausente: {entry['source']}")
    if files:
        game = resolve_path(p["game_dir"], base)
        if not game.is_dir() or not (game / exe).is_file(): raise ProjectError("Pasta do jogo/executável não encontrado.")
        if not p["icon"]: raise ProjectError("Escolha o ícone do jogo (sem placeholder automático).")
        for value in [p[k] for k in ("icon", "background", "launch_background", "sound", "platinum_icon")] + [a.get("icon", "") for a in p["achievements"]]:
            if value and not resolve_path(value, base).is_file(): raise ProjectError(f"Arquivo ausente: {value}")
        if p["adapter"] == "nwjs-steam" and not (game / "www/index.html").is_file(): raise ProjectError("NW.js: www/index.html não encontrado.")
        from .nwjs import validate_inputs as validate_nwjs
        validate_nwjs(p,game)
        from .love import inspect as inspect_love
        inspect_love(p,game)
    return p

def pe_architecture(path):
    import struct
    with Path(path).open("rb") as f:
        header = f.read(64)
        if len(header) != 64 or header[:2] != b"MZ": raise ProjectError("Executável não é PE Windows.")
        f.seek(struct.unpack_from("<I", header, 60)[0]); value = f.read(6)
    if len(value) != 6 or value[:4] != b"PE\0\0": raise ProjectError("Cabeçalho PE inválido.")
    machine = struct.unpack_from("<H", value, 4)[0]
    if machine not in (0x14c, 0x8664): raise ProjectError("Somente executáveis x86 ou x64 são suportados.")
    return "pe32" if machine == 0x14c else "pe64"
