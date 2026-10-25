"""Exercise generated bootstrap IO and the real BC7 encoder on Windows host."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zlib
from port_station import native, assets
from port_station.project import WORKSPACE, read_project
from port_station.builder import Builder

class NativeHostTests(unittest.TestCase):
    def test_bootstrap_first_copy_preserves_game_and_updates_profile_on_reopen(self):
        with tempfile.TemporaryDirectory(prefix='studio-bootstrap-')as temp:
            root=Path(temp);package=root/'package';data=root/'data';generated=root/'generated'
            p=read_project(WORKSPACE/'port_station/examples/tcoaal.ps5port.json')
            native.generate(p,generated,{'achievements':[{'id':'FIRST','title':'First'}]}, {}, b'{}')
            script='prefixes/tcoal/drive_c/Games/tcoal/www/js/'
            paths={'prefixes/tcoal/drive_c/Games/tcoal/test.dat':b'original game','profiles/tcoal.profile':b'profile v1','profiles/profiles.lst':b'tcoal.profile\n',script+'prospero_file_bridge.js':b'sdk bridge v1',script+'port_studio_achievements.js':b'owned bridge v1'}
            for rel,b in paths.items():
                path=package/'seed'/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
            (package/'seed-files.tsv').write_text(''.join(f'{len(b)}\t{zlib.crc32(b):08x}\t{rel}\n'for rel,b in paths.items()),encoding='utf8',newline='\n')
            (root/'driver.c').write_text('#include "studio_bootstrap.h"\nint main(int argc,char**argv){return argc==2?studio_bootstrap(argv[1]):99;}\n')
            exe=root/'test.exe'
            subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-I'+str(generated),'-DSTUDIO_DATA_ROOT="'+data.as_posix()+'"','-DSTUDIO_PACKAGE_ROOT="'+package.as_posix()+'"',str(generated/'studio_bootstrap.c'),str(root/'driver.c'),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([exe,data.as_posix()],check=True)
            game=data/'prefixes/tcoal/drive_c/Games/tcoal/test.dat';self.assertEqual(game.read_bytes(),b'original game')
            save=game.with_name('save.dat');save.write_bytes(b'my progress')
            (package/'seed/profiles/tcoal.profile').write_bytes(b'profile v2')
            (package/'seed/prefixes/tcoal/drive_c/Games/tcoal/test.dat').write_bytes(b'new game version')
            (package/'seed'/script/'port_studio_achievements.js').write_bytes(b'owned bridge v2')
            subprocess.run([exe,data.as_posix()],check=True)
            self.assertEqual(save.read_bytes(),b'my progress');self.assertEqual(game.read_bytes(),b'original game')
            self.assertEqual((data/'profiles/tcoal.profile').read_bytes(),b'profile v2')
            self.assertEqual((data/script/'port_studio_achievements.js').read_bytes(),b'owned bridge v2')
            self.assertTrue((data/'prefixes/tcoal/drive_c/PortStudioNW/Default').is_dir())

    def test_bc7_real_encoder_and_decoder(self):
        with tempfile.TemporaryDirectory(prefix='studio-art-')as temp:
            root=Path(temp);source=root/'test.png';assets.Image.new('RGB',(160,90),(32,90,150)).save(source)
            p=read_project(WORKSPACE/'port_station/examples/tcoaal.ps5port.json');p.update(icon=str(source),background=str(source),launch_background='',sound='')
            build=Builder(log=lambda s:None)
            assets.prepare_presentation(p,root,root/'output',build.run,lambda s:None)
            data=(root/'output/pic0.dds').read_bytes();assets.validate_dds(data)
            self.assertEqual(data,(root/'output/pic1.dds').read_bytes())
            with assets.Image.open(root/'output/pic0.dds')as im:
                self.assertEqual(im.size,(3840,2160));self.assertTrue(all(abs(a-b)<8 for a,b in zip(im.getpixel((1920,1080))[:3],(32,90,150))))

if __name__=='__main__':unittest.main()
