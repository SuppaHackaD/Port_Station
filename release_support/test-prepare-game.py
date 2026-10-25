"""Own fixtures only; never reads an installed commercial game."""
from pathlib import Path
import importlib.util,json,tempfile,unittest
spec=importlib.util.spec_from_file_location('preparation',Path(__file__).with_name('prepare-game.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PreparationTests(unittest.TestCase):
    def test_missing_translation_labels_are_added_only_to_copy(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);src=root/'source';lang=src/'www/languages/Portugues(Brasil)/dialogue.txt';lang.parent.mkdir(parents=True)
            lang.write_bytes(b'[CHOICES]\r\n#existing : Minha escolha.\r\n')
            (src/'Game.exe').write_bytes(b'own fixture, never executed')
            data=src/'www/data/9c7050ae76645487';data.parent.mkdir()
            data.write_text('12345678'+json.dumps({'labelLUT':{'existing':'Existing choice.','missing':'Call again.'}}),encoding='utf8')
            before=lang.read_bytes();module.prepare('tcoal',src,root/'output')
            self.assertEqual(lang.read_bytes(),before)
            result=(root/'output'/lang.relative_to(src)).read_bytes()
            self.assertTrue(result.startswith(before));self.assertIn(b'#missing : Ligar novamente.\r\n',result)
            with self.assertRaises(ValueError):module.prepare('tcoal',src,root/'output')

    def test_unsupported_breath_fails_before_copy(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);src=root/'source';managed=src/'Breath_Data/Managed';managed.mkdir(parents=True)
            (src/'Breath.exe').write_bytes(b'own fixture');(managed/'Assembly-CSharp.dll').write_bytes(b'unsupported fixture')
            with self.assertRaises(ValueError):module.prepare('breath',src,root/'output')
            self.assertFalse((root/'output').exists())

    def test_nested_output_is_rejected(self):
        with tempfile.TemporaryDirectory()as temp:
            src=Path(temp)
            with self.assertRaises(ValueError):module.prepare('tcoal',src,src/'nested')

if __name__=='__main__':unittest.main()
