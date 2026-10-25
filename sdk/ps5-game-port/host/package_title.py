"""Package an already linked native title folder; never compiles Unity content."""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import zipfile
import zlib

p = argparse.ArgumentParser()
p.add_argument('--directory', type=Path, required=True)
p.add_argument('--workspace', type=Path, required=True)
p.add_argument('--title-id', required=True)
p.add_argument('--title-name', required=True)
p.add_argument('--content-note', default='No supplied game dump, firmware or Unity runtime is included.')
p.add_argument('--heap-mib', type=int, default=0)
a = p.parse_args()
if not re.fullmatch(r'PPSA[0-9]{5}', a.title_id): raise SystemExit('Invalid title ID')
title = a.directory.resolve()
if not (title/'eboot.bin').is_file() or not (title/'sce_module/libc.prx').is_file():
    raise SystemExit('Native eboot.bin and generated libc.prx required')
if struct.unpack_from('<I', (title/'eboot.bin').read_bytes())[0] != 0x1D3D154F:
    raise SystemExit('Unexpected FSELF container magic')
system = title/'sce_sys'; system.mkdir(exist_ok=True)
param = {
    'ageLevel': {'default': 0}, 'applicationCategoryType': 0,
    'applicationDrmType': 'free', 'attribute': 0, 'attribute2': 0, 'attribute3': 0,
    'conceptId': a.title_id[4:], 'contentBadgeType': 1,
    'contentId': f'UP9000-{a.title_id}_00-GAMEPORTSDK00001', 'contentVersion': '01.000.001',
    'downloadDataSize': 256,
    'localizedParameters': {'defaultLanguage': 'en-US', 'en-US': {'titleName': a.title_name}},
    'masterVersion': '01.00', 'requiredSystemSoftwareVersion': '0x0000000000000000',
    'sdkVersion': '0x0000000000000000', 'titleId': a.title_id, 'versionFileUri': '',
}
(system/'param.json').write_text(json.dumps(param, indent=2)+'\n', encoding='utf-8')
def chunk(kind, data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',binascii.crc32(kind+data)&0xffffffff)
rows = bytearray()
for y in range(512):
    rows.append(0)
    for x in range(512):
        color = (35,190,170,255) if 64 <= x < 448 and 64 <= y < 448 and ((x//64+y//64)%2) else (15,25,45,255)
        rows.extend(color)
png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',512,512,8,6,0,0,0))
png += chunk(b'IDAT',zlib.compress(bytes(rows),9))+chunk(b'IEND',b'')
(system/'icon0.png').write_bytes(png)
licenses = title/'licenses'; licenses.mkdir(exist_ok=True)
shutil.copyfile(a.workspace/'tools/PS5_Vulkan/LICENSE', licenses/'GPL-3.0.txt')
heap_notice = ('Owned application heap: adapted from BlackBearReloaded, GPL-3.0-or-later.\n'
    'https://github.com/Swordpdf/ProsperoEden/blob/a26ba788222465ec7fb94dc813958fc749734e07/third_party/app_heap.c\n'
    'Corresponding local changes: sdk/ps5-game-port/runtime/heap.c and heap.h.\n'
    f'Configured process-lifetime application heap: {a.heap_mib} MiB.\n') if a.heap_mib else ''
(licenses/'NOTICE.txt').write_text(
    'PS5 Game Port SDK integration and original code-generated icon.\n'
    'CRT/native conversion/generated libc runtime: BlackBearReloaded/Mihawk-99, GPL-3.0-or-later.\n'
    'https://github.com/mihawk-99/PS5_Vulkan/tree/f410e67a0241b3e8edcdbcd2a9b285dfc4a412ed/tooling/native\n'
    'Public PS5 Payload SDK v0.44: John Tornblom and contributors, GPL/BSD components.\n'
    'https://github.com/ps5-payload-dev/sdk\n'
    'Corresponding local sample/integration sources: sdk/ps5-game-port and src/native_runtime.c.\n'
    + heap_notice + a.content_note + '\n', encoding='utf-8')
manifest = dict(title_id=a.title_id, build_scope='native homebrew; no Unity Player', files={})
for path in sorted(title.rglob('*')):
    if path.is_file(): manifest['files'][path.relative_to(title).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
(title.parent/(a.title_id+'-manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
archive = title.parent/(a.title_id+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as out:
    for path in sorted(title.rglob('*')):
        if not path.is_file(): continue
        info = zipfile.ZipInfo(path.relative_to(title.parent).as_posix(), (2026,10,20,0,0,0))
        info.create_system = 3; info.external_attr = 0o100777 << 16; info.compress_type = zipfile.ZIP_DEFLATED
        out.writestr(info,path.read_bytes())
print(archive)
