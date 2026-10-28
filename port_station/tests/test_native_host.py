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
    def test_language_asset_repairs_a_cached_prefix_without_touching_saves(self):
        with tempfile.TemporaryDirectory(prefix='station-language-cache-')as temp:
            root=Path(temp);package=root/'package';data=root/'data';generated=root/'generated'
            p=read_project(WORKSPACE/'port_station/examples/windows-game.ps5port.json')
            p.update(game_id='own.language',title_id='PPSA99501',adapter='none')
            name='www/data/owned-language';folder='prefixes/own-language/drive_c/Games/own-language/'
            original=b'LANGDATA owned fixture '*50000
            asset=package/'seed'/folder/name;asset.parent.mkdir(parents=True);asset.write_bytes(original)
            for n,b in {'profiles/own-language.profile':b'owned profile','profiles/profiles.lst':b'own-language.profile\n'}.items():
                dest=package/'seed'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
            cached=data/folder
            native.generate(p,generated,compat_files={name:asset})
            (root/'driver.c').write_text('#include "studio_bootstrap.h"\nint main(int n,char**v){return n==2?studio_bootstrap(v[1]):99;}\n')
            # Let the normal first install create its own valid marker, then
            # simulate the missing language file in an otherwise installed game.
            rows={folder+name:original,'profiles/own-language.profile':b'owned profile','profiles/profiles.lst':b'own-language.profile\n'}
            (package/'seed-files.tsv').write_text(''.join(f'{len(b)}\t{zlib.crc32(b):08x}\t{n}\n'for n,b in rows.items()),encoding='utf-8',newline='\n')
            exe=root/'test.exe'
            subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-I'+str(generated),'-DSTUDIO_DATA_ROOT="'+data.as_posix()+'"','-DSTUDIO_PACKAGE_ROOT="'+package.as_posix()+'"',str(generated/'studio_bootstrap.c'),str(root/'driver.c'),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([exe,data.as_posix()],check=True)
            (cached/'save.dat').write_bytes(b'progress')
            asset_in_cache=cached/name;asset_in_cache.unlink();(data/'.port-station-love-ready').unlink()
            subprocess.run([exe,data.as_posix()],check=True)
            self.assertEqual(asset_in_cache.read_bytes(),original)
            self.assertEqual((cached/'save.dat').read_bytes(),b'progress')

    def test_compatibility_sync_updates_cached_files_and_preserves_saves(self):
        with tempfile.TemporaryDirectory(prefix='station-compat-')as td:
            root=Path(td);package=root/'package';data=root/'data';p=read_project(WORKSPACE/'port_station/examples/windows-game.ps5port.json');p.update(game_id='own.compat',title_id='PPSA99501',adapter='none')
            folder='prefixes/own-compat/drive_c/Games/own-compat/'
            old=b'owned old DLL';new=b'owned new DLL '*50000;shim=b'owned helper';owned=root/'owned';owned.mkdir()
            (owned/'love.dll').write_bytes(new);(owned/'paenv.dll').write_bytes(shim)
            files={'love.dll':owned/'love.dll','paenv.dll':owned/'paenv.dll'}
            entries={folder+'love.dll':new,folder+'paenv.dll':shim,'profiles/own-compat.profile':b'own profile','profiles/profiles.lst':b'own-compat.profile\n'}
            for name,b in entries.items():q=package/'seed'/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
            (package/'seed-files.tsv').write_text(''.join(f'{len(b)}\t{zlib.crc32(b):08x}\t{n}\n'for n,b in entries.items()),encoding='utf-8',newline='\n')
            generated=root/'generated';native.generate(p,generated,compat_files=files)
            (root/'driver.c').write_text('#include "studio_bootstrap.h"\nint main(int argc,char**argv){return argc==2?studio_bootstrap(argv[1]):99;}\n')
            exe=root/'test.exe'
            subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-I'+str(generated),'-DSTUDIO_DATA_ROOT="'+data.as_posix()+'"','-DSTUDIO_PACKAGE_ROOT="'+package.as_posix()+'"',str(generated/'studio_bootstrap.c'),str(root/'driver.c'),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([exe,data.as_posix()],check=True)
            save=data/folder/'save.dat';save.write_bytes(b'owned progress');self.assertEqual((data/folder/'love.dll').read_bytes(),new)
            # Simulate a cached prefix from a previous build, retaining its ready marker.
            (data/'.port-station-love-ready').unlink();(data/folder/'love.dll').write_bytes(old)
            subprocess.run([exe,data.as_posix()],check=True)
            self.assertEqual((data/folder/'love.dll').read_bytes(),new);self.assertEqual(save.read_bytes(),b'owned progress')
            # A sealed cache reopens without rewriting the game files.
            before=(data/folder/'love.dll').stat().st_mtime_ns;subprocess.run([exe,data.as_posix()],check=True);self.assertEqual((data/folder/'love.dll').stat().st_mtime_ns,before)
            # A corrupt packaged update is refused and cannot replace the cached file.
            (data/'.port-station-love-ready').unlink();(data/folder/'love.dll').write_bytes(old);(package/'seed'/folder/'love.dll').write_bytes(b'bad source')
            result=subprocess.run([exe,data.as_posix()]);self.assertNotEqual(result.returncode,0);self.assertEqual((data/folder/'love.dll').read_bytes(),old);self.assertEqual(save.read_bytes(),b'owned progress')

    def test_display_detection_fallback_and_aspect_preserving_ceiling(self):
        with tempfile.TemporaryDirectory(prefix='station-display-')as td:
            root=Path(td);source=root/'display.c';exe=root/'display.exe'
            source.write_text('''#include "display_policy.h"
int main(void){
 struct {int rc;uint32_t w,h,expected_w,expected_h;int detected;}cases[]={
  {0,1280,720,1280,720,1},{0,1920,1080,1920,1080,1},
  {0,2560,1440,2560,1440,1},{0,3840,2160,3840,2160,1},
  {0,7680,4320,3840,2160,1},{0,5120,1440,3840,1080,1},
  {0,1080,3840,607,2160,1},{-1,3840,2160,1920,1080,0},
  {0,0,0,1920,1080,0},{0,20000,2160,1920,1080,0}};
 for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  StationDesktop r=station_desktop_resolve(cases[i].rc,cases[i].w,cases[i].h);
  if(r.width!=cases[i].expected_w||r.height!=cases[i].expected_h||r.detected!=cases[i].detected)return (int)i+1;
 }return 0;
}''',encoding='utf-8')
            subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-Wall','-Wextra','-Werror','-I'+str(WORKSPACE/'port_station/templates'),str(source),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True)

    def test_cached_breath_prefix_receives_bridge_update_without_reinstalling_game(self):
        with tempfile.TemporaryDirectory(prefix='station-breath-update-')as temp:
            root=Path(temp);package=root/'package';data=root/'data';generated=root/'generated'
            p=read_project(WORKSPACE/'port_station/examples/breath.ps5port.json')
            native.generate(p,generated,{'achievements':[]},{},b'{}')
            folder='prefixes/breath/drive_c/Games/breath/'
            assembly=folder+'Breath_Data/Managed/Assembly-CSharp.dll'
            bridge=folder+'Breath_Data/Managed/BreathPS5Bridge.dll'
            paths={assembly:b'own assembly v1',bridge:b'own bridge v1',folder+'level.dat':b'own unchanged scene','profiles/breath.profile':b'own profile','profiles/profiles.lst':b'breath.profile\n'}
            for rel,b in paths.items():
                q=package/'seed'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
            (package/'seed-files.tsv').write_text(''.join(f'{len(b)}\t{zlib.crc32(b):08x}\t{rel}\n'for rel,b in paths.items()),encoding='utf8',newline='\n')
            (root/'driver.c').write_text('#include "studio_bootstrap.h"\nint main(int argc,char**argv){return argc==2?studio_bootstrap(argv[1]):99;}\n')
            exe=root/'test.exe'
            subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-I'+str(generated),'-DSTUDIO_DATA_ROOT="'+data.as_posix()+'"','-DSTUDIO_PACKAGE_ROOT="'+package.as_posix()+'"',str(generated/'studio_bootstrap.c'),str(root/'driver.c'),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([exe,data.as_posix()],check=True)
            save=data/folder/'save.dat';save.write_bytes(b'own saved progress')
            (package/'seed'/assembly).write_bytes(b'own assembly v2')
            (package/'seed'/bridge).write_bytes(b'own bridge v2')
            (package/'seed'/folder/'level.dat').write_bytes(b'own replacement scene')
            subprocess.run([exe,data.as_posix()],check=True)
            self.assertEqual((data/assembly).read_bytes(),b'own assembly v2')
            self.assertEqual((data/bridge).read_bytes(),b'own bridge v2')
            self.assertEqual((data/folder/'level.dat').read_bytes(),b'own unchanged scene')
            self.assertEqual(save.read_bytes(),b'own saved progress')

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
