"""Real pinned-toolchain regression: the output path must remain one argument."""
from pathlib import Path
import struct
import json
import shlex
import sys
import subprocess
import tempfile
import unittest
from port_station.project import WORKSPACE
from port_station.toolchain import compile_payload


class PayloadToolchainTests(unittest.TestCase):
    @unittest.skipUnless((WORKSPACE/'build/host/ps5-native-tool.exe').is_file(), 'Windows kit required')
    def test_cmake_response_file_preserves_a_long_object_list(self):
        with tempfile.TemporaryDirectory(prefix='station-long-link-')as temp:
            root=Path(temp)/('Owned output & ação with spaces '+'x'*65);root.mkdir()
            (root/'main.c').write_text('int main(void){return 0;}\n')
            sources=['main.c']
            for i in range(40):
                name=f'owned link regression input {i:02d}.c';sources.append(name)
                (root/name).write_text(f'int owned_{i}(void){{return {i};}}\n')
            sdk=WORKSPACE/'sdk/ps5-game-port'
            (root/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.25)\nproject(OwnedLink LANGUAGES C CXX)\ninclude("'+(sdk/'cmake/PS5GamePort.cmake').as_posix()+'")\nps5_game_port_title(owned TITLE_ID PPSA99509 TITLE_NAME "Owned linker fixture" SOURCES '+' '.join('"'+n+'"'for n in sources)+')\n',encoding='utf-8')
            cmake=WORKSPACE/'tools/cmake/cmake-4.4.4-windows-x86_64/bin/cmake.exe'
            build=root/'native'
            def run(args):
                p=subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf-8',errors='replace')
                self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
            run([cmake,'-S',root,'-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
                 '-DCMAKE_TOOLCHAIN_FILE='+str(sdk/'cmake/toolchain.cmake'),
                 '-DCMAKE_MAKE_PROGRAM='+str(WORKSPACE/'tools/sdk-v0.44/ps5-payload-sdk/win/ninja.exe'),
                 '-DGP_PYTHON='+sys.executable])
            response=build/'owned-work/link-Release.rsp'
            args=shlex.split(response.read_text(encoding='utf-8'))
            self.assertGreater(len(' '.join(args)),8191)
            self.assertEqual(len([a for a in args if a.endswith('.c.o')and 'owned_link_regression_input_'in a]),40)
            run([cmake,'--build',build,'--parallel','4'])
            output=build/'dist/PPSA99509'
            self.assertEqual((output/'eboot.bin').read_bytes()[:4],bytes.fromhex('4f153d1d'))
            self.assertEqual(json.loads((output/'sce_sys/param.json').read_text())['titleId'],'PPSA99509')

    @unittest.skipUnless((WORKSPACE/'tools/llvm-18.1.8/bin/ld.lld.exe').is_file(), 'Windows kit required')
    def test_payload_links_with_spaces_unicode_and_shell_metacharacter(self):
        with tempfile.TemporaryDirectory(prefix='station-payload-')as temp:
            folder=Path(temp)/'Intravenous 2 Mercenarism & ação'
            folder.mkdir();source=folder/'owned source.c'
            source.write_text('int main(void){return 0;}\n',encoding='utf-8')
            output=folder/'helper output.elf';commands=[]
            def run(args):
                commands.append(list(map(str,args)))
                subprocess.run(commands[-1],check=True,capture_output=True)
            compile_payload([source],output,run)
            image=output.read_bytes()
            self.assertEqual(image[:5],b'\x7fELF\x02')
            self.assertEqual(struct.unpack_from('<HH',image,16),(3,62))
            self.assertNotEqual(struct.unpack_from('<Q',image,24)[0],0)
            self.assertTrue(commands[-1][0].endswith('ld.lld.exe'))
            self.assertIn(str(output),commands[-1])
            headers=struct.unpack_from('<Q',image,32)[0]
            size,count=struct.unpack_from('<HH',image,54)
            loads=[struct.unpack_from('<IIQQQQQQ',image,headers+i*size)for i in range(count)]
            self.assertTrue(any(p[0]==1 and p[7]==0x4000 for p in loads))


if __name__=='__main__':unittest.main()
