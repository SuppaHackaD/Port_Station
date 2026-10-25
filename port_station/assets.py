"""Real PNG / BC7 DDS / ATRAC9 assets; never rename an incompatible format."""
from __future__ import annotations
import hashlib
import io
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from .project import WORKSPACE, ProjectError, resolve_path

sys.path.insert(0, str(WORKSPACE / "tools/trophy-python"))
from PIL import Image, ImageOps

def png_bytes(source, size=256):
    with Image.open(source) as im:
        im = ImageOps.exif_transpose(im).convert("RGBA")
        im = ImageOps.fit(im, (size, size), method=Image.Resampling.LANCZOS)
        out = io.BytesIO(); im.save(out, "PNG", optimize=False)
    return out.getvalue()

def validate_dds(data):
    if len(data) != 148 + 3840 * 2160 or data[:4] != b"DDS " or struct.unpack_from("<I", data, 4)[0] != 124:
        raise ProjectError("Fundo: esperado DDS BC7 3840×2160, uma superfície sem mipmaps.")
    if struct.unpack_from("<II", data, 12) != (2160,3840) or data[84:88] != b"DX10" or struct.unpack_from("<IIIII", data, 128) != (98,3,0,1,0) or struct.unpack_from("<I",data,28)[0] not in (0,1):
        raise ProjectError("Cabeçalho DDS incompatível com o perfil de apresentação.")

def validate_at9(data):
    if len(data) < 128 or len(data) > 2097152 or data[:4] != b"RIFF" or data[8:12] != b"WAVE" or struct.unpack_from("<I",data,4)[0]+8 != len(data):
        raise ProjectError("Som deve ser um RIFF ATRAC9 completo, até 2 MiB.")
    chunks = {}; pos=12
    while pos+8 <= len(data):
        kind=data[pos:pos+4]; n=struct.unpack_from("<I",data,pos+4)[0]; pos+=8
        if pos+n > len(data): raise ProjectError("RIFF truncado.")
        chunks[kind]=data[pos:pos+n];pos+=n+(n&1)
    if pos != len(data) or not all(k in chunks for k in (b"fmt ",b"data",b"fact",b"smpl")): raise ProjectError("ATRAC9 sem formato/dados/fact/loop.")
    fmt=chunks[b"fmt "]; loop=chunks[b"smpl"]
    if len(fmt)<40 or len(loop)<60: raise ProjectError("ATRAC9: metadados incompletos.")
    tag,channels,rate,byte_rate=struct.unpack_from("<HHII",fmt)
    if tag!=65534 or channels not in (1,2) or rate!=48000 or not 0<byte_rate<=channels*12000 or fmt[24:40].hex()!="d242e147ba368d4d88fc61654f8c836c" or struct.unpack_from("<I",loop,28)[0]<1:
        raise ProjectError("ATRAC9: use 48 kHz, mono ≤96 kb/s ou estéreo ≤192 kb/s, com loop.")

def prepare_presentation(p, base, destination, run, log):
    destination.mkdir(parents=True,exist_ok=True)
    icon=resolve_path(p["icon"],base)
    (destination/"icon0.png").write_bytes(png_bytes(icon,512))
    selection=p["background"] or p["launch_background"]
    launch=p["launch_background"] or p["background"]
    cache={}
    for key,source in (("pic0",selection),("pic1",launch)):
        if not source: continue
        src=resolve_path(source,base); digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if digest not in cache:
            if src.suffix.lower()==".dds": data=src.read_bytes()
            else:
                tool=WORKSPACE/"build/port-studio/tools/make-app-assets.exe"
                if not tool.is_file(): raise ProjectError("Conversor BC7 ausente. Execute python -m port_station setup.")
                with tempfile.TemporaryDirectory(prefix="port-studio-art-") as temp:
                    # Encoder uses stb; normalize formats/orientation through Pillow first.
                    bg=Path(temp)/"source.png"
                    with Image.open(src) as im: ImageOps.exif_transpose(im).convert("RGBA").save(bg)
                    ico=Path(temp)/"icon.png";ico.write_bytes(png_bytes(icon,512))
                    run([str(tool),"--icon",str(ico),"--background",str(bg),"--out",temp])
                    data=(Path(temp)/"pic0.dds").read_bytes()
            validate_dds(data);cache[digest]=data
        (destination/(key+".dds")).write_bytes(cache[digest])
        log(f"Arte: {key}.dds pronta")
    if p["sound"]:
        src=resolve_path(p["sound"],base)
        from .audio import transcode
        report=transcode(src,destination/'snd0.at9',run,log,p.get('audio_start',0),p.get('audio_duration',15))
        import json
        (destination.parent/'audio-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        return report
    return None

def make_catalog(p, base, destination):
    resources={}
    def description(value):
        # The backend requires nonempty display text. Preserve missing metadata
        # in the project/extractor report; this is only a truthful display label.
        return value if value.strip() else 'Descrição não informada.'
    def resource(path):
        data=png_bytes(resolve_path(path or p["icon"],base)); digest=hashlib.sha256(data).hexdigest();resources[digest]=data;return digest
    catalog=dict(schema=1,game_id=p["game_id"],title=p["title"],catalog_version=p["catalog_version"],icon=resource(p["icon"]),achievements=[])
    for a in p["achievements"]:
        catalog["achievements"].append(dict(id=a["id"],title=a["title"],description=description(a.get("description","")),target=1,hidden=bool(a.get("hidden",False)),icon=resource(a.get("icon"))))
    if p["platinum"]:
        catalog["achievements"].append(dict(id=p["platinum_id"],title=p["platinum_title"],description=description(p["platinum_description"]),target=1,completion=True,icon=resource(p["platinum_icon"])))
    blob=__import__('json').dumps(catalog,ensure_ascii=False,separators=(',',':')).encode('utf8')
    if len(blob)>128*1024: raise ProjectError("Catálogo excede 128 KiB.")
    destination.mkdir(parents=True,exist_ok=True)
    (destination/"catalog.json").write_bytes(blob)
    assets=destination/"assets";assets.mkdir(exist_ok=True)
    for digest,data in resources.items():
        if len(data)>512*1024: raise ProjectError("PNG de conquista excede 512 KiB.")
        (assets/(digest+".png")).write_bytes(data)
    return catalog,resources,blob
