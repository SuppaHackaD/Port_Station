"""Generate the one-game shell from frozen, previously exercised runtime sources."""
import json
from pathlib import Path
from .project import WORKSPACE as R, ProjectError, runtime_id

def c_string(value):
    return '"'+''.join(f'\\x{x:02x}' for x in value.encode('utf8'))+'"'

def literal(data):
    return '\n'.join('"'+''.join(f'\\x{x:02x}'for x in data[i:i+256])+'"'for i in range(0,len(data),256))

def generate(p, out, catalog=None, resources=None, blob=None):
    out.mkdir(parents=True,exist_ok=True)
    game=p['game_id'];slug=runtime_id(p); root='/data/port-studio/'+p['title_id'].lower(); adapter=p['adapter']
    s=(R/'port_station/templates/wine64_main.c.in').read_text(encoding='utf8')
    s=s.replace('@TITLE_ID@',p['title_id']).replace('@DATA_ROOT@',root).replace('@SLUG@',slug)
    include=''; opened=''; tick=''; closed=''
    if adapter=='breath':
        include='#include "breath_achievements.h"\n#include "breath_pa.h"'
        opened='int ach_rc=breath_achievements_ps5_open(library_root,prefix,pad_status==PW_OK?pad.user_id:-1); (void)ach_rc;'
        tick='breath_achievements_ps5_tick(now);';closed='breath_pa_close();'
    elif adapter!='none':
        include='#include "studio_pa.h"'
        opened='int ach_rc=studio_pa_open(library_root,prefix,pad_status==PW_OK?pad.user_id:-1); (void)ach_rc;'
        closed='studio_pa_close();'
    for a,b in {'@ACH_INCLUDE@':include,'@ACH_OPEN@':opened,'@ACH_TICK@':tick,'@ACH_CLOSE@':closed}.items():s=s.replace(a,b)
    (out/'wine64_main.c').write_text(s,encoding='utf8',newline='\n')
    s=(R/'src/breath/wine_title/breath_bootstrap.c').read_text(encoding='utf8')
    for a,b in [('"breath_bootstrap.h"','"studio_bootstrap.h"'),('breath_bootstrap','studio_bootstrap'),('BREATH_DATA_ROOT','STUDIO_DATA_ROOT'),('BREATH_PACKAGE_ROOT','STUDIO_PACKAGE_ROOT'),('/data/breath-wine',root),('PPSA99397',p['title_id']),('prefixes/breath','prefixes/'+slug),('Breath-Wine-','Port-Studio-'),('.breath-', '.port-studio-'),('Breath:', 'Port Station:')]:s=s.replace(a,b)
    s=s.replace('Port-Studio-'+p['title_id']+'-v1','Port-Studio-'+p['title_id']+'-'+game+'-v1')
    # Extra writable NW.js Chromium user directory is absent from the file manifest.
    needle=' f=fopen(mark,"wb");if(!f)return -14;'
    if p['profile']=='nwjs-canvas':
        s=s.replace(needle,' snprintf(dest,sizeof(dest),"%s/prefixes/'+slug+'/drive_c/PortStudioNW/Default/.folder",root);if(folders(dest))return -17;\n'+needle)
    sync=(R/'port_station/templates/sync_profiles.c.inc').read_text().replace('@SLUG@',slug).replace('@TITLE_ID@',p['title_id'])
    owned=''
    if adapter=='nwjs-steam':
        owned=','.join(['']+[json.dumps('prefixes/'+slug+'/drive_c/Games/'+slug+'/www/js/'+n)for n in ['prospero_file_bridge.js','port_studio_achievements.js']])
    sync=sync.replace('@STUDIO_FILES@',owned)
    s=s.replace('int studio_bootstrap(const char*root){',sync+'\nint studio_bootstrap(const char*root){')
    s=s.replace('int result=install(root);','int result=install(root);if(!result)result=sync_profiles(root);')
    (out/'studio_bootstrap.c').write_text(s,encoding='utf8',newline='\n')
    (out/'studio_bootstrap.h').write_text('int studio_bootstrap(const char *root);\n')
    if adapter=='none':return
    names=[a['id']for a in catalog['achievements']];titles=[a['title']for a in catalog['achievements']]
    prefix='breath_pa'if adapter=='breath'else'studio'
    h='#include <stddef.h>\nstatic const unsigned char '+prefix+'_catalog[]=\n'+literal(blob)+';\n'
    for i,(digest,data)in enumerate(resources.items()):h+=f'static const unsigned char pa_icon_{i}[]=\n'+literal(data)+';\n'
    h+='static const struct{const unsigned char*data;size_t size;const char*hash;}'+prefix+'_assets[]={\n'
    for i,digest in enumerate(resources):h+=f'{{pa_icon_{i},sizeof(pa_icon_{i})-1,"{digest}"}},\n'
    h+='};\n'
    if adapter=='breath':
        h+='#define BREATH_PA_GAME_ID '+c_string(game)+'\n'
        h+='#define BREATH_PA_CATALOG_TITLES 1\nstatic const struct{const char*id,*title;}breath_pa_titles[]={'+','.join('{'+c_string(i)+','+c_string(t)+'}'for i,t in zip(names,titles))+'};\n'
    else:
        h+='static const char *const studio_ids[]={'+','.join(c_string(i)for i in names)+'};\n'
        h+='static const char *const studio_names[]={'+','.join(c_string(i)for i in titles)+'};\n'
        worker=(R/'src/tcoal/prospero_adapter/tcoal_pa.c').read_text().replace('tcoal','studio').replace('TCOAL','Port Station')
        worker=worker.replace('outbox,"studio",owner','outbox,"'+game+'",owner').replace('prefix,"studio",owner','prefix,"'+game+'",owner')
        (out/'studio_pa.c').write_text(worker,encoding='utf8',newline='\n')
        (out/'studio_pa.h').write_text('#include <stdint.h>\nint studio_pa_open(const char*,const char*,int32_t);\nvoid studio_pa_close(void);\n')
    (out/('breath_pa_assets.h'if adapter=='breath'else'studio_pa_assets.h')).write_text(h,encoding='ascii')

def cmake(p, generated):
    # CMake bracket arguments prevent interpreting user titles and paths as source code.
    def q(s):
        s=str(s).replace('\\','/');n='='
        while ']'+n+']' in s:n+='='
        return '['+n+'['+s+']'+n+']'
    old=(R/'src/tcoal/wine_title/CMakeLists.txt').read_text()
    files=old.split('set(files ',1)[1].split(')\n',1)[0]
    native=['wine64_main.c','studio_bootstrap.c']
    if p['adapter'] not in ('none','breath'):native+=['studio_pa.c']
    sources=[str(generated/n)for n in native]+[str(R/'src/tcoal/wine_title/tcoal_close.c')]
    extra=[]
    if p['adapter']=='breath':extra=['src/breath/wine_title/breath_achievements.c','src/breath/prospero_adapter/breath_pa.c','src/breath/prospero_adapter/breath_pa_ps5.c']
    elif p['adapter']!='none':extra=['sdk/prospero-achievements/bridge/pa_file_bridge.c']
    sources+=[str(R/n)for n in extra]
    includes=[generated,R/'src/tcoal/wine_title',R/'src/breath/wine_title',R/'src/breath/prospero_adapter',R/'sdk/prospero-achievements/include',R/'sdk/prospero-achievements/bridge']
    libs=''
    if p['adapter']!='none':libs=q(R/'build/prospero-achievements/ps5/libprospero_achievements.a')+' '
    return f'''cmake_minimum_required(VERSION 3.25)
project(PortStation LANGUAGES C CXX)
include({q(R/'sdk/ps5-game-port/cmake/PS5GamePort.cmake')})
set(upstream {q(R/'build/prospero-evaluation/source-v020')})
set(files {files})
set(sources {' '.join(q(s)for s in sources)})
foreach(file IN LISTS files)
 list(APPEND sources "${{upstream}}/${{file}}")
endforeach()
ps5_game_port_title(port_wine TITLE_ID {p['title_id']} TITLE_NAME {q(p['title'])}
 SOURCES ${{sources}} CONTENT_NOTE "Port Station: Windows/Wine standalone homebrew."
 LIBRARIES {libs}-lSceAgc -lSceAgcDriver -lSceVideoOut -lScePad -lSceUserService -lSceAudioOut -lSceSysmodule -lSceNet -lkernel)
target_include_directories(port_wine_objects PRIVATE "${{upstream}}/include" "${{upstream}}/src" "${{upstream}}/native" "${{upstream}}/native/ps5log" {' '.join(q(s)for s in includes)})
target_compile_definitions(port_wine_objects PRIVATE GP_BOOT_LOG="/data/port-studio-{p['title_id']}-boot.log" PW_BUILD_ID="port-studio-0.1.0" PW_WINE64_SCRIPT=0 PW_WINE64_SECONDS=0 PW_WINE64_SCRIPT_CYCLES=2 PW_WINE64_WAIT_WATCHDOG=0)
target_compile_options(port_wine_objects PRIVATE -Wno-unused-function)
set_source_files_properties("${{upstream}}/native/ps5log/ps5log.c" PROPERTIES COMPILE_OPTIONS "-include;${{upstream}}/native/ps5log/ps5log_ps5_net.h")
'''
