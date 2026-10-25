"""Bounded data readers. Game scripts and executables are never evaluated."""
import json
import re
import struct


def tokens(text, javascript=False):
    """Small lexer for VDF/JS literal calls; interpolated templates stay dynamic."""
    i = 0; previous = None
    while i < len(text):
        c = text[i]
        if c.isspace(): i += 1; continue
        if text.startswith('//', i):
            end = text.find('\n', i); i = len(text) if end < 0 else end + 1; continue
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0: raise ValueError('Comentário não terminado')
            i = end + 2; continue
        start = i
        if javascript and c=='/' and (previous is None or previous[1] in ('=', '(', '[', '{', ',', ':', ';', 'return', '!', '?')):
            i+=1; bracket=False
            while i<len(text):
                char=text[i];i+=1
                if char=='\\':i+=1;continue
                if char=='[':bracket=True
                if char==']':bracket=False
                if char=='/' and not bracket:break
                if char in '\r\n':raise ValueError('Regex JavaScript não terminada')
            else:raise ValueError('Regex JavaScript não terminada')
            while i<len(text) and text[i].isalpha():i+=1
            item=('regex',text[start:i],start)
            yield item;previous=item;continue
        if c in '\"\'`':
            quote = c; i += 1; value = ''; dynamic = False
            while i < len(text) and text[i] != quote:
                c = text[i]; i += 1
                if quote == '`' and c == '$' and i < len(text) and text[i] == '{': dynamic = True
                if c == '\\':
                    if i == len(text): raise ValueError('Escape incompleto')
                    e = text[i]; i += 1
                    if e in 'ux':
                        count = 4 if e == 'u' else 2
                        value += chr(int(text[i:i+count], 16)); i += count
                    else: value += {'n':'\n','r':'\r','t':'\t','b':'\b','f':'\f'}.get(e,e)
                else: value += c
            if i == len(text): raise ValueError('String não terminada')
            i += 1; item=('dynamic' if dynamic else 'string', value, start)
        elif c.isalnum() or c in '_$':
            i += 1
            while i < len(text) and (text[i].isalnum() or text[i] in '_$-'): i += 1
            item=('word', text[start:i], start)
        else:
            i += 1; item=('punct', c, start)
        yield item;previous=item


def vdf_text(text):
    stream = iter(tokens(text)); count = 0
    def read(nested=False, depth=0):
        nonlocal count
        if depth > 48: raise ValueError('VDF profundo demais')
        result = {}
        for kind, key, _ in stream:
            if key == '}' and kind == 'punct':
                if not nested: raise ValueError('Fechamento VDF inesperado')
                return result
            if kind not in ('word','string'): raise ValueError('Chave VDF inválida')
            try: k, value, _ = next(stream)
            except StopIteration: raise ValueError('Valor VDF ausente')
            if k == 'punct' and value == '{': value = read(True, depth+1)
            elif k not in ('word','string'): raise ValueError('Valor VDF inválido')
            if key in result: raise ValueError('Chave VDF duplicada: '+key)
            result[key] = value; count += 1
            if count > 100000: raise ValueError('VDF grande demais')
        if nested: raise ValueError('Bloco VDF não terminado')
        return result
    return read()


def vdf_binary(data):
    """Legacy binary KeyValues (end=8); other variants are explicitly rejected."""
    offset = 0; count = 0
    def take(n):
        nonlocal offset
        if n < 0 or offset+n > len(data): raise ValueError('VDF binário truncado')
        b = data[offset:offset+n]; offset += n; return b
    def string():
        nonlocal offset
        end = data.find(b'\0',offset,offset+65537)
        if end < 0: raise ValueError('String VDF inválida')
        b = data[offset:end]; offset = end+1; return b.decode('utf-8')
    def read(depth=0):
        nonlocal count
        if depth > 48: raise ValueError('VDF profundo demais')
        result = {}
        while True:
            kind = take(1)[0]
            if kind == 8: return result
            key = string(); count += 1
            if count > 100000: raise ValueError('VDF grande demais')
            if kind == 0: value = read(depth+1)
            elif kind == 1: value = string()
            elif kind in (2,4): value = struct.unpack('<i',take(4))[0]
            elif kind == 3: value = struct.unpack('<f',take(4))[0]
            elif kind == 6: value = take(4).hex()
            elif kind == 7: value = struct.unpack('<Q',take(8))[0]
            else: raise ValueError('Variante/tipo VDF binário não suportado: '+str(kind))
            if key in result: raise ValueError('Chave VDF duplicada: '+key)
            result[key] = value
    result = read()
    if offset != len(data): raise ValueError('Dados extras em VDF binário')
    return result


def read_metadata(data, binary=False):
    if binary: return vdf_binary(data)
    text = data.decode('utf-8-sig')
    try: return json.loads(text)
    except json.JSONDecodeError: return vdf_text(text)


def localized(value, language):
    if isinstance(value,str): return value, None
    if isinstance(value,dict):
        aliases={'brazilian':['pt-BR','pt_BR','pt-br'],'portuguese':['pt-PT','pt_PT','pt'],'english':['en','en-US'],'spanish':['es','es-ES'],'french':['fr'],'german':['de'],'japanese':['ja']}
        for key in dict.fromkeys([language, *aliases.get(language,[]), 'english', 'en', *sorted(value)]):
            if isinstance(value.get(key),str): return value[key], key
    return '', None


def definitions(value, context=False, depth=0):
    if depth > 48: raise ValueError('Metadados profundos demais')
    if isinstance(value,list):
        for item in value: yield from definitions(item,context,depth+1)
    elif isinstance(value,dict):
        display = value.get('display',{})
        identity = any(k in value for k in ('id','source_id','api_name','apiName','name'))
        metadata = any(k in value for k in ('title','displayName','description','desc')) or isinstance(display,dict) and any(k in display for k in ('name','desc'))
        if context and identity and metadata:
            row = dict(value)
            if isinstance(display,dict):
                row.setdefault('displayName',display.get('name',''));row.setdefault('description',display.get('desc',''))
                for key in ('hidden','icon'): row.setdefault(key,display.get(key))
            yield row
            return
        for key,item in value.items():
            ctx = key.lower() in ('achievements','achievementdefinitions') or key.lower()=='bits' and str(value.get('type'))=='4'
            if context and isinstance(item,dict) and not any(k in item for k in ('id','source_id','api_name','apiName','name')) and any(k in item for k in ('title','displayName','description','desc')):
                item = dict(item,id=key)
            yield from definitions(item,context or ctx,depth+1)


def javascript_calls(text):
    stream=[]
    for token in tokens(text,True):
        if len(stream)>=200000:raise ValueError('Limite de tokens JavaScript atingido')
        stream.append(token)
    for i in range(len(stream)-5):
        receiver,dot,method,left,arg,right = stream[i:i+6]
        if receiver[0]!='word' or dot[1]!='.' or method[0]!='word' or left[1]!='(': continue
        if receiver[1].lower() not in ('steam','steamworks','greenworks','steamclient','achievements','achievement'): continue
        if method[1].lower() not in ('awardachievement','activateachievement','setachievement','unlockachievement','unlock'): continue
        if arg[0]=='string' and right[1] in (',',')'):
            yield arg[1], arg[2]


def native_candidates(data):
    seen = set()
    for match in re.finditer(rb'(?<![A-Za-z0-9_])(?:ACH_|ACHIEVEMENT_|ACHV_|TROPHY_)[A-Z0-9_]{2,56}(?![A-Za-z0-9_])',data):
        name = match[0].decode('ascii')
        if name not in seen: seen.add(name);yield name,match.start()
