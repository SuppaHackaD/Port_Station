import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from achievement_extractor.official import fetch,enrich,detect_app_id,LookupError,FALLBACK,select_confirmed
from achievement_extractor.core import export

class OfficialTests(unittest.TestCase):
    def payload(self):
        return {'response':{'achievements':[{'internal_name':'FIRST','localized_name':'Primeira ação',
            'localized_desc':'Descrição oficial','hidden':False,'player_percent_unlocked':'90'}]}}
    def response(self,value): return io.BytesIO(json.dumps(value).encode('utf-8'))
    def test_anonymous_official_request_has_no_user_progress_or_credentials(self):
        with patch('achievement_extractor.official.request.OpenerDirector.open',return_value=self.response(self.payload())) as opened:
            schema=fetch('123','brazilian')
        req=opened.call_args.args[0]
        self.assertEqual(req.full_url,'https://api.steampowered.com/IPlayerService/GetGameAchievements/v1/?appid=123&language=brazilian')
        self.assertEqual(schema['entries']['FIRST']['description'],'Descrição oficial')
        self.assertNotIn('player_percent',json.dumps(schema));self.assertNotIn('key=',req.full_url)
    def test_error_and_bad_response_are_actionable(self):
        for payload in [{}, {'response':{'achievements':[]}}, {'response':{'achievements':[{'internal_name':'bad\nID'}]}},
                        {'response':{'achievements':[{'internal_name':'X','localized_desc':None}]}}]:
            with self.subTest(payload=payload), patch('achievement_extractor.official.request.OpenerDirector.open',return_value=self.response(payload)):
                with self.assertRaises(LookupError):fetch('123')
        with patch('achievement_extractor.official.request.OpenerDirector.open',side_effect=HTTPError('https://api.steampowered.com',429,'limit',{},None)):
            with self.assertRaisesRegex(LookupError,'HTTP 429'):fetch('123')
        with self.assertRaises(LookupError):fetch('123?key=secret')
    def test_exact_join_keeps_manual_translation_and_does_not_add_unknown_ids(self):
        original={'entries':[dict(source_id='FIRST',title='Tradução minha',description='',hidden=False,review=['description'],
            evidence=[],manual_fields=['title'],selected=True),dict(source_id='first',title='first',description='',hidden=False,review=['description'],evidence=[])], 'warnings':[]}
        before=copy.deepcopy(original)
        schema={'appid':'123','language_requested':'brazilian','provider':'steam','entries':{
            'FIRST':dict(title='Primeira',description='Oficial',hidden=True),'UNMATCHED':dict(title='Other',description='No',hidden=False)}}
        result=enrich(original,schema)
        self.assertEqual(original,before);self.assertEqual(len(result['entries']),2)
        row=result['entries'][0];self.assertEqual(row['title'],'Tradução minha');self.assertEqual(row['description'],'Oficial')
        self.assertEqual(result['entries'][1]['description'],'');self.assertEqual(result['official_lookup']['matched'],1)
        select_confirmed(result);self.assertTrue(result['entries'][0]['selected']);self.assertFalse(result['entries'][1]['selected'])
        self.assertNotIn('unlocked',row);self.assertEqual(row['official_texts']['brazilian']['title'],'Primeira')
    def test_missing_description_exports_valid_fallback_but_preserves_report_absence(self):
        with tempfile.TemporaryDirectory() as td:
            result={'entries':[dict(source_id='FIRST',title='First',description='   ',icon='',hidden=False,selected=True)]}
            path=export(result,Path(td)/'export')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['achievements'][0]['description'],FALLBACK)
            self.assertEqual(json.loads((path.parent/'extraction-report.json').read_text(encoding='utf-8'))['entries'][0]['description'],'   ')
    def test_appid_hint_is_explicit_and_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'steam_appid.txt';path.write_text('123\n');self.assertEqual(detect_app_id(td),'123')
            path.write_text('not an id');self.assertEqual(detect_app_id(td),'')

if __name__=='__main__':unittest.main()
