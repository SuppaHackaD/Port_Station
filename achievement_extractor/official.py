"""Opt-in, bounded Steam metadata lookup. Never queries a player's progress."""
import copy
import json
import re
from urllib import request, parse, error

ENDPOINT = 'https://api.steampowered.com/IPlayerService/GetGameAchievements/v1/'
FALLBACK = 'Descrição não fornecida'


class LookupError(ValueError): pass


def app_id(value):
    text = str(value).strip()
    if not re.fullmatch(r'[1-9][0-9]{0,9}', text) or int(text) > 4294967295:
        raise LookupError('Informe um AppID Steam numérico válido.')
    return text


def detect_app_id(folder):
    """A hint, never a title/name-based guess. The user confirms before lookup."""
    from pathlib import Path
    path = Path(folder) / 'steam_appid.txt'
    try:
        if path.stat().st_size > 32: return ''
        return app_id(path.read_text(encoding='utf-8-sig'))
    except (OSError, UnicodeError, LookupError): return ''


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


def fetch(steam_app_id, language='english'):
    ident = app_id(steam_app_id)
    if not re.fullmatch('[a-zA-Z-]{2,32}', language):
        raise LookupError('Idioma Steam inválido.')
    url = ENDPOINT + '?' + parse.urlencode({'appid': ident, 'language': language})
    try:
        req = request.Request(url, headers={'User-Agent': 'PortStation-AchievementExtractor/0.2'})
        with request.build_opener(NoRedirect()).open(req, timeout=15) as response:
            data = response.read(4*1024*1024 + 1)
        if len(data) > 4*1024*1024: raise LookupError('Resposta Steam acima do limite de 4 MiB.')
        payload = json.loads(data)
        if not isinstance(payload,dict) or not isinstance(payload.get('response'),dict):
            raise LookupError('Resposta Steam inválida.')
        rows = payload['response'].get('achievements')
        if not isinstance(rows, list) or not rows:
            raise LookupError('A Steam não retornou um catálogo para esse AppID.')
        if len(rows) > 4096: raise LookupError('Catálogo Steam acima do limite.')
        output = {}
        for row in rows:
            if not isinstance(row, dict): raise LookupError('Linha Steam inválida.')
            source = row.get('internal_name')
            if not isinstance(source, str) or not source or len(source.encode('utf-8')) > 256 or any(ord(c)<32 for c in source):
                raise LookupError('ID Steam inválida.')
            if source in output: raise LookupError('IDs Steam duplicadas.')
            item = {'source_id': source, 'hidden': row.get('hidden', False) in (True, 1, '1', 'true')}
            for field, key, limit in [('title','localized_name',256),('description','localized_desc',2048)]:
                text = row.get(key, '')
                if not isinstance(text,str) or '\0' in text or len(text.encode('utf-8')) > limit:
                    raise LookupError('Texto Steam inválido ou acima do limite.')
                item[field] = text.strip()
            output[source] = item
        return {'appid': ident, 'language_requested': language, 'provider': ENDPOINT, 'entries': output}
    except error.HTTPError as exc:
        raise LookupError(f'Consulta Steam indisponível (HTTP {exc.code}). Use metadados locais ou edição manual.') from None
    except (error.URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LookupError('Não foi possível consultar a Steam. Use metadados locais ou edição manual.') from None


def enrich(result, schema):
    """Exact-ID merge, no new rows/unlocks, manual edits preserved field by field."""
    result = copy.deepcopy(result)
    count = 0
    for row in result['entries']:
        official = schema['entries'].get(row['source_id'])
        if not official: continue
        row.setdefault('official_texts', {})[schema['language_requested']] = dict(official)
        manual = set(row.get('manual_fields', []))
        if row.get('user_reviewed') and 'manual_fields' not in row: manual.update(('title','description','hidden'))
        for key in ('title','description','hidden'):
            if key not in manual and official[key] not in ('', None):
                row[key] = official[key]
                if key in row['review']: row['review'].remove(key)
        row['evidence'].append({'kind':'steam-official','appid':schema['appid'],
            'language_requested':schema['language_requested'],'provider':schema['provider']})
        count += 1
    result['official_lookup'] = {k:v for k,v in schema.items() if k != 'entries'}
    result['official_lookup'].update(matched=count, unmatched=len(result['entries'])-count,
        matched_ids=[row['source_id'] for row in result['entries'] if row['source_id'] in schema['entries']])
    result['warnings'].append(f'Steam: {count} IDs correspondentes; idioma solicitado {schema["language_requested"]}. '
                              'O serviço pode retornar inglês quando não há localização; revise os textos.')
    return result


def select_confirmed(result):
    if not result.get('official_lookup'):
        raise LookupError('Consulte primeiro o catálogo oficial pelo AppID correto.')
    ids=set(result['official_lookup']['matched_ids'])
    for row in result['entries']: row['selected']=row['source_id'] in ids
