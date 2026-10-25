import copy
import io
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from port_station.project import default_project, read_project, validate, ProjectError, relative_file, pe_architecture, WORKSPACE
from port_station.builder import Builder, make_profile, tree, Cancelled
from port_station import native, assets

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.p=read_project(WORKSPACE/'port_station/examples/tcoaal.ps5port.json')
        self.base=WORKSPACE/'port_station/examples'

    def test_existing_recipes_resolve_independently_of_cwd(self):
        for name in ['breath','tcoaal']:
            p=read_project(self.base/(name+'.ps5port.json'));validate(p,self.base,False)

    def test_generic_project_has_no_game_specific_adapter(self):
        p=read_project(self.base/'windows-game.ps5port.json')
        validate(p,self.base,False)
        self.assertEqual(p['adapter'],'none')
        self.assertEqual(p['achievements'],[])
        self.assertFalse(p['platinum'])
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);native.generate(p,out)
            main=(out/'wine64_main.c').read_text(encoding='utf8')
            self.assertNotIn('studio_pa_open(',main)
            self.assertNotIn('breath_achievements_ps5_open(',main)
            self.assertFalse((out/'studio_pa.c').exists())

    def test_canonical_package_contains_the_implementation(self):
        import inspect
        self.assertEqual(Builder.__module__,'port_station.builder')
        self.assertTrue(Path(inspect.getfile(Builder)).resolve().is_relative_to(WORKSPACE/'port_station'))
        self.assertFalse((WORKSPACE/'port_studio').exists())

    def test_breath_accepts_an_isolated_application_and_achievement_namespace(self):
        p=read_project(self.base/'breath.ps5port.json')
        p.update(title='Breath',title_id='PPSA99999',game_id='breathy',version='01.000.001')
        validate(p,self.base,False)

    def test_breath_still_requires_original_achievement_ids(self):
        p=read_project(self.base/'breath.ps5port.json');p['game_id']='breathy'
        p['achievements'][0]['id']='RENAMED'
        with self.assertRaisesRegex(ProjectError,'11 IDs originais'):
            validate(p,self.base,False)

    def test_breath_generated_catalog_and_prefix_use_the_custom_namespace(self):
        p=read_project(self.base/'breath.ps5port.json')
        p.update(title_id='PPSA99999',game_id='breath.isolated')
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);catalog,resources,blob=assets.make_catalog(p,self.base,out/'catalog')
            native.generate(p,out/'generated',catalog,resources,blob)
            self.assertEqual(json.loads(blob)['game_id'],'breath.isolated')
            header=(out/'generated/breath_pa_assets.h').read_text(encoding='ascii')
            self.assertIn('#define BREATH_PA_GAME_ID '+native.c_string('breath.isolated'),header)
            bootstrap=(out/'generated/studio_bootstrap.c').read_text(encoding='utf8')
            self.assertIn('prefixes/breath-isolated',bootstrap)
            self.assertIn('/data/port-studio/ppsa99999',bootstrap)

    def test_duplicate_canonical_ids_rejected(self):
        self.p['achievements'].append(copy.deepcopy(self.p['achievements'][0]))
        with self.assertRaises(ProjectError):validate(self.p,self.base,False)

    def test_duplicate_source_ids_rejected(self):
        self.p['achievements'][1]['source_id']=self.p['achievements'][0]['source_id']
        with self.assertRaises(ProjectError):validate(self.p,self.base,False)

    def test_catalog_cannot_fake_unlocks_without_adapter(self):
        self.p['adapter']='none'
        with self.assertRaises(ProjectError):validate(self.p,self.base,False)

    def test_completion_does_not_collide_with_regular_id(self):
        self.p['platinum']=True;self.p['platinum_id']=self.p['achievements'][0]['id']
        with self.assertRaises(ProjectError):validate(self.p,self.base,False)

    def test_file_traversal_and_windows_collisions(self):
        for name in ['../escape.exe','/root','C:/game.exe','a\\game.exe','a//game.exe','NUL.txt','folder./a','a\tname']:
            with self.subTest(name=name),self.assertRaises(ProjectError):relative_file(name)
        self.assertEqual(str(relative_file('dados/Capítulo 1.txt')),'dados/Capítulo 1.txt')

    def test_profile_identity_cannot_be_overridden(self):
        self.p['profile_options']={'application':{'prefix':'another-game'}}
        with self.assertRaises(ProjectError):validate(self.p,self.base,False)

    def test_canvas_is_first_argument_and_exit_does_not_use_create(self):
        profile=make_profile(self.p,'pe32')
        self.assertIn('arguments = canvas --single-process',profile)
        self.assertIn('create = none',profile)
        self.assertIn('architecture = pe32',profile)

    def test_dotted_backend_id_maps_to_valid_wine_identifier(self):
        import subprocess
        self.p['game_id']='studio.test-game'
        with tempfile.TemporaryDirectory()as temp:
            path=Path(temp)/'game.profile';path.write_text(make_profile(self.p,'pe32'),encoding='utf8',newline='\n')
            checker=WORKSPACE/'build/port-studio/tools/check-profile.exe'
            if checker.is_file():subprocess.run([str(checker),str(path)],check=True,capture_output=True)
            self.assertIn('id = studio-test-game',path.read_text())

    def test_worker_keeps_dotted_backend_namespace_and_bootstrap_identity(self):
        self.p['game_id']='studio.test-game'
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);c,res,blob=assets.make_catalog(self.p,self.base,out/'catalog');native.generate(self.p,out/'generated',c,res,blob)
            worker=(out/'generated/studio_pa.c').read_text();bootstrap=(out/'generated/studio_bootstrap.c').read_text()
            self.assertIn('outbox,"studio.test-game",owner',worker)
            self.assertIn('prefixes/studio-test-game',bootstrap)
            self.assertIn('PPSA99411-studio.test-game-v1',bootstrap)

    def test_pe_architecture_without_commercial_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            exe=Path(temp)/'fixture.exe'
            for machine,expected in [(0x14c,'pe32'),(0x8664,'pe64')]:
                data=bytearray(134);data[:2]=b'MZ';struct.pack_into('<I',data,60,128)
                data[128:132]=b'PE\0\0';struct.pack_into('<H',data,132,machine)
                exe.write_bytes(data);self.assertEqual(pe_architecture(exe),expected)

    def test_unicode_catalog_completion_and_png_are_real(self):
        self.p['title']='Teste — ação';self.p['platinum']=True
        with tempfile.TemporaryDirectory()as temp:
            c,res,blob=assets.make_catalog(self.p,self.base,Path(temp))
            self.assertEqual(json.loads(blob)['title'],'Teste — ação')
            self.assertEqual(sum(bool(a.get('completion'))for a in c['achievements']),1)
            for data in res.values():
                self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
                with assets.Image.open(io.BytesIO(data))as im:self.assertEqual(im.size,(256,256))

    def test_native_identity_and_achievement_worker_generation(self):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);c,res,blob=assets.make_catalog(self.p,self.base,out/'catalog')
            native.generate(self.p,out/'generated',c,res,blob)
            main=(out/'generated/wine64_main.c').read_text()
            self.assertNotIn('@ACH_',main);self.assertIn('PPSA99411',main)
            self.assertIn('/data/port-studio/ppsa99411',main)
            self.assertIn('studio_pa_close();pw_diagnostics_close(reason)',main)
            self.assertTrue((out/'generated/studio_pa_assets.h').is_file())

    def test_bridge_patches_copy_only_and_preserves_original_bytes(self):
        with tempfile.TemporaryDirectory()as temp:
            game=Path(temp);(game/'www').mkdir();original=b'<!doctype html><body>original<script src="js/main.js"></script></body>'
            (game/'www/index.html').write_bytes(original);Builder(log=lambda s:None).nw_bridge(self.p,game)
            result=(game/'www/index.html').read_bytes()
            self.assertIn(original.split(b'</body>')[0],result)
            self.assertEqual(result.count(b'port_studio_achievements.js'),1)
            self.assertIn('"warden_wins": "WARDEN_WINS"',(game/'www/js/port_studio_achievements.js').read_text())
            with self.assertRaises(ProjectError):Builder(log=lambda s:None).nw_bridge(self.p,game)

    def test_fake_dds_and_fake_audio_rejected(self):
        for validate_asset in [assets.validate_dds,assets.validate_at9]:
            with self.assertRaises(ProjectError):validate_asset(b'fake format')

    def test_cancelled_build_preserves_sources(self):
        event=threading.Event();event.set()
        with self.assertRaises(Cancelled):Builder(cancel=event).checkpoint()

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory()as temp:
            path=Path(temp);(path/'keep.txt').write_text('user data')
            with self.assertRaises(ProjectError):Builder(log=lambda s:None).build(self.p,self.base,path)
            self.assertEqual((path/'keep.txt').read_text(),'user data')

    def test_case_collisions_rejected(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory()as temp:
            with patch('port_station.builder.os.walk',return_value=[(temp,[],['Data.bin','data.bin'])]):
                with self.assertRaises(ProjectError):list(tree(Path(temp)))

    def test_game_bytecode_is_preserved_while_tool_cache_can_be_excluded(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);source=root/'source';source.mkdir();(source/'game.pyc').write_bytes(b'compiled game')
            builder=Builder(log=lambda s:None);builder.copy(source,root/'game');builder.copy(source,root/'tools',skip_python_cache=True)
            self.assertEqual((root/'game/game.pyc').read_bytes(),b'compiled game');self.assertFalse((root/'tools/game.pyc').exists())

if __name__=='__main__':unittest.main()
