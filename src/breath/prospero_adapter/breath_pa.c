/* Adapter for the game's existing local ledger, never a gameplay-memory scan. */
#include "breath_pa.h"
#include "breath_pa_assets.h"
#include <stdio.h>
#include <string.h>
static const char *ids[]={"COROA","OCULOS","SONIC","OLHOSARANHA","ARANHA","ENGUIA","MORCEGO","TARTARUGA","THEEND","BUG","SPEEDRUN"};
int breath_pa_open(BreathPA *a,const char *root,uint32_t user,unsigned port){
    char path[800],owner[9];memset(a,0,sizeof(*a));
    int n=snprintf(path,sizeof(path),"%s/achievements/users/%08x/prospero-v1",root,user);
    if(n<0||(size_t)n>=sizeof(path))return PA_SDK_INVALID;
    snprintf(owner,sizeof(owner),"%08x",user);
    int rc=pa_sdk_init(&a->sdk,path,"breath",owner,port);if(rc)return rc;
    for(size_t i=0;i<sizeof(breath_pa_assets)/sizeof(breath_pa_assets[0]);i++){
        char hash[65];rc=pa_sdk_asset(&a->sdk,breath_pa_assets[i].data,breath_pa_assets[i].size,hash);
        if(rc)return rc;if(strcmp(hash,breath_pa_assets[i].hash))return PA_SDK_INVALID;
    }
    rc=pa_sdk_catalog(&a->sdk,breath_pa_catalog,sizeof(breath_pa_catalog)-1);if(rc)return rc;
    a->ready=1;return 0;
}
int breath_pa_capture(BreathPA *a,uint32_t earned_mask){
    if(!a||!a->ready||earned_mask>0x7ffu)return PA_SDK_INVALID;
    for(unsigned i=0;i<11;i++)if((earned_mask&(1u<<i))&&!(a->queued&(1u<<i))){
        char event[65];snprintf(event,sizeof(event),"breath-unlock-v1-%s",ids[i]);
        int rc=pa_sdk_unlock(&a->sdk,ids[i],event);if(rc)return rc;
        a->queued|=1u<<i;
    }
    return 0;
}
int breath_pa_pump(BreathPA *a){return a&&a->ready?pa_sdk_pump(&a->sdk):PA_SDK_INVALID;}
int breath_pa_pump_with_callback(BreathPA *a,PA_UnlockCallback callback,void *userdata){
    return a&&a->ready?pa_sdk_pump_with_callback(&a->sdk,callback,userdata):PA_SDK_INVALID;
}
const char *breath_pa_title(const char *id){
    if(!id)return NULL;
#ifdef BREATH_PA_CATALOG_TITLES
    for(size_t i=0;i<sizeof(breath_pa_titles)/sizeof(breath_pa_titles[0]);i++)if(!strcmp(id,breath_pa_titles[i].id))return breath_pa_titles[i].title;
#else
    /* Keep older generated resources buildable; current bundles embed titles. */
    for(size_t i=0;i<sizeof(ids)/sizeof(ids[0]);i++)if(!strcmp(id,ids[i]))return ids[i];
    if(!strcmp(id,"PLATINUM"))return id;
#endif
    return NULL;
}
int breath_pa_notification(char *message,size_t capacity,const char *id){
    const char *title=breath_pa_title(id);if(!message||!capacity||!title)return -1;
    int n=snprintf(message,capacity,"Prospero Achievements - Breath\nConquista desbloqueada: %s",title);
    return n>0&&(size_t)n<capacity?n:-1;
}
