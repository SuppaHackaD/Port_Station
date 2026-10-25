"""Actual C Breath adapter + SDK + local C service; no console or game data."""
from pathlib import Path
import json,socket,subprocess,tempfile,time,unittest,urllib.request
from port_station import assets,native
from port_station.project import WORKSPACE as R,read_project
ZIG=R/'tools/zig-python/ziglang/zig.exe'
SERVER=R/'build/prospero-achievements/host/prospero_achievements.exe'

@unittest.skipUnless(ZIG.is_file()and SERVER.is_file(),'Requires the Windows kit host compiler and service')
class BreathNamespaceTests(unittest.TestCase):
    def test_custom_namespace_does_not_unlock_original_and_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix='pa-breath-namespaces-')as temp:
            root=Path(temp);base=R/'port_station/examples';executables={}
            for game,legacy in [('breath',True),('breathy',False)]:
                p=read_project(base/'breath.ps5port.json');p['game_id']=game;p['title_id']='PPSA99999'
                work=root/game;catalog,resources,blob=assets.make_catalog(p,base,work/'catalog')
                native.generate(p,work/'generated',catalog,resources,blob)
                header=work/'generated/breath_pa_assets.h'
                if legacy:
                    value=header.read_text(encoding='ascii')
                    value=value.replace('#define BREATH_PA_GAME_ID '+native.c_string(game)+'\n','')
                    header.write_text(value,encoding='ascii')
                driver=work/'driver.c'
                driver.write_text(r'''#include "breath_pa.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv){
 if(argc!=4)return 9;BreathPA pa;
 int rc=breath_pa_open(&pa,argv[1],42,(unsigned)strtoul(argv[2],NULL,10));
 if(rc){printf("open=%d\n",rc);return 1;}
 rc=breath_pa_capture(&pa,(unsigned)strtoul(argv[3],NULL,10));if(rc)return 2;
 for(unsigned i=0;i<10;i++){rc=breath_pa_pump(&pa);if(rc<0)return 3;if(!pa_sdk_pending(&pa.sdk))break;}
 printf("game=%s pending=%d\n",pa.sdk.game_id,pa_sdk_pending(&pa.sdk));
 return pa_sdk_pending(&pa.sdk)?4:0;
}
''',encoding='ascii')
                exe=work/'adapter.exe';common=R/'src/prospero_achievements'
                command=[str(ZIG),'cc','-target','x86_64-windows-gnu','-std=c11','-O2','-DCJSON_NESTING_LIMIT=32','-I'+str(work/'generated'),'-I'+str(R/'src/breath/prospero_adapter'),'-I'+str(R/'sdk/prospero-achievements/include'),'-I'+str(common),str(driver),str(R/'src/breath/prospero_adapter/breath_pa.c'),str(R/'sdk/prospero-achievements/src/pa_sdk.c'),str(common/'pa_common.c'),str(common/'vendor/cJSON.c'),str(common/'vendor/sha256.c'),'-lws2_32','-o',str(exe)]
                subprocess.run(command,check=True,capture_output=True);executables[game]=exe
            with socket.socket()as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            log=(root/'server.log').open('wb')
            server=subprocess.Popen([str(SERVER),str(root/'service'),str(port)],stdout=log,stderr=subprocess.STDOUT)
            def get(path):
                return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/v1/'+path,timeout=2))
            try:
                deadline=time.monotonic()+8
                while True:
                    try:get('info');break
                    except OSError:
                        if time.monotonic()>deadline:raise
                        time.sleep(.05)
                def client(game,mask):
                    result=subprocess.run([str(executables[game]),str(root/('client-'+game)),str(port),str(mask)],check=True,text=True,capture_output=True)
                    self.assertIn('game='+game+' pending=0',result.stdout)
                client('breath',0);before=get('state/0000002a/breath')
                self.assertEqual(before['event_count'],0)
                client('breathy',1<<5);state=get('state/0000002a/breathy')
                self.assertEqual(state['game_id'],'breathy')
                self.assertEqual([a['id']for a in state['achievements']if a['unlocked']],['ENGUIA'])
                self.assertEqual(state['event_count'],1)
                self.assertEqual(get('state/0000002a/breath'),before)
                client('breathy',1<<5)
                self.assertEqual(get('state/0000002a/breathy'),state)
            finally:
                server.terminate();server.wait(timeout=5);log.close()

if __name__=='__main__':unittest.main()
