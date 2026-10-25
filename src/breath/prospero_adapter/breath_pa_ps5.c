#include "breath_pa.h"
#include "breath_achievements.h"
#include "ps5log.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static BreathAchievements local;
static BreathPA client;
static char data_root[720];
static int running,stopping,finished;
static uint64_t fallback_poll;
static void event_log(const char *s){PS5LOG_LOG("BREATH ACH %s",s);}
static void event_notice(const char *text){
    struct{char reserved[45];char message[3075];}r={0};
    extern int sceKernelSendNotificationRequest(int,void *,size_t,int);
    snprintf(r.message,sizeof(r.message),"%s",text);sceKernelSendNotificationRequest(0,&r,sizeof(r),0);
}
static void confirmed_unlock(void *userdata,const char *game,const char *user,const char *id){
    (void)userdata;(void)game;(void)user;char text[512];
    if(breath_pa_notification(text,sizeof(text),id)>0)event_notice(text);
}
static uint64_t millis(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return(uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static void capture_local(void){
    int rc=breath_achievements_poll(&local);
    if(rc<0)PS5LOG_LOG("BREATH PA local read rc=%d",rc);
    if(client.ready){
        rc=breath_pa_capture(&client,local.seen);
        if(rc<0)PS5LOG_LOG("BREATH PA queue rc=%d errno=%d stage=%s",rc,client.sdk.last_errno,client.sdk.last_stage?client.sdk.last_stage:"?");
    }
}
static void *worker(void *unused){
    (void)unused;uint64_t prepare_at=0,pump_at=0;unsigned delay=1000;int previous=-999;
    while(!__atomic_load_n(&stopping,__ATOMIC_ACQUIRE)){
        uint64_t now=millis();
        if(!client.ready&&now>=prepare_at){
            int rc=breath_pa_open(&client,data_root,local.user,PA_SDK_DEFAULT_PORT);prepare_at=now+10000;
            PS5LOG_LOG("BREATH PA prepare rc=%d user=%08x imported_mask=%03x",rc,local.user,local.seen);
        }
        capture_local();
        if(client.ready&&now>=pump_at&&!__atomic_load_n(&stopping,__ATOMIC_ACQUIRE)){
            int rc=breath_pa_pump_with_callback(&client,confirmed_unlock,NULL);
            if(rc!=previous||rc>0)PS5LOG_LOG("BREATH PA pump rc=%d HTTP=%d queued_mask=%03x instance=%s",rc,client.sdk.last_http_status,client.queued,client.sdk.synced_instance);
            previous=rc;if(rc<0){delay=delay<30000?delay*2:60000;if(delay>60000)delay=60000;}else delay=1000;
            pump_at=millis()+delay;
        }
        for(unsigned i=0;i<25&&!__atomic_load_n(&stopping,__ATOMIC_ACQUIRE);i++)usleep(10000);
    }
    /* Final disk pass only. Never make the console wait for a network retry. */
    capture_local();__atomic_store_n(&finished,1,__ATOMIC_RELEASE);return NULL;
}
int breath_achievements_ps5_open(const char *root,const char *prefix,int32_t user){
    if(strlen(root)>=sizeof(data_root))return -1;
    int rc=breath_achievements_open(&local,root,prefix,user,event_log,NULL);
    if(rc){event_notice("Breath: falha ao preparar registro local de conquistas.");return rc;}
    strcpy(data_root,root);pthread_t thread;pthread_attr_t attr;pthread_attr_init(&attr);
    rc=pthread_attr_setstacksize(&attr,512u*1024u);
    if(!rc)rc=pthread_create(&thread,&attr,worker,NULL);
    pthread_attr_destroy(&attr);
    if(!rc){pthread_detach(thread);running=1;PS5LOG_LOG("BREATH PA worker started SDK=%s",PA_SDK_VERSION);}
    else {local.notify=event_notice;PS5LOG_LOG("BREATH PA worker unavailable rc=%d; keeping local bridge",rc);}
    /* Backend/thread failure never prevents the game from starting. */
    return 0;
}
void breath_achievements_ps5_tick(uint64_t now){
    if(running||now<fallback_poll)return;fallback_poll=now+250000000u;(void)breath_achievements_poll(&local);
}
void breath_pa_close(void){
    if(!running)return;__atomic_store_n(&stopping,1,__ATOMIC_RELEASE);
    for(unsigned i=0;i<250&&!__atomic_load_n(&finished,__ATOMIC_ACQUIRE);i++)usleep(10000);
    /* On an OS-forced close the existing ledger also remains a replay source. */
}
