import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from port_station import native
from port_station.project import WORKSPACE, default_project, validate, ProjectError


class FileMarkerTests(unittest.TestCase):
    def project(self):
        p=default_project();p['adapter']='file-markers'
        p['achievements']=[{'id':'ONE','title':'First','description':'Owned fixture'}]
        p['file_markers']={'ONE':'users/owned/Save/Achi ONE'}
        return p

    def test_validation_requires_exact_catalog_and_relative_distinct_paths(self):
        p=self.project();validate(p,WORKSPACE,False)
        for rules in ({},{'OTHER':'owned'},{'ONE':'../save'},{'ONE':'C:/save'}):
            p=self.project();p['file_markers']=rules
            with self.assertRaises(ProjectError):validate(p,WORKSPACE,False)
        p=self.project();p['adapter']='file-v1'
        with self.assertRaises(ProjectError):validate(p,WORKSPACE,False)
        p=self.project();p['achievements'].append({'id':'TWO','title':'Second'})
        p['file_markers']['TWO']=p['file_markers']['ONE'].upper()
        with self.assertRaises(ProjectError):validate(p,WORKSPACE,False)

    def test_generated_worker_snapshots_before_thread_and_polls_own_sdk(self):
        p=self.project()
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);blob=json.dumps({'achievements':p['achievements']}).encode()
            native.generate(p,root,{'achievements':p['achievements']},{},blob)
            source=(root/'studio_pa.c').read_text()
            self.assertLess(source.index('int marker_rc=station_markers_open'),source.index('pthread_create'))
            self.assertIn('pa_sdk_unlock((PA_SDK *)context,id,event)',source)
            self.assertIn('station_markers_poll(&marker_state',source)
            self.assertNotIn('int rc=pa_file_bridge_poll(&bridge)',source)
            self.assertTrue((root/'file_markers.h').is_file())

    def test_crlf_requires_exact_bytes_and_recovers_previously_missed_marker(self):
        p=self.project();p['file_marker_content']='arbitrary'
        with self.assertRaises(ProjectError):validate(p,WORKSPACE,False)
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);prefix=root/'prefix';(prefix/'drive_c/Save').mkdir(parents=True)
            (prefix/'drive_c/ProsperoAchievements').mkdir()
            source=root/'test.c';exe=root/'test.exe'
            source.write_text(r'''#include "file_markers.h"
#undef NDEBUG
#include <assert.h>
static unsigned calls;
static int put(void *context,const char *id,const char *event){
 (void)context;assert(!strcmp(id,"FLY")&&!strcmp(event,"marker-fly"));calls++;return 0;
}
static void write_bytes(const char *path,const char *bytes,size_t size){
 FILE *f=fopen(path,"wb");assert(f);assert(fwrite(bytes,1,size,f)==size);assert(!fclose(f));
}
int main(int argc,char **argv){
 assert(argc==2);StationMarkers old,updated;
 const StationMarkerRule rules[]={{"FLY","Save/Achi FLY","marker-fly"}};
 const char *identity="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
 assert(!station_markers_open(&old,argv[1],rules,1,identity,""));
 char path[1600];snprintf(path,sizeof(path),"%s/drive_c/Save/Achi FLY",argv[1]);
 write_bytes(path,"\r\n",2);
 assert(!station_markers_poll(&old,rules,put,NULL));
 assert(!station_markers_poll(&old,rules,put,NULL));assert(!calls);
 /* Upgrade reads the original absent baseline instead of ignoring the real award. */
 assert(!station_markers_open(&updated,argv[1],rules,1,identity,"\r\n"));
 const char *bad[]={"xx","\n","\r\nX",""};
 for(unsigned i=0;i<4;i++){
  write_bytes(path,bad[i],strlen(bad[i]));
  assert(!station_markers_poll(&updated,rules,put,NULL));
  assert(!station_markers_poll(&updated,rules,put,NULL));assert(!calls);
 }
 write_bytes(path,"\r\n",2);
 assert(!station_markers_poll(&updated,rules,put,NULL));
 assert(station_markers_poll(&updated,rules,put,NULL)==1);assert(calls==1);
 assert(!station_markers_poll(&updated,rules,put,NULL));assert(calls==1);
 return 0;
}''',encoding='utf8')
            run=subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-Wall','-Wextra','-Werror','-I'+str(WORKSPACE/'port_station/templates'),str(source),'-o',str(exe)],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode('utf8','replace'))
            subprocess.run([str(exe),str(prefix)],check=True)

    def test_durable_baseline_observes_only_new_empty_files_and_retries_queue(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);prefix=root/'prefix';save=prefix/'drive_c/Save';save.mkdir(parents=True)
            (prefix/'drive_c/ProsperoAchievements').mkdir()
            (save/'old').write_bytes(b'')
            source=root/'test.c';exe=root/'test.exe'
            source.write_text('''#include "file_markers.h"
#undef NDEBUG
#include <assert.h>
static int calls=0,fail=0;
static int put(void *ctx,const char *id,const char *event){
 (void)ctx;assert(!strcmp(id,"NEW")&&!strcmp(event,"marker-new"));calls++;return fail?-1:0;
}
int main(int argc,char **argv){
 assert(argc==2);StationMarkers a,b;const char *prefix=argv[1];
 const char *identity="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
 const StationMarkerRule rules[]={{"OLD","Save/old","marker-old"},{"NEW","Save/new","marker-new"}};
 assert(!station_markers_open(&a,prefix,rules,2,identity,""));
 assert(!station_markers_poll(&a,rules,put,NULL));assert(calls==0);
 char path[1600];snprintf(path,sizeof(path),"%s/drive_c/Save/new",prefix);
 FILE *f=fopen(path,"wb");assert(f);assert(fwrite("x",1,1,f)==1);fclose(f);
 assert(!station_markers_poll(&a,rules,put,NULL));assert(calls==0);
 f=fopen(path,"wb");assert(f);fclose(f);
 assert(!station_markers_poll(&a,rules,put,NULL));assert(calls==0);
 fail=1;assert(!station_markers_poll(&a,rules,put,NULL));assert(calls==1);
 /* Simulate close after the genuine marker appeared but queue storage failed. */
 assert(!station_markers_open(&b,prefix,rules,2,identity,""));
 fail=0;assert(!station_markers_poll(&b,rules,put,NULL));
 assert(station_markers_poll(&b,rules,put,NULL)==1);assert(calls==2);
 assert(!station_markers_poll(&b,rules,put,NULL));assert(calls==2);
 /* Existing baseline still ignores OLD, and NEW has a stable dedup event. */
 assert(!station_markers_open(&a,prefix,rules,2,identity,""));
 assert(!station_markers_poll(&a,rules,put,NULL));
 assert(station_markers_poll(&a,rules,put,NULL)==1);assert(calls==3);
 snprintf(path,sizeof(path),"%s/drive_c/ProsperoAchievements/markers-%s-v1.txt",prefix,identity);
 f=fopen(path,"wb");assert(f);fputs("broken",f);fclose(f);
 assert(station_markers_open(&a,prefix,rules,2,identity,"")==-2);
 assert(!station_markers_poll(&a,rules,put,NULL));assert(calls==3);
 return 0;
}''',encoding='utf8')
            run=subprocess.run([str(WORKSPACE/'tools/zig-python/ziglang/zig.exe'),'cc','-O2','-Wall','-Wextra','-Werror','-I'+str(WORKSPACE/'port_station/templates'),str(source),'-o',str(exe)],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode('utf8','replace'))
            subprocess.run([str(exe),str(prefix)],check=True)
