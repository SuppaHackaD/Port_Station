#include "breath_pa.h"
#include "breath_achievements.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned notices,completion_notices;
static void unlocked(void *userdata,const char *game,const char *user,const char *id){
    (void)userdata;(void)game;(void)user;char message[512];
    if(breath_pa_notification(message,sizeof(message),id)>0){notices++;if(!strcmp(id,"PLATINUM"))completion_notices++;}
}
int main(int argc,char **argv){
    if(argc!=5)return 9;BreathAchievements local;BreathPA pa;
    int rc=breath_achievements_open(&local,argv[1],argv[2],(int32_t)strtoul(argv[3],NULL,16),NULL,NULL);
    if(!rc)rc=breath_pa_open(&pa,argv[1],local.user,(unsigned)strtoul(argv[4],NULL,10));
    char message[512];const char *title=breath_pa_title("PLATINUM");
    int titles=title&&!strcmp(title,"Breath \xe2\x80\x94 Platina")&&breath_pa_notification(message,sizeof(message),"ENGUIA")>0&&strstr(message,"First Kill: Eletric guy")&&breath_pa_notification(message,sizeof(message),"UNKNOWN")==-1;
    printf("open=%d seen=%x titles=%d\n",rc,local.seen,titles);fflush(stdout);if(rc)return 1;
    char line[32];while(fgets(line,sizeof(line),stdin)){
        if(!strcmp(line,"exit\n"))break;
        int polled=breath_achievements_poll(&local),queued=breath_pa_capture(&pa,local.seen);
        int sent=!strcmp(line,"pump\n")?breath_pa_pump_with_callback(&pa,unlocked,NULL):0;
        printf("poll=%d queue=%d sent=%d seen=%x pending=%d notices=%u completion=%u\n",polled,queued,sent,local.seen,pa_sdk_pending(&pa.sdk),notices,completion_notices);fflush(stdout);
    }
    return 0;
}
