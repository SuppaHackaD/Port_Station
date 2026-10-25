/* Local achievement backend only: no native PS5 trophy registration. */
#include "breath_achievements.h"
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <direct.h>
#include <windows.h>
#define make_directory(p) _mkdir(p)
#define replace_file(a,b) (MoveFileExA(a,b,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)?0:-1)
#else
#define make_directory(p) mkdir(p,0777)
#define replace_file(a,b) rename(a,b)
#endif
static const char *ids[]={"COROA","OCULOS","SONIC","OLHOSARANHA","ARANHA","ENGUIA","MORCEGO","TARTARUGA","THEEND","BUG","SPEEDRUN"};
static void log_message(BreathAchievements *a,const char *format,...){
    if(!a->log)return;char text[256];va_list args;va_start(args,format);vsnprintf(text,sizeof(text),format,args);va_end(args);a->log(text);
}
static int parents(const char *path){
    char text[1024];if(strlen(path)>=sizeof(text))return -1;strcpy(text,path);
    for(char *p=text+1;*p;p++)if(*p=='/'){*p=0;if(make_directory(text)&&errno!=EEXIST)return -1;*p='/';}return 0;
}
static int save(BreathAchievements *a,uint32_t mask){
    char temp[1060],text[96];snprintf(temp,sizeof(temp),"%s.new",a->ledger);
    int n=snprintf(text,sizeof(text),"BREATH_LEDGER_V1\t%08x\t%03x\n",a->user,mask);
    FILE *f=fopen(temp,"wb");if(!f)return -1;
    int ok=fwrite(text,1,(size_t)n,f)==(size_t)n;int closed=fclose(f);
    return ok&&!closed&&!replace_file(temp,a->ledger)?0:-1;
}
int breath_achievements_open(BreathAchievements *a,const char *root,const char *prefix,
                             int32_t user,BreathAchievementMessage log,BreathAchievementMessage notify){
    memset(a,0,sizeof(*a));a->log=log;a->notify=notify;
    if(user<0||strlen(root)>700||strlen(prefix)>700)return -1;
    a->user=(uint32_t)user;
    snprintf(a->ledger,sizeof(a->ledger),"%s/achievements/users/%08x/unlocks-v1.txt",root,a->user);
    snprintf(a->events,sizeof(a->events),"%s/drive_c/BreathPS5/events-%08x.tsv",prefix,a->user);
    if(parents(a->ledger)||parents(a->events))return -2;
    FILE *f=fopen(a->ledger,"rb");
    if(f){
        char text[96]={0},canonical[96];size_t n=fread(text,1,sizeof(text)-1,f);int read_error=(ferror)(f);fclose(f);
        unsigned owner=0,mask=0;
        if(read_error||sscanf(text,"BREATH_LEDGER_V1\t%x\t%x",&owner,&mask)!=2||owner!=a->user||mask>0x7ff)return -3;
        int length=snprintf(canonical,sizeof(canonical),"BREATH_LEDGER_V1\t%08x\t%03x\n",owner,mask);
        if(n!=(size_t)length||memcmp(text,canonical,n))return -3;a->seen=mask;
    }else if(errno!=ENOENT)return -3;
    char context[1024],text[64];snprintf(context,sizeof(context),"%s/drive_c/BreathPS5/context-v1.txt",prefix);
    f=fopen(context,"wb");if(!f)return -4;
    int n=snprintf(text,sizeof(text),"BREATH_CONTEXT_V1\t%08x\n",a->user);
    int ok=fwrite(text,1,(size_t)n,f)==(size_t)n;int closed=fclose(f);if(!ok||closed)return -4;
    a->active=1;log_message(a,"backend=local user=%08x loaded=%03x",a->user,a->seen);return 0;
}
int breath_achievements_poll(BreathAchievements *a){
    if(!a->active)return -1;FILE *f=fopen(a->events,"rb");if(!f)return errno==ENOENT?0:-2;
    if(fseek(f,a->offset,SEEK_SET)){fclose(f);return -2;}
    int unlocked=0;char text[96];
    for(unsigned row=0;row<64&&fgets(text,sizeof(text),f);row++){
        size_t size=strlen(text);long end=ftell(f);if(end<0)break;
        int complete=size&&text[size-1]=='\n';
        if(a->discarding){a->offset=end;if(complete)a->discarding=0;continue;}
        if(!complete){if(size==sizeof(text)-1){a->discarding=1;a->offset=end;log_message(a,"ignored oversized event");}break;}
        char canonical[96];unsigned owner=0,id=0;
        snprintf(canonical,sizeof(canonical),"BREATH_BRIDGE_V1\t%08x\n",a->user);
        if(!strcmp(text,canonical)){
            if(!a->handshake){a->handshake=1;log_message(a,"managed bridge ready user=%08x",a->user);}
            a->offset=end;continue;
        }
        int fields=sscanf(text,"BREATH_UNLOCK_V1\t%x\t%u",&owner,&id);
        snprintf(canonical,sizeof(canonical),"BREATH_UNLOCK_V1\t%08x\t%u\n",owner,id);
        if(fields!=2||owner!=a->user||id>=11||strcmp(text,canonical)){log_message(a,"ignored invalid or foreign event");a->offset=end;continue;}
        uint32_t bit=1u<<id;
        if(!(a->seen&bit)){
            if(save(a,a->seen|bit)){log_message(a,"ledger write failed user=%08x id=%u errno=%d; retry pending",a->user,id,errno);break;}
            a->seen|=bit;unlocked++;log_message(a,"unlocked user=%08x id=%u name=%s backend=local",a->user,id,ids[id]);
            if(a->notify){char message[160];snprintf(message,sizeof(message),"Breath - conquista local: %s",ids[id]);a->notify(message);}
        }
        a->offset=end;
    }
    int failed=(ferror)(f);fclose(f);return failed?-2:unlocked;
}
