#include "prospero_achievements.h"
#include "pa_common.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <errno.h>
#include <sys/stat.h>
static int sdk_error(PA_SDK *s,const char *stage,int result){
    s->last_stage=stage;s->last_errno=errno;return result;
}
static int http(PA_SDK *s,const char *method,const char *path,const char *type,const void *body,size_t size,char **reply){
    *reply=NULL;pa_socket fd=pa_connect(s->port);if(fd==PA_INVALID)return PA_SDK_OFFLINE;
    char h[1024];int hn=snprintf(h,sizeof(h),"%s %s HTTP/1.1\r\nHost: 127.0.0.1:%u\r\nConnection: close\r\nContent-Type: %s\r\nContent-Length: %zu\r\n\r\n",method,path,s->port,type,size);
    int result=PA_SDK_OFFLINE,status=0;
    if(hn<=0||(size_t)hn>=sizeof(h)||pa_send_all(fd,h,(size_t)hn)||(size&&pa_send_all(fd,body,size)))goto done;
    char head[8193];size_t used=0;head[0]=0;
    while(used<sizeof(head)-1){int r=(int)recv(fd,head+used,1,0);if(r!=1)goto done;head[++used]=0;if(used>=4&&!memcmp(head+used-4,"\r\n\r\n",4))break;}
    if(!strstr(head,"\r\n\r\n")||sscanf(head,"HTTP/1.1 %d",&status)!=1)goto done;
    char *length=strstr(head,"\r\nContent-Length: ");if(!length)goto done;
    char *end=NULL;unsigned long n=strtoul(length+18,&end,10);if(n>128*1024||!end||memcmp(end,"\r\n",2))goto done;
    *reply=malloc(n+1);if(!*reply){result=PA_SDK_STORAGE;goto done;}
    size_t pos=0;while(pos<n){int r=(int)recv(fd,*reply+pos,(int)(n-pos),0);if(r<=0){free(*reply);*reply=NULL;goto done;}pos+=(size_t)r;}
    (*reply)[n]=0;s->last_http_status=status;result=status;
done:
    pa_socket_close(fd);return result;
}
int pa_sdk_init(PA_SDK *s,const char *root,const char *game,const char *user,unsigned port){
    if(!s||!root||strlen(root)>=sizeof(s->root)||!pa_game_id(game)||!pa_user(user)||!port||port>65535)return PA_SDK_INVALID;
    memset(s,0,sizeof(*s));strcpy(s->root,root);strcpy(s->game_id,game);strcpy(s->user_id,user);s->port=port;
    if(pa_net_init()||pa_mkdirs(root))return PA_SDK_STORAGE;
    char p[1024];snprintf(p,sizeof(p),"%s/pending",root);if(pa_mkdirs(p))return PA_SDK_STORAGE;
    snprintf(p,sizeof(p),"%s/assets",root);if(pa_mkdirs(p))return PA_SDK_STORAGE;
    /* Do not accidentally reuse another game's or user's persistent outbox. */
    char identity[180];snprintf(identity,sizeof(identity),"PA_SDK_V1\t%s\t%s\n",game,user);
    snprintf(p,sizeof(p),"%s/identity.txt",root);size_t n;unsigned char *old=pa_read(p,512,&n);
    if(old){int same=n==strlen(identity)&&!memcmp(old,identity,n);free(old);return same?0:PA_SDK_CONFLICT;}
    struct stat st;if(!stat(p,&st))return PA_SDK_STORAGE;
    return pa_atomic(p,identity,strlen(identity))?PA_SDK_STORAGE:0;
}
int pa_sdk_asset(PA_SDK *s,const void *b,size_t n,char hash[65]){
    if(!s||!b||!hash||n<8||n>PA_MAX_BODY||memcmp(b,"\x89PNG\r\n\x1a\n",8))return PA_SDK_INVALID;
    pa_hash(b,n,hash);char p[1024];snprintf(p,sizeof(p),"%s/assets/%s.png",s->root,hash);
    if(pa_atomic(p,b,n))return PA_SDK_STORAGE;s->synced_catalog[0]=0;return 0;
}
int pa_sdk_catalog(PA_SDK *s,const void *b,size_t n){
    if(!s||n>PA_MAX_CATALOG)return PA_SDK_INVALID;cJSON *j=pa_json(b,n);const char *id=pa_string(j,"game_id");
    int valid=id&&!strcmp(id,s->game_id);cJSON_Delete(j);if(!valid)return PA_SDK_INVALID;
    char p[1024];snprintf(p,sizeof(p),"%s/catalog.json",s->root);
    if(pa_atomic(p,b,n))return PA_SDK_STORAGE;s->synced_catalog[0]=0;return 0;
}
int pa_sdk_pending(PA_SDK *s){
    char p[1024];snprintf(p,sizeof(p),"%s/pending",s->root);PA_Names list;
    if(pa_names_get(p,&list)){s->directory_method=list.method;int result=sdk_error(s,"queue.list",PA_SDK_STORAGE);pa_names_free(&list);return result;}
    int count=0;s->directory_method=list.method;
    for(size_t i=0;i<list.count;i++)if(strlen(list.name[i])==69&&!strcmp(list.name[i]+64,".json"))count++;
    pa_names_free(&list);return count;
}
static int enqueue(PA_SDK *s,const char *achievement,const char *event,const char *type,unsigned value){
    if(!s)return PA_SDK_INVALID;
    if(!pa_id(achievement)||!pa_id(event)||value>1000000000u)return sdk_error(s,"queue.validate",PA_SDK_INVALID);
    cJSON *j=cJSON_CreateObject();cJSON_AddStringToObject(j,"event_id",event);cJSON_AddStringToObject(j,"game_id",s->game_id);
    cJSON_AddStringToObject(j,"user_id",s->user_id);cJSON_AddStringToObject(j,"achievement_id",achievement);
    cJSON_AddStringToObject(j,"type",type);if(!strcmp(type,"progress"))cJSON_AddNumberToObject(j,"value",value);
    char *b=cJSON_PrintUnformatted(j);cJSON_Delete(j);if(!b)return sdk_error(s,"queue.json",PA_SDK_STORAGE);
    char hash[65],p[1024];pa_hash(event,strlen(event),hash);snprintf(p,sizeof(p),"%s/pending/%s.json",s->root,hash);
    size_t n;unsigned char *old=pa_read(p,4096,&n);if(old){int same=n==strlen(b)&&!memcmp(old,b,n);free(old);free(b);return same?0:PA_SDK_CONFLICT;}
    struct stat st;if(!stat(p,&st)){free(b);return sdk_error(s,"queue.existing-unreadable",PA_SDK_STORAGE);}
    int pending=pa_sdk_pending(s);if(pending<0||pending>=PA_MAX_EVENTS){free(b);if(pending>=PA_MAX_EVENTS)return sdk_error(s,"queue.limit",PA_SDK_STORAGE);return PA_SDK_STORAGE;}
    int rc=pa_atomic(p,b,strlen(b));free(b);
    if(rc)return sdk_error(s,"queue.commit",PA_SDK_STORAGE);
    s->last_stage="queue.ready";s->last_errno=0;return 0;
}
int pa_sdk_unlock(PA_SDK *s,const char *a,const char *e){return enqueue(s,a,e,"unlock",0);}
int pa_sdk_progress(PA_SDK *s,const char *a,unsigned v,const char *e){return enqueue(s,a,e,"progress",v);}
int pa_sdk_pump_with_callback(PA_SDK *s,PA_UnlockCallback callback,void *userdata){
    if(!s)return PA_SDK_INVALID;char *reply=NULL;int status=http(s,"GET","/api/v1/info","application/json",NULL,0,&reply);
    if(status!=200){free(reply);return status<0?status:PA_SDK_PROTOCOL;}
    cJSON *info=pa_json(reply,strlen(reply));free(reply);int major=0;const char *instance=pa_string(info,"instance_id");
    const char *service=pa_string(info,"service");
    if(!service||strcmp(service,"prospero_achievements")||pa_integer(info,"api_major",1,1,&major)||!instance||strlen(instance)>=96){cJSON_Delete(info);return PA_SDK_PROTOCOL;}
    char current[96];strcpy(current,instance);cJSON_Delete(info);
    char p[1100],catalog_hash[65];size_t n;snprintf(p,sizeof(p),"%s/catalog.json",s->root);unsigned char *catalog=pa_read(p,PA_MAX_CATALOG,&n);
    if(!catalog)return PA_SDK_STORAGE;pa_hash(catalog,n,catalog_hash);
    if(strcmp(s->synced_instance,current)||strcmp(s->synced_catalog,catalog_hash)){
        snprintf(p,sizeof(p),"%s/assets",s->root);PA_Names assets;
        if(pa_names_get(p,&assets)){int result=sdk_error(s,"assets.list",PA_SDK_STORAGE);pa_names_free(&assets);free(catalog);return result;}
        for(size_t i=0;i<assets.count;i++){
            const char *name=assets.name[i];
            if(strlen(name)!=68||strcmp(name+64,".png"))continue;
            char id[65];memcpy(id,name,64);id[64]=0;if(!pa_digest(id))continue;
            snprintf(p,sizeof(p),"%s/assets/%s",s->root,name);size_t size;unsigned char *data=pa_read(p,PA_MAX_BODY,&size);
            if(!data){pa_names_free(&assets);free(catalog);return sdk_error(s,"assets.read",PA_SDK_STORAGE);}
            char endpoint[128];snprintf(endpoint,sizeof(endpoint),"/api/v1/assets/%s.png",id);
            status=http(s,"PUT",endpoint,"image/png",data,size,&reply);free(data);free(reply);
            if(status!=200&&status!=201){pa_names_free(&assets);free(catalog);return status<0?status:PA_SDK_PROTOCOL;}
        }pa_names_free(&assets);
        status=http(s,"POST","/api/v1/catalogs","application/json",catalog,n,&reply);free(reply);
        if(status!=200&&status!=201){free(catalog);return status<0?status:PA_SDK_PROTOCOL;}
        strcpy(s->synced_instance,current);strcpy(s->synced_catalog,catalog_hash);
    }free(catalog);
    snprintf(p,sizeof(p),"%s/pending",s->root);PA_Names events;
    if(pa_names_get(p,&events)){int result=sdk_error(s,"queue.list-send",PA_SDK_STORAGE);pa_names_free(&events);return result;}
    int acknowledged=0,failed=0;
    for(size_t i=0;i<events.count;i++){
        const char *name=events.name[i];
        if(strlen(name)!=69||strcmp(name+64,".json"))continue;
        char id[65];memcpy(id,name,64);id[64]=0;if(!pa_digest(id))continue;
        snprintf(p,sizeof(p),"%s/pending/%s",s->root,name);unsigned char *data=pa_read(p,4096,&n);if(!data){failed=sdk_error(s,"queue.read",PA_SDK_STORAGE);continue;}
        cJSON *event=pa_json(data,n);const char *event_id=pa_string(event,"event_id");char expected[65];
        if(!event_id){cJSON_Delete(event);free(data);failed=PA_SDK_INVALID;continue;}pa_hash(event_id,strlen(event_id),expected);
        if(strcmp(id,expected)){cJSON_Delete(event);free(data);failed=PA_SDK_INVALID;continue;}
        status=http(s,"POST","/api/v1/events","application/json",data,n,&reply);free(data);
        cJSON *ack=reply?pa_json(reply,strlen(reply)):NULL;const char *acked=pa_string(ack,"event_id"),*kind=pa_string(ack,"status");
        if((status==200||status==201)&&acked&&kind&&!strcmp(acked,event_id)&&(!strcmp(kind,"accepted")||!strcmp(kind,"duplicate"))){
            if(callback&&!strcmp(kind,"accepted")){
                cJSON *awards=cJSON_GetObjectItemCaseSensitive(ack,"new_unlocks");
                if(cJSON_IsArray(awards)&&cJSON_GetArraySize(awards)<=PA_MAX_ACH){
                    for(cJSON *a=awards->child;a;a=a->next){
                        if(!cJSON_IsString(a)||!pa_id(a->valuestring))continue;
                        int duplicate=0;for(cJSON *b=awards->child;b!=a;b=b->next)if(cJSON_IsString(b)&&!strcmp(b->valuestring,a->valuestring))duplicate=1;
                        if(!duplicate)callback(userdata,s->game_id,s->user_id,a->valuestring);
                    }
                }
            }
            if(remove(p))failed=PA_SDK_STORAGE;else acknowledged++;
        }else{failed=status<0?status:status==409?PA_SDK_CONFLICT:PA_SDK_PROTOCOL;if(status==404)s->synced_instance[0]=0;}
        cJSON_Delete(ack);cJSON_Delete(event);free(reply);if(status<0)break;
    }pa_names_free(&events);return failed?failed:acknowledged;
}
int pa_sdk_pump(PA_SDK *s){return pa_sdk_pump_with_callback(s,NULL,NULL);}
