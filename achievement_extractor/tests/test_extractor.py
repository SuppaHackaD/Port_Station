import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from achievement_extractor.formats import vdf_text,vdf_binary,javascript_calls,definitions,native_candidates,localized
from achievement_extractor.core import scan,export,save_report,canonical_id,ExtractionError

def own_exe(path,extra=b''):
    data=bytearray(134);data[:2]=b'MZ';struct.pack_into('<I',data,60,128);data[128:132]=b'PE\0\0';struct.pack_into('<H',data,132,0x8664);path.write_bytes(data+extra)

class FormatTests(unittest.TestCase):
    def test_js_literal_calls_comments_regex_and_dynamic_names(self):
        text='''// Steam.awardAchievement("COMMENT");
var r=/Steam.awardAchievement("REGEX")/;
var text="Steam.awardAchievement('STRING')";
Steam.awardAchievement("REAL"); greenworks.activateAchievement('ESC\\u0041PE', ok);
Steam.awardAchievement("PREFIX_"+name); Steam.awardAchievement(`DYNAMIC_${id}`);
Steam.awardAchievement(id); other.unlock("NOT_STEAM");'''
        self.assertEqual([r[0]for r in javascript_calls(text)],['REAL','ESCAPE'])
        self.assertEqual([r[0]for r in javascript_calls('Steam.awardAchievement("NO_SEMI")')],['NO_SEMI'])
    def test_vdf_text_and_binary_schema_bits_preserve_ids_and_hidden(self):
        text='''"stats" { "1" { "type" "4" "bits" { "0" { "name" "FIRST" "display" { "name" { "english" "First" } "desc" { "english" "Own description" } "hidden" "1" } } } } "2" { "type" "1" "name" "ordinary_stat" } }'''
        rows=list(definitions(vdf_text(text)))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['name'],'FIRST');self.assertEqual(rows[0]['hidden'],'1')
        binary=b'\x00achievements\0\x000\0\x01name\0FIRST\0\x01displayName\0First\0\x02hidden\0'+struct.pack('<i',1)+b'\x08\x08\x08'
        rows=list(definitions(vdf_binary(binary)));self.assertEqual(rows[0]['name'],'FIRST');self.assertEqual(rows[0]['hidden'],1)
        for bad in [binary[:-1],binary+b'garbage',b'\x05name\0']:
            with self.assertRaises(ValueError):vdf_binary(bad)
    def test_schema_language_dicts_are_not_separate_achievements(self):
        data={'achievements':[{'name':'ONE','displayName':{'english':'First','brazilian':'Primeira'},'description':{'english':'Own'}}]}
        self.assertEqual(len(list(definitions(data))),1)
        keyed={'achievements':{'ONE':{'title':'First','description':'Own'}}}
        self.assertEqual(list(definitions(keyed))[0]['id'],'ONE')
    def test_canonical_collisions_preserve_source_ids(self):
        used=set();reserved={'a b','a_b','a_b!'};values=[]
        for source in sorted(reserved):
            value=canonical_id(source,reserved,used);used.add(value);values.append(value)
        self.assertEqual(len(set(values)),3);self.assertIn('a_b',values)
    def test_native_candidates_are_only_an_heuristic(self):
        rows=list(native_candidates(b'xx\0ACH_FIRST\0SteamAPI_Init\0ACH_FIRST\0'))
        self.assertEqual([x[0]for x in rows],['ACH_FIRST'])
    def test_locale_alias_precedes_english_fallback(self):
        self.assertEqual(localized({'pt-BR':'Ação','english':'Action'},'brazilian'),('Ação','pt-BR'))

class WorkflowTests(unittest.TestCase):
    def test_catalog_merge_export_unicode_icons_and_no_source_modification(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);game=root/'game';game.mkdir();exe=game/'Own.exe';own_exe(exe,b'\0ACH_CANDIDATE\0')
            image=b'\x89PNG\r\n\x1a\n' # Own image fixture, never decoded.
            (game/'own.png').write_bytes(image)
            schema={'achievements':[{'name':'FIRST','displayName':{'brazilian':'Primeira — ação','english':'First'},'description':{'brazilian':'Descrição própria'},'hidden':'0','icon':'own.png'}]}
            (game/'achievements.json').write_text(json.dumps(schema),encoding='utf-8')
            (game/'main.js').write_text('Steam.awardAchievement("FIRST");',encoding='utf-8')
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in game.iterdir()}
            result=scan(game,exe);selected=[r for r in result['entries']if r['selected']]
            self.assertEqual(len(selected),1);self.assertFalse(selected[0]['hidden']);self.assertEqual(len(selected[0]['evidence']),2)
            path=export(result,root/'out');data=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['achievements'][0]['title'],'Primeira — ação');self.assertEqual(data['achievements'][0]['source_id'],'FIRST')
            self.assertEqual((path.parent/data['achievements'][0]['icon']).read_bytes(),image)
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in game.iterdir()})
            with self.assertRaises(ExtractionError):export(result,path.parent)
    def test_missing_names_are_explicit_and_progress_is_not_a_catalog(self):
        with tempfile.TemporaryDirectory()as td:
            game=Path(td);exe=game/'Own.exe';own_exe(exe)
            (game/'main.js').write_text('Steam.awardAchievement("FIRST");',encoding='utf-8')
            (game/'achievements.json').write_text('{"achievements":[{"id":"UNLOCKED_PROGRESS","unlocked":true}]}',encoding='utf-8')
            result=scan(game,exe);self.assertEqual(len(result['entries']),1)
            self.assertIn('title',result['entries'][0]['review']);self.assertEqual(result['entries'][0]['title'],'FIRST')
    def test_invalid_export_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);result={'entries':[{'selected':True,'source_id':'FIRST','title':'','description':'','icon':'','hidden':False}]}
            with self.assertRaises(ExtractionError):export(result,root/'out')
            self.assertFalse((root/'out').exists())
    def test_export_cannot_write_into_the_selected_game(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);exe=root/'Own.exe';own_exe(exe)
            (root/'achievements.json').write_text('[{"id":"ONE","title":"One"}]',encoding='utf-8')
            result=scan(root,exe)
            with self.assertRaises(ExtractionError):export(result,root/'out')
            self.assertFalse((root/'out').exists())
    def test_other_executable_and_traversal_icon_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);game=root/'game';game.mkdir();exe=game/'Own.exe';own_exe(exe)
            outside=root/'Outside.exe';own_exe(outside)
            with self.assertRaises(ExtractionError):scan(game,outside)
            (game/'achievements.json').write_text('{"achievements":[{"id":"ONE","title":"One","icon":"../private.png"}]}',encoding='utf-8')
            self.assertEqual(scan(game,exe)['entries'][0]['icon'],'')
    def test_tool_uses_no_game_specific_database(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);exe=root/'Arbitrary.exe';own_exe(exe)
            (root/'achievements.json').write_text('[{"api_name":"UNKNOWN_GAME_WIN","title":"Own unknown game","description":"A fixture."}]',encoding='utf-8')
            result=scan(root,exe);self.assertEqual(result['entries'][0]['source_id'],'UNKNOWN_GAME_WIN')
    def test_no_definitions_can_produce_a_report_without_an_empty_catalog(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);game=root/'game';game.mkdir();exe=game/'Own.exe';own_exe(exe)
            result=scan(game,exe);path=save_report(result,root/'report')
            self.assertTrue(path.is_file());self.assertFalse(path.with_name('achievements.json').exists())

if __name__=='__main__':unittest.main()
