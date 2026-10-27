"""Own fixtures only: award semantics, archive preservation and durable transport."""
from pathlib import Path
import ctypes,hashlib,os,tempfile,unittest,zipfile
from unittest.mock import patch
from port_station import love,love_achievements as bridge
from port_station.project import ProjectError

class ArchiveTests(unittest.TestCase):
    def test_local_module_is_preserved_and_only_configured_ids_are_mapped(self):
        original=b'return "owned platform fixture"'
        with tempfile.TemporaryDirectory()as td,patch.object(bridge,'MODULE_SHA',hashlib.sha256(original).hexdigest()):
            p=Path(td)/'fixture.exe';p.write_bytes(b'owned executable header')
            with zipfile.ZipFile(p,'a')as z:
                z.writestr(bridge.MODULE,original);z.writestr('other.bin',b'unchanged')
            project={'game_id':'own.game','achievements':[{'id':'CANONICAL','source_id':'SOURCE'}]}
            result=bridge.integrate(project,p)
            self.assertFalse(result['conditions_modified']);self.assertEqual(result['mapped_ids'],1)
            with zipfile.ZipFile(p)as z:
                self.assertEqual(z.read(bridge.ORIGINAL),original);self.assertEqual(z.read('other.bin'),b'unchanged')
                self.assertIn(b'["SOURCE"]="CANONICAL"',z.read(bridge.MODULE))
                self.assertIsNone(z.testzip())
            with self.assertRaises(ProjectError):bridge.integrate(project,p)

    def test_unverified_module_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/'fixture.exe'
            with zipfile.ZipFile(p,'w')as z:z.writestr(bridge.MODULE,b'unknown')
            before=p.read_bytes()
            with self.assertRaises(ProjectError):bridge.integrate({'game_id':'own','achievements':[{'id':'ONE'}]},p)
            self.assertEqual(p.read_bytes(),before)

@unittest.skipUnless(os.name=='nt'and love.HELPER.with_name('paevents.dll').is_file(),'Requires Windows kit event publisher')
class PublisherTests(unittest.TestCase):
    def test_context_binding_append_and_failure_contract(self):
        dll=ctypes.CDLL(str(love.HELPER.with_name('paevents.dll')))
        dll.pa_event_ready_v1.argtypes=[ctypes.c_char_p,ctypes.c_char_p]
        dll.pa_event_unlock_v1.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_char_p]
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);folder=os.fsencode(td);game=b'own.game'
            ready=lambda:dll.pa_event_ready_v1(folder,game)
            unlock=lambda value:dll.pa_event_unlock_v1(folder,game,value)
            self.assertEqual(ready(),-2)
            context=root/'own.game-context-v1.txt'
            context.write_bytes(b'PA_FILE_CONTEXT_V1\town.game\t00000001\n')
            self.assertEqual(ready(),0)
            event=root/'own.game-00000001.tsv'
            self.assertNotIn(b'UNLOCK',event.read_bytes())
            with event.open('ab')as f:f.write(b'partial')
            self.assertEqual(unlock(b'ONE'),0)
            saved=event.read_bytes()
            self.assertIn(b'partial\nPA_FILE_BRIDGE_V1\town.game\t00000001\nPA_FILE_UNLOCK_V1\town.game\t00000001\tONE\n',saved)
            self.assertEqual(unlock(b'../bad'),-1);self.assertEqual(event.read_bytes(),saved)
            context.write_bytes(b'PA_FILE_CONTEXT_V1\town.game\t00000001\r\n')
            self.assertEqual(unlock(b'TWO'),-3);self.assertEqual(event.read_bytes(),saved)
            context.write_bytes(b'PA_FILE_CONTEXT_V1\town.game\t00000002\n')
            self.assertEqual(unlock(b'TWO'),0);self.assertEqual(event.read_bytes(),saved)
            self.assertIn(b'\t00000002\tTWO\n',(root/'own.game-00000002.tsv').read_bytes())
            context.write_bytes(b'PA_FILE_CONTEXT_V1\town.game\t00000003\n')
            (root/'own.game-00000003.tsv').mkdir()
            self.assertEqual(unlock(b'THREE'),-4)

LUA=os.environ.get('PORT_STATION_LUAJIT_DLL','')
@unittest.skipUnless(LUA and Path(LUA).is_file(),'Set PORT_STATION_LUAJIT_DLL to a LuaJIT 2.x library')
class LuaTests(unittest.TestCase):
    def run_lua(self,script):
        lib=ctypes.CDLL(LUA);lib.luaL_newstate.restype=ctypes.c_void_p
        for name,args in [('luaL_openlibs',[ctypes.c_void_p]),('luaL_loadbuffer',[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_char_p]),('lua_pcall',[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]),('lua_close',[ctypes.c_void_p])]:getattr(lib,name).argtypes=args
        lib.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];lib.lua_tolstring.restype=ctypes.c_char_p
        state=lib.luaL_newstate();self.assertTrue(state)
        try:
            lib.luaL_openlibs(state);data=script.encode('utf-8')
            rc=lib.luaL_loadbuffer(state,data,len(data),b'owned-achievement-fixtures')
            if not rc:rc=lib.lua_pcall(state,0,0,0)
            self.assertEqual(rc,0,lib.lua_tolstring(state,-1,None))
        finally:lib.lua_close(state)

    def test_real_requests_returns_errors_retry_and_no_synthetic_awards(self):
        template=(bridge.WORKSPACE/'port_station/templates/love_achievements.lua').read_text(encoding='utf-8')
        self.run_lua('local install=(function()\n'+template+'\nend)()\n'+r'''
local events,calls,now={},0,0
local fail=true
local native={pa_event_ready_v1=function()return 0 end,
 pa_event_unlock_v1=function(folder,game,id)
   assert(game=='own.game');if fail then return -4 end
   events[#events+1]=id;return 0
 end}
package.preload.ffi=function()return {cdef=function()end,load=function()return native end}end
love={timer={getTime=function()return now end},platformAPI={
 SetAchievement=function(id,arg)
   calls=calls+1;if id=='ERROR' then error('original failure')end
   assert(arg=='unchanged');return false,nil,'tail'
 end,updateAPI=function()return 'update',nil,3 end,
 release=function()return 'release',nil,4 end}}
local cfg={gameId='own.game',aliases={SOURCE='CANONICAL',ERROR='ERROR'}}
local client=install(cfg);assert(#events==0)
assert(install(cfg)==client)
local a,b,c=love.platformAPI.SetAchievement('SOURCE','unchanged')
assert(a==false and b==nil and c=='tail' and calls==1 and #events==0)
fail=false;now=1
a,b,c=love.platformAPI.updateAPI();assert(a=='update'and b==nil and c==3)
assert(#events==1 and events[1]=='CANONICAL')
love.platformAPI.SetAchievement('SOURCE','unchanged')
love.platformAPI.SetAchievement('UNKNOWN','unchanged')
assert(calls==3 and #events==1)
assert(not pcall(love.platformAPI.SetAchievement,'ERROR','unchanged'))
assert(calls==4 and #events==1)
a,b,c=love.platformAPI.release();assert(a=='release'and b==nil and c==4)
assert(#events==1)
''')

    def test_wrapper_preserves_module_varargs_and_survives_missing_publisher(self):
        wrapper=bridge.wrapper({'gameId':'own.game','aliases':{'SOURCE':'CANONICAL'}}).decode()
        self.run_lua(r'''
local count=0
love={filesystem={load=function(path)
 if path=='port_station/original_steam.luac'then return function(...)
  assert(select('#',...)==3);assert(select(1,...)=='argument');count=count+1
  return 'original',nil,9
 end end
 return nil,'owned missing publisher fixture'
end}}
local run=function(...)
'''+wrapper+r'''
end
local a,b,c=run('argument',nil,'third')
assert(a=='original'and b==nil and c==9 and count==1)
''')

    @unittest.skipUnless(love.HELPER.with_name('paevents.dll').is_file(),'Requires Windows kit event publisher')
    def test_actual_ffi_publisher_writes_only_after_own_award(self):
        import json
        template=(bridge.WORKSPACE/'port_station/templates/love_achievements.lua').read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'own.game-context-v1.txt').write_bytes(b'PA_FILE_CONTEXT_V1\town.game\t00000001\n')
            dll=love.HELPER.with_name('paevents.dll').as_posix()
            self.run_lua('local install=(function()\n'+template+'\nend)()\n'+
                'local ffi=require("ffi");local real_load=ffi.load;ffi.load=function(name) assert(name=="paevents.dll");return real_load('+json.dumps(dll)+') end\n'+
                'love={platformAPI={SetAchievement=function(id) assert(id=="SOURCE");return true end}}\n'+
                'install({gameId="own.game",folder='+json.dumps(root.as_posix())+',aliases={SOURCE="CANONICAL"}})\n'+
                'assert(love.platformAPI.SetAchievement("SOURCE"))\n')
            data=(root/'own.game-00000001.tsv').read_bytes()
            self.assertEqual(data.count(b'PA_FILE_UNLOCK_V1'),1)
            self.assertIn(b'\town.game\t00000001\tCANONICAL\n',data)

if __name__=='__main__':unittest.main()
