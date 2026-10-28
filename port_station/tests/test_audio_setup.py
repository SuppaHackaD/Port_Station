"""Optional dependency setup: owned inputs only, no network requests."""
from pathlib import Path
import hashlib,importlib.util,io,json,sys,tempfile,unittest,zipfile
from unittest.mock import patch
from port_station import audio
from port_station.project import ProjectError,WORKSPACE

class ToolDiagnosticsTests(unittest.TestCase):
    def test_missing_mismatched_and_valid_tools_have_distinct_results(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);tools=root/'tools/port-studio-audio';tools.mkdir(parents=True)
            ffmpeg=tools/'ffmpeg/ffmpeg.exe';encoder=tools/'port-at9-encode.exe';encoder.write_bytes(b'owned encoder')
            manifest={'files':{ffmpeg.relative_to(root).as_posix():hashlib.sha256(b'owned decoder').hexdigest(),encoder.relative_to(root).as_posix():hashlib.sha256(encoder.read_bytes()).hexdigest()}}
            (tools/'build.json').write_text(json.dumps(manifest),encoding='utf-8')
            with patch.multiple(audio,WORKSPACE=root,TOOLS=tools,FFMPEG=ffmpeg,ENCODER=encoder):
                with self.assertRaisesRegex(ProjectError,'Instalar FFmpeg'):audio.check_tools()
                ffmpeg.parent.mkdir();ffmpeg.write_bytes(b'existing custom decoder')
                with self.assertRaisesRegex(ProjectError,'difere da versão verificada'):audio.check_tools()
                self.assertEqual(ffmpeg.read_bytes(),b'existing custom decoder')
                ffmpeg.write_bytes(b'owned decoder');self.assertEqual(audio.check_tools(),manifest)
                encoder.unlink()
                with self.assertRaisesRegex(ProjectError,'Encoder ATRAC9 ausente'):audio.check_tools()
                (tools/'build.json').write_text('{bad',encoding='utf-8')
                with self.assertRaisesRegex(ProjectError,'Manifesto'):audio.check_tools()

class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('owned_ffmpeg_installer',WORKSPACE/'release_support/install-ffmpeg.py')
        cls.installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.installer)

    def archive(self,binary):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w')as z:z.writestr('owned-fixture/bin/ffmpeg.exe',binary)
        return data.getvalue()

    def test_verified_install_and_repeat_do_not_redownload_or_leave_partial_files(self):
        binary=b'owned decoder fixture';digest=hashlib.sha256(binary).hexdigest();m=self.installer
        with tempfile.TemporaryDirectory()as td,patch.object(m,'EXPECTED',digest):
            target=Path(td)/'tool/ffmpeg.exe'
            with patch.object(m.urllib.request,'urlopen',return_value=io.BytesIO(self.archive(binary)))as download:
                self.assertEqual(m.install(target,lambda s:None),target);download.assert_called_once()
            self.assertEqual(target.read_bytes(),binary);self.assertFalse(list(target.parent.glob('*.download')))
            with patch.object(m.urllib.request,'urlopen')as download:
                m.install(target,lambda s:None);download.assert_not_called()

    def test_hash_mismatch_and_write_failure_do_not_publish_an_executable(self):
        binary=b'owned decoder fixture';m=self.installer
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'tool/ffmpeg.exe'
            with patch.object(m,'EXPECTED','0'*64),patch.object(m.urllib.request,'urlopen',return_value=io.BytesIO(self.archive(binary))):
                with self.assertRaisesRegex(ValueError,'SHA-256'):m.install(target,lambda s:None)
            self.assertFalse(target.exists())
            with patch.object(m,'EXPECTED',hashlib.sha256(binary).hexdigest()),patch.object(m.urllib.request,'urlopen',return_value=io.BytesIO(self.archive(binary))),patch.object(m.os,'fsync',side_effect=OSError('owned storage failure')):
                with self.assertRaises(OSError):m.install(target,lambda s:None)
            self.assertFalse(target.exists());self.assertFalse(list(target.parent.glob('*.download')))

    def test_existing_different_executable_is_preserved(self):
        m=self.installer
        with tempfile.TemporaryDirectory()as td:
            target=Path(td)/'ffmpeg.exe';target.write_bytes(b'owned custom executable')
            with patch.object(m.urllib.request,'urlopen')as download:
                with self.assertRaisesRegex(ValueError,'Preserve/renomeie'):m.install(target,lambda s:None)
                download.assert_not_called()
            self.assertEqual(target.read_bytes(),b'owned custom executable')

class SetupUiTests(unittest.TestCase):
    def test_setup_is_available_without_game_configuration_and_uses_a_worker(self):
        import tkinter as tk
        from port_station.gui import App
        root=tk.Tk();root.withdraw()
        try:
            app=App(root)
            self.assertIn(app.audio_install_button,app.action_buttons)
            with patch('port_station.gui.threading.Thread')as thread:
                app.install_ffmpeg();thread.return_value.start.assert_called_once()
                self.assertTrue(thread.call_args.kwargs['daemon']);worker=thread.call_args.kwargs['target']
            self.assertTrue(app.busy);self.assertTrue(app.audio_install_button.instate(['disabled']))
            with patch('port_station.gui.Builder.run')as run,patch('port_station.audio.check_tools',return_value={}):
                worker();run.assert_called_once_with([sys.executable,WORKSPACE/'release_support/install-ffmpeg.py'])
            app.poll();self.assertFalse(app.busy);self.assertTrue(app.audio_install_button.instate(['!disabled']))
        finally:
            for timer in root.tk.call('after','info'):root.after_cancel(timer)
            root.destroy()

if __name__=='__main__':unittest.main()
