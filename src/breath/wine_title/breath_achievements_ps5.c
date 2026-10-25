#include "breath_achievements.h"
#include "ps5log.h"
#include <stddef.h>
#include <stdio.h>
static BreathAchievements achievements;
static uint64_t next_poll;
static void event_log(const char *text){PS5LOG_LOG("BREATH ACH %s",text);}
static void event_notice(const char *text){
    struct{char reserved[45];char message[3075];}request={0};
    extern int sceKernelSendNotificationRequest(int,void *,size_t,int);
    snprintf(request.message,sizeof(request.message),"%s",text);
    sceKernelSendNotificationRequest(0,&request,sizeof(request),0);
}
int breath_achievements_ps5_open(const char *root,const char *prefix,int32_t user){
    int result=breath_achievements_open(&achievements,root,prefix,user,event_log,event_notice);
    PS5LOG_LOG("BREATH ACH initialize status=%d user=%d",result,user);
    if(result)event_notice("Breath: falha ao preparar registro local de conquistas. Consulte o log.");
    return result;
}
void breath_achievements_ps5_tick(uint64_t now){
    if(now<next_poll)return;next_poll=now+250000000u;
    int result=breath_achievements_poll(&achievements);
    if(result<0)PS5LOG_LOG("BREATH ACH queue read status=%d",result);
}
