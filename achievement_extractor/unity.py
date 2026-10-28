"""Bounded static Unity string candidates; never proves an award call."""
import re
import struct


def il2cpp_literals(data):
    if len(data) < 24:
        raise ValueError('Cabeçalho IL2CPP incompleto.')
    magic, version, table, size, blob, blob_size = struct.unpack_from('<6I', data)
    if magic != 0xFAB11BAF or version not in (24, 27, 29, 31):
        raise ValueError('Formato/versão IL2CPP não suportado.')
    if table < 24 or size % 8 or table + size > len(data) or blob < table + size or blob + blob_size > len(data):
        raise ValueError('Seções IL2CPP inválidas.')
    if size // 8 > 262144:
        raise ValueError('Limite de literais IL2CPP atingido.')
    for index in range(size // 8):
        length, start = struct.unpack_from('<2I', data, table + index * 8)
        if start + length > blob_size:
            raise ValueError('Literal IL2CPP fora da seção.')
        if not 1 <= length <= 256:
            continue
        value = data[blob + start:blob + start + length].decode('utf8')
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}', value):
            yield value, blob + start, index


def serialized_candidates(stream, file_size, max_bytes=128*1024*1024, chunk_size=1024*1024):
    """Recognize Unity headers, then prefixed achievement-like ASCII strings.

    A candidate must carry its exact serialized byte length. Still review-only:
    this is not an object/type parser or an achievement condition decoder.
    """
    header = stream.read(48)
    if len(header) < 20:
        return
    metadata, declared, version, start = struct.unpack_from('>4I', header)
    if version not in range(17, 32) or header[16] != 0:
        return  # Big-endian serialized strings are not currently scanned.
    if version >= 22:
        if len(header) < 48:
            return
        metadata, declared, start, _ = struct.unpack_from('>IQQQ', header, 20)
    if declared != file_size or metadata <= 0 or not 20 <= start < declared:
        return
    pattern = re.compile(rb'(?:ACHI_|ACH_|ACHIEVEMENT_|ACHV_|TROPHY_)[A-Za-z0-9_.-]{1,96}')
    stream.seek(start)
    read = start
    tail = b''
    offset = start
    seen = set()
    while read < min(file_size, max_bytes):
        block = stream.read(min(chunk_size, min(file_size, max_bytes) - read))
        if not block:
            break
        read += len(block)
        data = tail + block
        safe = len(data) if read >= min(file_size, max_bytes) else max(0, len(data)-128)
        for match in pattern.finditer(data):
            at = match.start()
            if at < 4 or at >= safe or at + len(match[0]) >= len(data):
                continue
            if struct.unpack_from('<I', data, at-4)[0] != len(match[0]):
                continue
            name = match[0].decode('ascii')
            if name not in seen:
                seen.add(name)
                yield name, offset + at
        keep = max(0, safe-4)
        offset += keep
        tail = data[keep:]
