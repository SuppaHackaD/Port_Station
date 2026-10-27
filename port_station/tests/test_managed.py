import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zlib
from port_station import managed,native
from port_station.project import WORKSPACE as R,read_project,ProjectError

class ManagedTests(unittest.TestCase):
    def test_prepare_maps_source_ids_and_rejects_conflicting_overlays(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);game=root/'game';assembly=game/'Own_Data/Managed/Assembly-CSharp.dll';assembly.parent.mkdir(parents=True);assembly.write_bytes(b'own source')
            tools=root/'tools';tools.mkdir()
            for name,data in [('ProsperoManagedIntegrator.exe',b'own tool'),('ProsperoAchievements.dll',b'own bridge')]: (tools/name).write_bytes(data)
            (tools/'managed.lock.json').write_text(json.dumps({'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in tools.iterdir()}}))
            p=read_project(R/'port_station/examples/tcoaal.ps5port.json');p.update(adapter='unity-mono-steam',game_id='own.test',overlays=[])
            p['achievements']=[dict(id='CANONICAL',source_id='Source ç')]
            def run(args):
                self.assertEqual(args[-1],hashlib.sha256(b'own source').hexdigest())
                Path(args[-2]).write_bytes(b'own patched assembly')
            with patch.object(managed,'TOOLS',tools):
                files=managed.prepare(p,game,root/'prepared',run)
                self.assertEqual(assembly.read_bytes(),b'own source')
                text=files['Own_Data/Managed/ProsperoAchievements.config.tsv'].read_text(encoding='utf-8')
                self.assertEqual(text,'PA_MANAGED_CONFIG_V1\town.test\nMAP\tU291cmNlIMOn\tCANONICAL\n')
                p['overlays']=[dict(destination='own_data/managed/assembly-csharp.DLL')]
                with self.assertRaisesRegex(ProjectError,'overlay'):managed.prepare(p,game,root/'conflict',run)

    @unittest.skipUnless((R/'tools/zig-python/ziglang/zig.exe').is_file(),'Requires host compiler from kit')
    def test_large_managed_sync_checks_crc_and_preserves_saves_on_cached_prefix(self):
        with tempfile.TemporaryDirectory(prefix='station-managed-own-') as td:
            root=Path(td);package=root/'package';data=root/'data';generated=root/'generated'
            p=read_project(R/'port_station/examples/breath.ps5port.json');p.update(adapter='unity-mono-steam',game_id='own.test')
            own=root/'assembly.bin';own.write_bytes(b'own assembly bytes'*40000)
            rel='Own_Data/Managed/Assembly-CSharp.dll';prefix='prefixes/own-test/drive_c/Games/own-test/'
            native.generate(p,generated,{'achievements':[]},{},b'{}',managed_files={rel:own})
            paths={prefix+rel:own.read_bytes(),prefix+'save.dat':b'original save',
                   'profiles/own-test.profile':b'own profile','profiles/profiles.lst':b'own-test.profile\n'}
            for name,blob in paths.items():
                path=package/'seed'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
            (package/'seed-files.tsv').write_text(''.join(f'{len(blob)}\t{zlib.crc32(blob):08x}\t{name}\n'for name,blob in paths.items()),encoding='utf-8',newline='\n')
            (root/'driver.c').write_text('#include "studio_bootstrap.h"\nint main(int argc,char**argv){return argc==2?studio_bootstrap(argv[1]):99;}\n')
            exe=root/'test.exe'
            subprocess.run([str(R/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-I'+str(generated),
                '-DSTUDIO_DATA_ROOT="'+data.as_posix()+'"','-DSTUDIO_PACKAGE_ROOT="'+package.as_posix()+'"',
                str(generated/'studio_bootstrap.c'),str(root/'driver.c'),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([exe,data.as_posix()],check=True,capture_output=True)
            save=data/prefix/'save.dat';save.write_bytes(b'player saved progress')
            cached=data/prefix/rel;cached.write_bytes(b'outdated managed assembly')
            subprocess.run([exe,data.as_posix()],check=True,capture_output=True)
            self.assertEqual(cached.read_bytes(),own.read_bytes());self.assertEqual(save.read_bytes(),b'player saved progress')
            # A corrupt package must fail without replacing a known complete cached DLL.
            (package/'seed'/prefix/rel).write_bytes(b'corrupt')
            result=subprocess.run([exe,data.as_posix()],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(cached.read_bytes(),own.read_bytes())
            self.assertEqual(save.read_bytes(),b'player saved progress')

if __name__=='__main__':unittest.main()
