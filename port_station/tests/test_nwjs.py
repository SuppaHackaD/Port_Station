import json
from pathlib import Path
import tempfile
import unittest
from port_station.nwjs import prepare_fonts,register_font,achievement_aliases
from port_station.project import WORKSPACE,read_project

class NwjsTests(unittest.TestCase):
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
