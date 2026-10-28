/* SPDX-License-Identifier: GPL-3.0-or-later
 * Read-only observer for verified, empty-file achievement markers in drive_c.
 * Existing files are baselined before Wine starts; only new markers enqueue.
 */
#ifndef STATION_FILE_MARKERS_H
#define STATION_FILE_MARKERS_H
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#ifndef _WIN32
#include <unistd.h>
#define station_marker_stat lstat
#define station_marker_sync(f) fsync(fileno(f))
#else
#include <io.h>
#define station_marker_stat stat
#define station_marker_sync(f) _commit(_fileno(f))
#endif
typedef struct { const char *id, *path, *event; } StationMarkerRule;
typedef struct { char root[1024]; unsigned char state[256], stable[256]; unsigned count; } StationMarkers;
typedef int (*StationMarkerEnqueue)(void *, const char *, const char *);

/* 0 absent, 1 a regular empty file, 2 another existing object, -1 read error. */
static int station_marker_probe(const char *root, const char *relative)
{
    char path[1600];struct stat st;
    int n=snprintf(path,sizeof(path),"%s/%s",root,relative);
    if(n<0||(size_t)n>=sizeof(path))return -1;
    if(station_marker_stat(path,&st))return errno==ENOENT?0:-1;
    return S_ISREG(st.st_mode)&&st.st_size==0?1:2;
}
static int station_markers_open(StationMarkers *state,const char *prefix,
                                const StationMarkerRule *rules,unsigned count,
                                const char *identity)
{
    if(!state||!prefix||!rules||!count||count>256||!identity||strlen(identity)!=64)return -1;
    for(unsigned i=0;i<64;i++)if(!((identity[i]>='0'&&identity[i]<='9')||(identity[i]>='a'&&identity[i]<='f')))return -1;
    memset(state,0,sizeof(*state));
    int n=snprintf(state->root,sizeof(state->root),"%s/drive_c",prefix);
    if(n<0||(size_t)n>=sizeof(state->root))return -1;
    char path[1300],temp[1320],saved[600],expected[600];
    n=snprintf(path,sizeof(path),"%s/ProsperoAchievements/markers-%s-v1.txt",state->root,identity);
    if(n<0||(size_t)n>=sizeof(path))return -1;
    int header=snprintf(expected,sizeof(expected),"PA_MARKER_BASELINE_V1\t%s\n",identity);
    FILE *in=fopen(path,"rb");
    if(in){
        size_t size=fread(saved,1,sizeof(saved),in);int error=ferror(in);fclose(in);
        if(error||size!=(size_t)header+count||memcmp(saved,expected,(size_t)header))return -2;
        for(unsigned i=0;i<count;i++){
            if(saved[header+i]!='1'&&saved[header+i]!='2')return -2;
            state->state[i]=(unsigned char)(saved[header+i]-'0');
        }
        state->count=count;return 0;
    }
    if(errno!=ENOENT)return -2;
    for(unsigned i=0;i<count;i++){
        int found=station_marker_probe(state->root,rules[i].path);
        if(found<0)return -2;
        /* 1 armed after absent baseline, 2 ignored/queued. The initial
         * baseline is durable, so a real marker survives queue failures or
         * closing immediately after an award. Re-enqueue uses the same event
         * ID and the backend suppresses duplicate unlocks/popups. */
        state->state[i]=(unsigned char)(found?2:1);
        expected[header+i]=(char)('0'+state->state[i]);
    }
    snprintf(temp,sizeof(temp),"%s.new",path);FILE *out=fopen(temp,"wb");if(!out)return -2;
    size_t size=(size_t)header+count;
    int ok=fwrite(expected,1,size,out)==size;
    if(ok&&(fflush(out)||station_marker_sync(out)))ok=0;
    if(fclose(out))ok=0;
    if(!ok||rename(temp,path))return -2;
    state->count=count;return 0;
}
static int station_markers_poll(StationMarkers *state,const StationMarkerRule *rules,
                                StationMarkerEnqueue enqueue,void *context)
{
    if(!state||!rules||!enqueue)return -1;
    int queued=0;
    for(unsigned i=0;i<state->count;i++){
        if(state->state[i]==2)continue;
        int found=station_marker_probe(state->root,rules[i].path);
        if(state->state[i]==0){
            if(found>=0)state->state[i]=(unsigned char)(found?2:1);
            continue;
        }
        if(found!=1){state->stable[i]=0;continue;}
        if(!state->stable[i]){state->stable[i]=1;continue;}
        if(!enqueue(context,rules[i].id,rules[i].event)){state->state[i]=2;queued++;}
    }
    return queued;
}
#endif
