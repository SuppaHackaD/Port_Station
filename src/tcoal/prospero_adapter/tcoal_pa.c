#include "prospero_achievements.h"
#include "tcoal_pa.h"
#include "pa_file_bridge.h"
#include "tcoal_pa_assets.h"
#include "ps5log.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static PA_SDK sdk;
static PA_FileBridge bridge;
static char outbox[800],owner[9];
static int running,stop,finished;
static void unlocked(void *userdata,const char *game,const char *user,const char *id){
    (void)userdata;(void)game;(void)user;
    for(size_t i=0;i<sizeof(tcoal_ids)/sizeof(tcoal_ids[0]);i++)if(!strcmp(id,tcoal_ids[i])){
        struct{char reserved[45];char message[3075];}r={0};
        extern int sceKernelSendNotificationRequest(int,void *,size_t,int);
        snprintf(r.message,sizeof(r.message),"Prospero Achievements - TCOAL\nConquista desbloqueada: %s",tcoal_names[i]);
        int rc=sceKernelSendNotificationRequest(0,&r,sizeof(r),0);
        PS5LOG_LOG("TCOAL PA notification id=%s rc=%d",id,rc);(void)rc;break;
    }
}
static uint64_t ms(void){struct timespec t;return clock_gettime(CLOCK_MONOTONIC,&t)?0:(uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static int prepare(void){
    int rc=pa_sdk_init(&sdk,outbox,"tcoal",owner,PA_SDK_DEFAULT_PORT);if(rc)return rc;
    for(size_t i=0;i<sizeof(tcoal_assets)/sizeof(tcoal_assets[0]);i++){
        char hash[65];rc=pa_sdk_asset(&sdk,tcoal_assets[i].data,tcoal_assets[i].size,hash);if(rc)return rc;
        if(strcmp(hash,tcoal_assets[i].hash))return -3;
    }
    return pa_sdk_catalog(&sdk,tcoal_catalog,sizeof(tcoal_catalog)-1);
}
static void *worker(void *unused){
    (void)unused;int ready=0,previous=-999,logged=0;unsigned delay=1000;uint64_t prepare_at=0,pump_at=0;
    while(!__atomic_load_n(&stop,__ATOMIC_ACQUIRE)){
        uint64_t now=ms();
        if(!ready&&now>=prepare_at){int rc=prepare();ready=rc==0;prepare_at=now+10000;PS5LOG_LOG("TCOAL PA prepare rc=%d user=%s",rc,owner);}
        if(ready){
            int rc=pa_file_bridge_poll(&bridge);
            if(rc)PS5LOG_LOG("TCOAL PA stream rc=%d offset=%ld handshake=%d",rc,bridge.offset,bridge.handshake);
            if(bridge.handshake&&!logged){logged=1;PS5LOG_LOG("TCOAL PA JS hook ready user=%s",owner);}
            if(now>=pump_at&&!__atomic_load_n(&stop,__ATOMIC_ACQUIRE)){
                rc=pa_sdk_pump_with_callback(&sdk,unlocked,NULL);if(rc!=previous||rc>0)PS5LOG_LOG("TCOAL PA pump rc=%d HTTP=%d instance=%s",rc,sdk.last_http_status,sdk.synced_instance);
                previous=rc;if(rc<0){delay=delay<30000?delay*2:60000;if(delay>60000)delay=60000;}else delay=1000;
                pump_at=ms()+delay;
            }
        }
        for(unsigned i=0;i<25&&!__atomic_load_n(&stop,__ATOMIC_ACQUIRE);i++)usleep(10000);
    }
    if(ready)(void)pa_file_bridge_poll(&bridge);__atomic_store_n(&finished,1,__ATOMIC_RELEASE);return NULL;
}
int tcoal_pa_open(const char *root,const char *prefix,int32_t user){
    if(user<0)return -1;snprintf(owner,sizeof(owner),"%08x",(unsigned)user);
    int n=snprintf(outbox,sizeof(outbox),"%s/achievements/users/%s/prospero-v1",root,owner);if(n<0||(size_t)n>=sizeof(outbox))return -1;
    int rc=pa_file_bridge_open(&bridge,&sdk,prefix,"tcoal",owner,tcoal_ids,sizeof(tcoal_ids)/sizeof(tcoal_ids[0]));if(rc)return rc;
    pthread_t thread;pthread_attr_t attr;pthread_attr_init(&attr);rc=pthread_attr_setstacksize(&attr,512*1024);
    if(!rc)rc=pthread_create(&thread,&attr,worker,NULL);pthread_attr_destroy(&attr);
    if(!rc){pthread_detach(thread);running=1;}return rc;
}
void tcoal_pa_close(void){
    if(!running)return;__atomic_store_n(&stop,1,__ATOMIC_RELEASE);
    for(unsigned i=0;i<250&&!__atomic_load_n(&finished,__ATOMIC_ACQUIRE);i++)usleep(10000);
}
