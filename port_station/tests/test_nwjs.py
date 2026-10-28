import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from port_station.nwjs import prepare_fonts,register_font,achievement_aliases,prepare_language_assets,validate_inputs,TC_LANGUAGE
from port_station.project import WORKSPACE,read_project,ProjectError,BREATH_IDS

class NwjsTests(unittest.TestCase):
    def game_fixture(self,root):
        (root/'package.json').write_text(json.dumps({'name':'The Coffin of Andy and Leyley','main':'www/index.html'}))
        (root/'www/js').mkdir(parents=True);(root/'www/js/main.js').write_text('const GAME_VERSION="3.0.13";')
        data=root/TC_LANGUAGE;data.parent.mkdir(parents=True)
        return data

    def test_language_wrong_extension_is_restored_only_in_build_copy(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);game=root/'game';game.mkdir();canonical=self.game_fixture(game)
            original=b'LANGDATA'+json.dumps({'linesLUT':{'1':'Owned text'},'labelLUT':{}}).encode()
            renamed=canonical.with_suffix('.txt');renamed.write_bytes(original)
            with patch('port_station.nwjs.TC_LANGUAGE_SHA256',hashlib.sha256(original).hexdigest()):
                files,report=prepare_language_assets(game,root/'output')
            self.assertEqual(files[TC_LANGUAGE].read_bytes(),original)
            self.assertTrue(report['restored_name']);self.assertFalse(canonical.exists())
            self.assertEqual(renamed.read_bytes(),original)
            with self.assertRaisesRegex(ProjectError,'difere da revisão'):prepare_language_assets(game,root/'other')

    def test_language_missing_or_corrupt_is_rejected_before_build(self):
        with tempfile.TemporaryDirectory()as temp:
            game=Path(temp);canonical=self.game_fixture(game)
            with self.assertRaisesRegex(ProjectError,'base de idioma ausente'):prepare_language_assets(game,game/'out')
            canonical.write_bytes(b'invalid data')
            with self.assertRaisesRegex(ProjectError,'base de idioma inválida'):prepare_language_assets(game,game/'out')
            self.assertEqual(canonical.read_bytes(),b'invalid data')

    def test_catalog_from_breath_is_rejected_for_tcoaal(self):
        with tempfile.TemporaryDirectory()as temp:
            game=Path(temp);canonical=self.game_fixture(game)
            canonical.write_bytes(b'LANGDATA'+json.dumps({'linesLUT':{},'labelLUT':{}}).encode())
            project={'profile':'nwjs-canvas','adapter':'nwjs-steam','achievements':[{'id':n}for n in BREATH_IDS]}
            with self.assertRaisesRegex(ProjectError,'11 conquistas de Breath'):validate_inputs(project,game)
            for achievement in project['achievements']:achievement['source_id']='custom_'+achievement['id']
            validate_inputs(project,game) # Explicit custom alias mappings remain permitted.
            project['achievements']=[{'id':'WARDEN_WINS'}];validate_inputs(project,game)
            files,report=prepare_language_assets(game,game/'out');self.assertFalse(report['restored_name'])

    def test_other_games_and_versions_are_not_renamed(self):
        with tempfile.TemporaryDirectory()as temp:
            game=Path(temp);self.assertEqual(prepare_language_assets(game,game/'out'),({},{}))
            self.game_fixture(game);(game/'www/js/main.js').write_text('const GAME_VERSION="4.0";')
            self.assertEqual(prepare_language_assets(game,game/'out'),({},{}))

    @unittest.skipUnless((WORKSPACE/'build/port-studio/runtime-kit/prefix/drive_c/windows/Fonts/Faustina-Regular.ttf').is_file(),'Windows kit font fixture required')
    def test_original_faustina_css_is_fixed_and_repeat_is_idempotent(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);game=root/'game';fonts=game/'www/fonts';fonts.mkdir(parents=True);prefix=root/'prefix';prefix.mkdir()
            system=b'WINE REGISTRY Version 2\n\n[Unrelated] 123\n"preserve"="value"\n'
            (prefix/'system.reg').write_bytes(system)
            font=WORKSPACE/'build/port-studio/runtime-kit/prefix/drive_c/windows/Fonts/Faustina-Regular.ttf';(fonts/font.name).write_bytes(font.read_bytes())
            original=b'@font-face {\r\n    font-family: GameFont;\r\n    src: url("Faustina-Regular.ttf");\r\n}\r\n.other { color: red; }\r\n'
            css=fonts/'gamefont.css';css.write_bytes(original);report=prepare_fonts(game,prefix)
            expected=original.replace(b'src: url(',b'src: local("Faustina Regular"), local("Faustina"), url(')
            self.assertEqual(css.read_bytes(),expected);self.assertEqual(len(report['css']),1)
            reg=(prefix/'system.reg').read_bytes();self.assertTrue(reg.startswith(system));self.assertEqual(reg.count(b'"Faustina Regular (TrueType)"="Faustina-Regular.ttf"'),3)
            second=prepare_fonts(game,prefix);self.assertEqual(second['css'],[]);self.assertEqual((prefix/'system.reg').read_bytes(),reg)

    def test_registry_other_values_preserved(self):
        reg=b'WINE REGISTRY Version 2\n\n[Software\\\\Microsoft\\\\Windows NT\\\\CurrentVersion\\\\Fonts] 123\n"Unrelated"="keep.ttf"\n\n[Other]\n"x"="y"\n'
        updated=register_font(reg,'Custom Regular','custom.ttf');self.assertIn(b'"Unrelated"="keep.ttf"',updated);self.assertIn(b'[Other]\n"x"="y"',updated)
        self.assertEqual(register_font(updated,'Custom Regular','custom.ttf'),updated)

    def test_tcoal_aliases_from_raw_package_preserve_canonical_ids(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);(root/'package.json').write_text(json.dumps({'name':'The Coffin of Andy and Leyley','main':'www/index.html'}))
            p={'achievements':[{'id':'WARDEN_WINS'}]};aliases=achievement_aliases(p,root)
            self.assertEqual(aliases,{'WARDEN_WINS':'WARDEN_WINS','warden_wins':'WARDEN_WINS'})
            self.assertNotIn('source_id',p['achievements'][0])

    def test_other_games_keep_exact_alias_semantics(self):
        with tempfile.TemporaryDirectory()as temp:
            self.assertEqual(achievement_aliases({'achievements':[{'id':'FIRST'}]},Path(temp)),{'FIRST':'FIRST'})

if __name__=='__main__':unittest.main()
