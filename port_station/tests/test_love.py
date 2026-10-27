"""Owned fixtures for preparation and profile API behavior; no game data."""
from pathlib import Path
import ctypes,hashlib,json,os,tempfile,unittest
from unittest.mock import patch
from port_station import love
from port_station.project import default_project,ProjectError

class LoveTests(unittest.TestCase):
    def test_unknown_engines_and_bytecode_are_not_patched(self):
        with self.assertRaises(ProjectError):love.engine_bytes(b'unknown engine')
        with self.assertRaises(ProjectError):love.controller_chunk(b'unknown bytecode')
        with tempfile.TemporaryDirectory()as td:
            game=Path(td);(game/'love.dll').write_bytes(b'unknown engine')
            self.assertIsNone(love.inspect(default_project(),game))

    def test_supported_fixture_is_prepared_without_changing_input(self):
        original=b'owned engine userenv.dll\0 tail';fixed=original.replace(b'userenv.dll\0',b'paenv.dll\0\0\0')
        with tempfile.TemporaryDirectory()as td,patch.object(love,'ENGINE',hashlib.sha256(original).hexdigest()),patch.object(love,'ENGINE_FIXED',hashlib.sha256(fixed).hexdigest()):
            root=Path(td);game=root/'game';game.mkdir();(game/'love.dll').write_bytes(original);(game/'Game.exe').write_bytes(b'owned executable');helper=root/'paenv.dll';helper.write_bytes(b'owned helper')
            helper.with_name('helper.json').write_text(json.dumps({'architecture':'pe64','dll_sha256':love.digest(helper),'source_sha256':love.digest(love.WORKSPACE/'port_station/native_compat/paenv.c')}),encoding='utf-8')
            p=default_project()
            with self.assertRaisesRegex(ProjectError,'opengl-xinput'):love.inspect(p,game)
            p['profile']='opengl-xinput';plan=love.inspect(p,game)
            files,report=love.prepare(plan,game,root/'prepared',helper)
            self.assertEqual((game/'love.dll').read_bytes(),original)
            self.assertEqual(files['love.dll'].read_bytes(),fixed)
            self.assertEqual(files['paenv.dll'].read_bytes(),b'owned helper')
            self.assertFalse(report['controller_repair']);self.assertFalse(report['source_modified'])
            self.assertEqual(love.engine_bytes(fixed),fixed)
            rows,stamp=love.sync_rows(p,files);self.assertEqual(len(stamp),64);self.assertEqual(len(rows),2)
            (game/'paenv.dll').write_bytes(b'unrelated local DLL')
            with self.assertRaisesRegex(ProjectError,'conflita'):love.prepare(plan,game,root/'collision',helper)

    @unittest.skipUnless(os.name=='nt'and love.HELPER.is_file(),'Requires the Windows kit helper')
    def test_helper_current_process_profile_size_and_buffer_contract(self):
        from ctypes import wintypes as w
        lib=ctypes.WinDLL(str(love.HELPER),use_last_error=True)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);advapi=ctypes.WinDLL('advapi32',use_last_error=True)
        kernel.GetCurrentProcess.restype=w.HANDLE
        advapi.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]
        kernel.CloseHandle.argtypes=[w.HANDLE]
        token=w.HANDLE();self.assertTrue(advapi.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)))
        try:
            for suffix,char,make,expected in [('W',w.WCHAR,ctypes.create_unicode_buffer,os.environ['USERPROFILE']),('A',ctypes.c_char,ctypes.create_string_buffer,os.environ['USERPROFILE'].encode('mbcs'))]:
                f=getattr(lib,'GetUserProfileDirectory'+suffix);f.argtypes=[w.HANDLE,ctypes.POINTER(char),ctypes.POINTER(w.DWORD)];f.restype=w.BOOL
                count=w.DWORD(0);self.assertFalse(f(token,None,ctypes.byref(count)));self.assertEqual(ctypes.get_last_error(),122);self.assertEqual(count.value,len(expected)+1)
                buf=make('###'if suffix=='W'else b'###');short=w.DWORD(1);self.assertFalse(f(token,buf,ctypes.byref(short)));self.assertEqual(buf.value,'###'if suffix=='W'else b'###')
                buf=make(count.value);self.assertTrue(f(token,buf,ctypes.byref(count)));self.assertEqual(buf.value,expected)
                self.assertFalse(f(None,buf,ctypes.byref(count)));self.assertEqual(ctypes.get_last_error(),6)
                self.assertFalse(f(token,buf,None));self.assertEqual(ctypes.get_last_error(),87)
        finally:kernel.CloseHandle(token)

if __name__=='__main__':unittest.main()
