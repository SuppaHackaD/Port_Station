"""Bounded LÖVE/ZIP and LuaJIT constant reader. Never loads a Lua runtime."""
from pathlib import PurePosixPath
import re
import struct
import zipfile

IDENTIFIER=re.compile(r'[A-Za-z_][A-Za-z0-9_.-]{1,127}\Z')


def luajit_strings(data):
    """Read string/table constants in dump v1/v2, not instructions or control flow."""
    pos=0;limit=len(data);strings=[];prototypes=0
    def take(n):
        nonlocal pos
        if n<0 or pos+n>limit:raise ValueError('LuaJIT truncado ou comprimento inválido')
        start=pos;pos+=n;return data[start:pos]
    def number(bits=32):
        value=0
        for shift in range(0,bits,7):
            byte=take(1)[0];value|=(byte&127)<<shift
            if not byte&128:
                if value>=(1<<bits):raise ValueError('Inteiro LuaJIT fora do limite')
                return value
        raise ValueError('Inteiro LuaJIT malformado')
    def string(size):
        offset=pos;raw=take(size)
        try:text=raw.decode('utf-8')
        except UnicodeError:return
        if IDENTIFIER.fullmatch(text):strings.append((text,offset))
    def table_value():
        kind=number()
        if kind>=5:string(kind-5)
        elif kind==3:number()
        elif kind==4:number();number()
        elif kind not in (0,1,2):raise ValueError('Constante de tabela LuaJIT inválida')
    if take(3)!=b'\x1bLJ':raise ValueError('Não é um dump LuaJIT')
    version=take(1)[0]
    if version not in (1,2):raise ValueError('Versão LuaJIT não suportada')
    flags=number()
    if flags&~(7 if version==1 else 31):raise ValueError('Flags LuaJIT não suportadas')
    if not flags&2:take(number())
    while True:
        size=number()
        if not size:break
        end=pos+size
        if end>len(data):raise ValueError('Protótipo LuaJIT truncado')
        limit=end;prototypes+=1
        if prototypes>100000:raise ValueError('Limite de protótipos LuaJIT')
        header=take(4);uv=header[3]
        kgc,kn,bc=number(),number(),number()
        if max(kgc,kn,bc)>1000000:raise ValueError('Contagem LuaJIT acima do limite')
        debug=0
        if not flags&2:
            debug=number()
            if debug:number();number()
        take(bc*4+uv*2)
        for _ in range(kgc):
            kind=number()
            if kind>=5:string(kind-5)
            elif kind==1:
                array,hashed=number(),number()
                if array+2*hashed>1000000:raise ValueError('Tabela LuaJIT acima do limite')
                for _ in range(array+2*hashed):table_value()
            elif kind in (2,3):number();number()
            elif kind==4:
                for _ in range(4):number()
            elif kind!=0:raise ValueError('Constante LuaJIT inválida')
        for _ in range(kn):
            floating=data[pos]&1 if pos<limit else False
            number(33)
            if floating:number()
        take(debug)
        if pos!=end:raise ValueError('Tamanho de protótipo LuaJIT inconsistente')
        limit=len(data)
    if pos!=len(data):raise ValueError('Dados extras no dump LuaJIT')
    return strings


def archive_members(path,max_entries=12000,max_file=8*1024*1024,max_total=128*1024*1024):
    """Read selected members in place, including ZIP appended to a PE. No extraction."""
    with open(path,'rb')as f:
        f.seek(0,2);size=f.tell();f.seek(max(0,size-65557));tail=f.read()
    eocd=tail.rfind(b'PK\x05\x06')
    if eocd<0:return
    if eocd+22>len(tail):raise ValueError('Diretório ZIP truncado')
    fields=struct.unpack_from('<4s4H2IH',tail,eocd)
    if fields[1] or fields[2] or fields[3]!=fields[4]:raise ValueError('ZIP multipartes não suportado')
    if fields[4]>max_entries or fields[5]>8*1024*1024:raise ValueError('Diretório ZIP acima do limite')
    used=0;seen=set()
    with zipfile.ZipFile(path)as archive:
        for item in archive.infolist():
            name=item.filename
            if item.is_dir():continue
            if name.casefold() in seen:raise ValueError('Nomes duplicados no pacote ZIP')
            seen.add(name.casefold())
            parts=PurePosixPath(name).parts
            if name.startswith('/')or '\\'in name or ':'in name or '..'in parts or any(ord(c)<32 for c in name):
                raise ValueError('Nome de membro ZIP inválido')
            if PurePosixPath(name).suffix.lower()not in ('.lua','.json','.vdf','.js','.cjs','.mjs'):continue
            if item.flag_bits&1:raise ValueError('Membro ZIP criptografado não suportado')
            if item.file_size>max_file or used+item.file_size>max_total:raise ValueError('Leitura do pacote ZIP acima do limite')
            if item.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):raise ValueError('Compressão ZIP não suportada')
            with archive.open(item)as stream:data=stream.read(max_file+1)
            if len(data)!=item.file_size:raise ValueError('Tamanho de membro ZIP inconsistente')
            used+=len(data)
            yield name,data
