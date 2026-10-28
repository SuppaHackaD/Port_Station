import subprocess
import tempfile
import unittest
from pathlib import Path
from port_station.project import WORKSPACE, default_project, validate, ProjectError
from port_station.builder import make_profile
from port_station import native


class KeyboardStickTests(unittest.TestCase):
    def test_profile_extension_is_compiled_and_not_sent_to_upstream_parser(self):
        p=default_project();p['profile_options']={'input':{'mode':'keyboard','left_stick':'dpad','up':'w','mouse':'right_stick'}}
        validate(p,WORKSPACE,False)
        profile=make_profile(p,'pe64');self.assertNotIn('left_stick',profile)
        self.assertIn('mode = keyboard',profile);self.assertIn('graphics = dxvk',profile)
        with tempfile.TemporaryDirectory()as td:
            native.generate(p,Path(td));source=(Path(td)/'wine64_main.c').read_text()
            self.assertIn('#define STATION_LEFT_STICK_DPAD 1',source)
            self.assertNotIn('@LEFT_STICK_DPAD@',source)
        p['profile_options']['input']['mode']='xinput'
        with self.assertRaises(ProjectError):validate(p,WORKSPACE,False)

    def test_edges_hysteresis_physical_merge_diagonals_and_disconnect(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);source=root/'test.c';exe=root/'test.exe'
            source.write_text('''#include "keyboard_stick.h"
#undef NDEBUG
#include <assert.h>
int main(void){
 StationKeyboardStick s={0,0};uint32_t p,r;
 station_keyboard_stick(&s,1,128,128,0,&p,&r);assert(!p&&!r);
 station_keyboard_stick(&s,1,128,70,0,&p,&r);assert(p==0x10&&!r);
 station_keyboard_stick(&s,1,128,90,0,&p,&r);assert(!p&&!r);
 station_keyboard_stick(&s,1,128,128,0x10,&p,&r);assert(!p&&!r);
 station_keyboard_stick(&s,1,128,128,0,&p,&r);assert(!p&&r==0x10);
 station_keyboard_stick(&s,1,0,0,0,&p,&r);assert(p==0x90&&!r);
 station_keyboard_stick(&s,1,255,255,0,&p,&r);assert(p==0x60&&r==0x90);
 station_keyboard_stick(&s,0,255,255,0x4000,&p,&r);assert(!p&&r==0x60);
 station_keyboard_stick(&s,1,128,128,0,&p,&r);assert(!p&&!r);
 return 0;
}''',encoding='utf8')
            run=subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-Wall','-Wextra','-Werror','-I'+str(WORKSPACE/'port_station/templates'),str(source),'-o',str(exe)],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode('utf8','replace'))
            subprocess.run([str(exe)],check=True)
