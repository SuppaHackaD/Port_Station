import io
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from achievement_extractor.unity import il2cpp_literals, serialized_candidates
from achievement_extractor.core import scan
from achievement_extractor.official import enrich, select_confirmed
from achievement_extractor.tests.test_extractor import own_exe


def metadata(strings):
    table = bytearray(); blob = bytearray()
    for value in strings:
        raw = value.encode('utf8'); table += struct.pack('<II', len(raw), len(blob)); blob += raw
    return struct.pack('<6I', 0xFAB11BAF, 29, 24, len(table), 24+len(table), len(blob)) + table + blob


def asset(body):
    header = bytearray(64)
    struct.pack_into('>I', header, 8, 22)
    struct.pack_into('>IQQQ', header, 20, 16, 64+len(body), 64, 0)
    return bytes(header)+body


class UnityCandidatesTests(unittest.TestCase):
    def test_game_data_is_scanned_before_large_ancillary_folders(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);own_exe(root/'Game.exe')
            extra=root/'Data';extra.mkdir()
            for i in range(20):(extra/str(i)).write_bytes(b'not game metadata')
            meta=root/'Game_Data/il2cpp_data/Metadata/global-metadata.dat';meta.parent.mkdir(parents=True)
            meta.write_bytes(metadata(['ACHI_First']))
            with patch('achievement_extractor.core.MAX_FILES',5):result=scan(root,'Game.exe')
            self.assertTrue(result['coverage']['truncated'])
            self.assertEqual([r['source_id']for r in result['entries']],['ACHI_First'])

    def test_metadata_exact_literals_and_offsets_and_bounds(self):
        raw = metadata(['ACHI_MixedCase', 'no prefix', 'SECRET_ID'])
        rows = list(il2cpp_literals(raw))
        self.assertEqual([r[0] for r in rows], ['ACHI_MixedCase', 'SECRET_ID'])
        for value, offset, index in rows:
            self.assertEqual(raw[offset:offset+len(value)], value.encode())
        for bad in (raw[:20], raw[:-1], b'BAD!'+raw[4:]):
            with self.assertRaises(ValueError): list(il2cpp_literals(bad))
        broken = bytearray(raw); struct.pack_into('<I', broken, 28, 0xffffffff)
        with self.assertRaises(ValueError): list(il2cpp_literals(broken))

    def test_serialized_candidates_cross_chunks_preserve_case_and_length(self):
        name = b'ACHI_ExactCase'
        body = b'x'*57+struct.pack('<I',len(name))+name+b'\0'*4
        body += struct.pack('<I',2)+b'ACHI_FALSE\0'
        raw = asset(body)
        for chunk in (73, 128, 1024):
            self.assertEqual(list(serialized_candidates(io.BytesIO(raw),len(raw),chunk_size=chunk)), [('ACHI_ExactCase', 64+61)])
        self.assertEqual(list(serialized_candidates(io.BytesIO(raw),len(raw)+1)), [])
        self.assertEqual(list(serialized_candidates(io.BytesIO(raw),len(raw),max_bytes=80)), [])

    def test_scan_and_official_merge_do_not_claim_runtime_unlocks(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);own_exe(root/'Game.exe')
            unity=root/'Game_Data';p=unity/'il2cpp_data/Metadata/global-metadata.dat';p.parent.mkdir(parents=True)
            p.write_bytes(metadata(['ACHI_First','OFFICIAL_OTHER']))
            name=b'ACHI_AssetOnly';(unity/'resources.assets').write_bytes(asset(struct.pack('<I',len(name))+name+b'\0'*4))
            result=scan(root,'Game.exe')
            self.assertEqual({r['source_id']for r in result['entries']},{'ACHI_First','ACHI_AssetOnly'})
            self.assertTrue(all(not r['selected']for r in result['entries']))
            schema={'appid':'42','language_requested':'english','provider':'owned fixture','entries':{
                n:{'title':n,'description':'Owned description','hidden':False}for n in ('ACHI_First','ACHI_AssetOnly','OFFICIAL_OTHER','NOT_LOCAL')}}
            result=enrich(result,schema);select_confirmed(result)
            self.assertEqual({r['source_id']for r in result['entries']if r['selected']},{'ACHI_First','ACHI_AssetOnly','OFFICIAL_OTHER'})
            self.assertFalse(any(r['source_id']=='NOT_LOCAL'for r in result['entries']))


if __name__=='__main__':unittest.main()
