#include "pa_file_bridge.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <direct.h>
#include <io.h>
#include <windows.h>
#define mkdir_one(p) _mkdir(p)
#define close _close
#define write _write
#define sync_fd _commit
#define open _open
#define binary _O_BINARY
#else
#include <unistd.h>
#define mkdir_one(p) mkdir(p,0700)
#define sync_fd fsync
#define binary 0
#endif
static int valid_id(const char *s,int lower){
    if(!s||!*s||strlen(s)>64||strstr(s,".."))return 0;
    for(size_t i=0;s[i];i++)if(!((s[i]>='a'&&s[i]<='z')||(!lower&&s[i]>='A'&&s[i]<='Z')||(s[i]>='0'&&s[i]<='9')||(i&&(s[i]=='.'||s[i]=='_'||s[i]=='-'))))return 0;
    return 1;
}
static int context_write(const char *path,const char *game,const char *user){
    char temp[1100],text[160];snprintf(temp,sizeof(temp),"%s.new",path);
    int n=snprintf(text,sizeof(text),"PA_FILE_CONTEXT_V1\t%s\t%s\n",game,user);
    FILE *old=fopen(path,"rb");if(old){
        char b[160]={0},owner[9]={0},oldgame[65]={0},canonical[160];size_t got=fread(b,1,sizeof(b)-1,old);int error=(ferror)(old);fclose(old);
        if(error||sscanf(b,"PA_FILE_CONTEXT_V1\t%64s\t%8s",oldgame,owner)!=2||strcmp(oldgame,game))return -1;
        for(unsigned i=0;i<8;i++)if(!((owner[i]>='0'&&owner[i]<='9')||(owner[i]>='a'&&owner[i]<='f')))return -1;
        int len=snprintf(canonical,sizeof(canonical),"PA_FILE_CONTEXT_V1\t%s\t%s\n",game,owner);if(got!=(size_t)len||memcmp(b,canonical,got))return -1;
    }else if(errno!=ENOENT)return -1;
    int fd=open(temp,O_WRONLY|O_CREAT|O_TRUNC|binary,0600);if(fd<0)return -1;
    size_t at=0;int rc=0;
    while(at<(size_t)n){int written=(int)write(fd,text+at,(unsigned)((size_t)n-at));if(written<0&&errno==EINTR)continue;if(written<=0){rc=-1;break;}at+=(size_t)written;}
    if(!rc&&sync_fd(fd))rc=-1;if(close(fd))rc=-1;if(rc)return -1;
#ifdef _WIN32
    return MoveFileExA(temp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)?0:-1;
#else
    return rename(temp,path);
#endif
}
int pa_file_bridge_open(PA_FileBridge *b,PA_SDK *s,const char *prefix,const char *game,const char *user,const char *const *ids,unsigned count){
    if(!b||!s||!prefix||strlen(prefix)>700||!valid_id(game,1)||!user||strlen(user)!=8||!ids||!count||count>256)return -1;
    for(unsigned i=0;i<8;i++)if(!((user[i]>='0'&&user[i]<='9')||(user[i]>='a'&&user[i]<='f')))return -1;
    for(unsigned i=0;i<count;i++){if(!valid_id(ids[i],0))return -1;for(unsigned j=0;j<i;j++)if(!strcmp(ids[i],ids[j]))return -1;}
    memset(b,0,sizeof(*b));b->sdk=s;b->ids=ids;b->count=count;strcpy(b->game,game);strcpy(b->user,user);
    char folder[900],context[1024];snprintf(folder,sizeof(folder),"%s/drive_c/ProsperoAchievements",prefix);
    if(mkdir_one(folder)&&errno!=EEXIST)return -2;
    snprintf(context,sizeof(context),"%s/%s-context-v1.txt",folder,game);if(context_write(context,game,user))return -2;
    snprintf(b->events,sizeof(b->events),"%s/%s-%s.tsv",folder,game,user);return 0;
}
int pa_file_bridge_poll(PA_FileBridge *b){
    FILE *f=fopen(b->events,"rb");if(!f)return errno==ENOENT?0:-2;
    if(fseek(f,b->offset,SEEK_SET)){fclose(f);return -2;}
    char text[256];int captured=0;
    for(unsigned row=0;row<128&&fgets(text,sizeof(text),f);row++){
        size_t n=strlen(text);long end=ftell(f);if(end<0){captured=-2;break;}
        int complete=n&&text[n-1]=='\n';
        if(b->discarding){b->offset=end;if(complete)b->discarding=0;continue;}
        if(!complete){if(n==sizeof(text)-1){b->discarding=1;b->offset=end;}break;}
        char canonical[256];snprintf(canonical,sizeof(canonical),"PA_FILE_BRIDGE_V1\t%s\t%s\n",b->game,b->user);
        if(!strcmp(text,canonical)){b->handshake=1;b->offset=end;continue;}
        char game[65]={0},user[9]={0},id[65]={0};
        int fields=sscanf(text,"PA_FILE_UNLOCK_V1\t%64s\t%8s\t%64s",game,user,id);
        snprintf(canonical,sizeof(canonical),"PA_FILE_UNLOCK_V1\t%s\t%s\t%s\n",game,user,id);
        if(fields!=3||strcmp(game,b->game)||strcmp(user,b->user)||strcmp(text,canonical)){b->offset=end;continue;}
        unsigned i=0;for(;i<b->count;i++)if(!strcmp(id,b->ids[i]))break;
        if(i==b->count||b->queued[i]){b->offset=end;continue;}
        /* This unlock-only transport reserves each achievement ID as its stable
         * event ID within the SDK's existing game/user namespace. */
        int rc=pa_sdk_unlock(b->sdk,id,id);if(rc){fclose(f);return rc;}
        b->queued[i]=1;captured++;b->offset=end;
    }
    int error=(ferror)(f);fclose(f);return error?-2:captured;
}
