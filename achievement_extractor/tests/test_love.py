import hashlib
import io
import tempfile
from pathlib import Path
import unittest
import zipfile
from achievement_extractor.love import luajit_strings,archive_members
from achievement_extractor.formats import native_candidates,native_candidate_stream
from achievement_extractor.core import scan,export
from achievement_extractor.official import enrich,select_confirmed
from achievement_extractor.tests.test_extractor import own_exe

def uleb(n):
    result=bytearray()
    while n>=128:result.append((n&127)|128);n>>=7
    result.append(n);return bytes(result)

def dump(strings,version=1):
    proto=b'\0\0\x01\0'+uleb(len(strings))+b'\0\0'
    for text in strings:
        raw=text.encode('utf-8');proto+=uleb(len(raw)+5)+raw
    return b'\x1bLJ'+bytes([version,2])+uleb(len(proto))+proto+b'\0'

class LoveTests(unittest.TestCase):
    def test_luajit_versions_constants_and_truncation(self):
        for version in (1,2):
            data=dump(['FIRST','arbitrary_id','Not an identifier'],version)
            self.assertEqual([s for s,_ in luajit_strings(data)],['FIRST','arbitrary_id'])
            with self.assertRaises(ValueError):luajit_strings(data[:-2])
        with self.assertRaises(ValueError):luajit_strings(dump(['FIRST'],3))
        with self.assertRaises(ValueError):luajit_strings(dump(['FIRST'])+b'garbage')

    def test_table_constants_are_parsed_as_values_not_raw_printable_runs(self):
        table=b'\x01\x01\x01'+uleb(5+5)+b'FIRST'+uleb(5+6)+b'SECOND'+b'\x03\x2a'
        proto=b'\0\0\x01\0\x01\0\0'+table
        data=b'\x1bLJ\x01\x02'+uleb(len(proto))+proto+b'\0'
        self.assertEqual([s for s,_ in luajit_strings(data)],['FIRST','SECOND'])

    def test_fused_pe_reads_constants_then_exact_official_match_without_execution(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);game=root/'game';game.mkdir();exe=game/'Own.exe';own_exe(exe)
            with zipfile.ZipFile(exe,'a',zipfile.ZIP_DEFLATED)as z:
                z.writestr('game/achievements.lua',dump(['FIRST','UNOFFICIAL']))
                z.writestr('game/other.lua',dump(['lower_case_id']))
            before=hashlib.sha256(exe.read_bytes()).hexdigest()
            result=scan(game,exe)
            self.assertEqual(result['coverage']['luajit_members'],2)
            self.assertFalse(any(row['selected']for row in result['entries']))
            schema={'appid':'123','provider':'steam','language_requested':'english','entries':{
                key:dict(title=key,description='Official',hidden=False)for key in ('FIRST','lower_case_id','NOT_IN_GAME')}}
            result=enrich(result,schema);select_confirmed(result)
            path=export(result,root/'out',official_only=True,steam_app_id='123')
            import json
            self.assertEqual({row['source_id']for row in json.loads(path.read_text())['achievements']},{'FIRST','lower_case_id'})
            self.assertEqual(hashlib.sha256(exe.read_bytes()).hexdigest(),before)
            self.assertFalse((game/'game').exists())
            self.assertTrue(all('member'in e for row in result['entries']for e in row['evidence']if e['kind']=='luajit-constant'))

    def test_zip_limits_and_unsafe_names_fail_without_extraction(self):
        with tempfile.TemporaryDirectory()as td:
            path=Path(td)/'own.love'
            with zipfile.ZipFile(path,'w')as z:z.writestr('../bad.lua',dump(['FIRST']))
            with self.assertRaisesRegex(ValueError,'Nome'):list(archive_members(path))
            with zipfile.ZipFile(path,'w')as z:z.writestr('a.lua',b'A'*100);z.writestr('b.lua',b'B')
            with self.assertRaisesRegex(ValueError,'Diretório'):list(archive_members(path,max_entries=1))
            with self.assertRaisesRegex(ValueError,'Leitura'):list(archive_members(path,max_file=50))

    def test_native_stream_preserves_boundaries_and_deduplicates(self):
        data=b'X'*139+b'XACH_NOT_REAL\0ACH_REAL\0'+b'a'*170+b'\0ACH_SECOND\0ACH_REAL\0'
        expected=list(native_candidates(data))
        for size in (16,128,139,256):
            self.assertEqual(list(native_candidate_stream(io.BytesIO(data),chunk_size=size)),expected)

if __name__=='__main__':unittest.main()
