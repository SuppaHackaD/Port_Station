"""Verify runtime overlays using owned fixture files and a temporary Git repo."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,tempfile,unittest,zipfile

spec=importlib.util.spec_from_file_location('updates',Path(__file__).with_name('package-update.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
MESA='build/prospero-evaluation/staged/PPSA99995/'

class UpdateTests(unittest.TestCase):
    def run_case(self, names, invalid=False):
        with tempfile.TemporaryDirectory(prefix='station-owned-overlay-')as td:
            root=Path(td);repo=root/'repo';kit=root/'kit';repo.mkdir();kit.mkdir()
            def git(*args):
                subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True)
            git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            lock=repo/'port_station/runtime.lock.json';lock.parent.mkdir()
            lock.write_text(json.dumps({'files':{n:'0'*64 for n in names}}),encoding='utf-8')
            git('add','.');git('commit','-qm','base');git('tag','base')
            current={}
            for n in names:
                p=kit/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'owned provider fixture')
                current[n]=hashlib.sha256(p.read_bytes()).hexdigest()
            lock.write_text(json.dumps({'files':current}),encoding='utf-8')
            git('add','.');git('commit','-qm','update')
            if invalid:(kit/names[0]).write_bytes(b'changed after sealing')
            previous=m.R;m.R=repo
            try:
                out=root/'update.zip'
                if invalid or any('unapproved.dll' in n for n in names):
                    with self.assertRaises(ValueError):m.package('base',out,kit)
                else:
                    m.package('base',out,kit)
                    with zipfile.ZipFile(out)as z:
                        self.assertIsNone(z.testzip())
                        for n in names:self.assertEqual(z.read('Port_Station/'+n),(kit/n).read_bytes())
                        self.assertEqual(json.loads(z.read('UPDATE.json'))['base_tag'],'base')
            finally:m.R=previous

    def test_both_architectures_and_manifest_are_included(self):
        self.run_case([MESA+'mesa-zink-manifest.json']+
                      [MESA+'win/mesa-zink/'+a+'/'+n for a in ('i386-windows','x86_64-windows')
                       for n in ('opengl32.dll','libgallium_wgl.dll')])
    def test_changed_runtime_is_rejected(self):
        self.run_case([MESA+'win/mesa-zink/x86_64-windows/libgallium_wgl.dll'],invalid=True)
    def test_owned_love_helper_is_included(self):
        self.run_case(['build/port-studio/compat/pe64/paenv.dll','build/port-studio/compat/pe64/paevents.dll','build/port-studio/compat/pe64/helper.json'])
    def test_unapproved_binary_is_rejected(self):
        self.run_case([MESA+'win/mesa-zink/x86_64-windows/unapproved.dll'])

if __name__=='__main__':unittest.main()
