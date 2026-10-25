#include "pa_common.h"
#include "pa_model.h"
#include "pa_web_assets.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <signal.h>
#include <time.h>
#ifdef _WIN32
#include <process.h>
#include <io.h>
#define getpid _getpid
#define strcasecmp _stricmp
#else
#include <strings.h>
#endif
static volatile sig_atomic_t running=1;
static uint64_t started;
static char instance[96];
static void stop_server(int n){(void)n;running=0;}
static void notify(const char *message){
#ifdef PA_PS5
    struct {char reserved[45];char message[3075];} req={0};
    extern int sceKernelSendNotificationRequest(int,void *,size_t,int);
    snprintf(req.message,sizeof(req.message),"%s",message);sceKernelSendNotificationRequest(0,&req,sizeof(req),0);
#else
    (void)message;
#endif
}
static void response(pa_socket s,int status,const char *mime,const void *body,size_t n){
    char head[1024];const char *reason=status<300?"OK":status==404?"Not Found":"Error";
    int len=snprintf(head,sizeof(head),
        "HTTP/1.1 %d %s\r\nContent-Length: %zu\r\nContent-Type: %s\r\nConnection: close\r\n"
        "Cache-Control: %s\r\nX-Content-Type-Options: nosniff\r\n"
        "Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'\r\n\r\n",
        status,reason,n,mime,!strcmp(mime,"image/png")?"public, max-age=31536000, immutable":"no-store");
    if(len>0&&(size_t)len<sizeof(head)){if(!pa_send_all(s,head,(size_t)len))pa_send_all(s,body,n);}
}
static void json_response(pa_socket s,int status,cJSON *j){
    char *b=cJSON_PrintUnformatted(j);
    if(b){response(s,status,"application/json; charset=utf-8",b,strlen(b));free(b);}
    else response(s,503,"application/json","{\"error\":\"out of memory\"}",25);
    cJSON_Delete(j);
}
static void error_response(pa_socket s,int code,const char *message){
    cJSON *j=cJSON_CreateObject();cJSON_AddStringToObject(j,"error",message);json_response(s,code,j);
}
static int read_request(pa_socket s,char method[12],char path[512],unsigned char **body,size_t *n,int *origin){
    char header[8193];size_t used=0;*body=NULL;*n=0;*origin=0;
    uint64_t deadline=pa_millis()+4000;
    /* Read the bounded header first. Body bytes remain in the socket. */
    while(used<sizeof(header)-1){
        if(pa_millis()>deadline)return -1;
        int r=(int)recv(s,header+used,1,0);if(r!=1)return -1;used++;header[used]=0;
        if(used>=4&&!memcmp(header+used-4,"\r\n\r\n",4))break;
    }
    if(used<4||memcmp(header+used-4,"\r\n\r\n",4))return -1;
    char version[16],extra;char *end=strstr(header,"\r\n");if(!end)return -1;*end=0;
    if(sscanf(header,"%11s %511s %15s %c",method,path,version,&extra)!=3||strcmp(version,"HTTP/1.1"))return -1;
    if(path[0]!='/'||strchr(path,'%')||strchr(path,'\\')||strchr(path,'?')||strstr(path,".."))return -1;
    int content_length=0;
    for(char *line=end+2;*line;){
        char *next=strstr(line,"\r\n");if(!next)return -1;*next=0;if(!*line)break;
        char *colon=strchr(line,':');if(!colon)return -1;*colon++=0;while(*colon==' '||*colon=='\t')colon++;
        if(!strcasecmp(line,"Content-Length")){
            if(content_length++||!*colon)return -1;
            size_t value=0;for(char *p=colon;*p;p++){if(!isdigit((unsigned char)*p))return -1;value=value*10+(unsigned)(*p-'0');if(value>PA_MAX_BODY)return -1;}*n=value;
        }else if(!strcasecmp(line,"Transfer-Encoding"))return -1;
        else if(!strcasecmp(line,"Origin"))*origin=1;
        line=next+2;
    }
    if((!strcmp(method,"POST")||!strcmp(method,"PUT"))&&!content_length)return -1;
    if(*n){*body=malloc(*n);if(!*body)return -1;size_t pos=0;
        while(pos<*n){if(pa_millis()>deadline){free(*body);*body=NULL;return -1;}int r=(int)recv(s,(char*)*body+pos,(int)(*n-pos),0);if(r<=0){free(*body);*body=NULL;return -1;}pos+=(size_t)r;}
    }return 0;
}
static void handle(pa_socket s,const char *root,int loopback){
    char method[12],path[512];unsigned char *body=NULL;size_t n=0;int origin;
    if(read_request(s,method,path,&body,&n,&origin)){error_response(s,400,"invalid or oversized HTTP request");return;}
    int get=!strcmp(method,"GET");
    if(!get&&(!loopback||origin)){error_response(s,403,"SDK writes require a local native client");free(body);return;}
    cJSON *j=NULL;int status=404;
    if(get&&!strcmp(path,"/")){
        response(s,200,"text/html; charset=utf-8",pa_web_index,sizeof(pa_web_index)-1);goto done;
    }
    if(get&&!strcmp(path,"/app.css")){
        response(s,200,"text/css; charset=utf-8",pa_web_css,sizeof(pa_web_css)-1);goto done;
    }
    if(get&&!strcmp(path,"/app.js")){
        response(s,200,"text/javascript; charset=utf-8",pa_web_js,sizeof(pa_web_js)-1);goto done;
    }
    if(get&&!strcmp(path,"/api/v1/info")){
        j=cJSON_CreateObject();cJSON_AddStringToObject(j,"service","prospero_achievements");cJSON_AddStringToObject(j,"version",PA_VERSION);
        cJSON_AddNumberToObject(j,"api_major",1);cJSON_AddNumberToObject(j,"api_minor",0);cJSON_AddStringToObject(j,"instance_id",instance);
        cJSON_AddNumberToObject(j,"uptime_ms",(double)(pa_millis()-started));
        cJSON_AddNumberToObject(j,"max_achievements",PA_MAX_ACH);cJSON_AddNumberToObject(j,"max_events_per_user_game",PA_MAX_EVENTS);
        status=200;
    }else if(get&&!strcmp(path,"/api/v1/games")){j=pa_games_get(root);status=200;}
    else if(get&&!strcmp(path,"/api/v1/users")){j=pa_users_get(root);status=200;}
    else if(get&&!strncmp(path,"/api/v1/state/",14)){
        char *user=path+14,*slash=strchr(user,'/');if(slash){*slash=0;status=pa_state_get(root,user,slash+1,&j);}
    }else if(!strcmp(method,"POST")&&!strcmp(path,"/api/v1/catalogs"))status=pa_catalog_register(root,body,n,&j);
    else if(!strcmp(method,"POST")&&!strcmp(path,"/api/v1/events"))status=pa_event_commit(root,body,n,&j);
    else if(!strcmp(method,"POST")&&!strcmp(path,"/api/v1/service/stop")){
        j=cJSON_CreateObject();cJSON_AddStringToObject(j,"status","stopping");running=0;status=200;
    }
    else if(!strncmp(path,"/api/v1/assets/",15)){
        char *id=path+15;size_t len=strlen(id);
        if(len==68&&!strcmp(id+64,".png")){
            id[64]=0;
            if(!get&&!strcmp(method,"PUT"))status=pa_asset_put(root,id,body,n,&j);
            else if(get&&pa_digest(id)){
                char file[1200];snprintf(file,sizeof(file),"%s/assets/%s.png",root,id);size_t size;unsigned char *png=pa_read(file,PA_MAX_BODY,&size);
                if(png){response(s,200,"image/png",png,size);free(png);goto done;}
            }
        }
    }
    if(j)json_response(s,status,j);else error_response(s,status,"unknown endpoint");
done:
    free(body);
}
int main(int argc,char **argv){
    const char *root="/data/prospero-achievements";unsigned port=PA_PORT;
#ifndef PA_PS5
    if(argc>1)root=argv[1];if(argc>2)port=(unsigned)strtoul(argv[2],NULL,10);
#else
    (void)argc;(void)argv;
#endif
    if(!port||port>65535||strlen(root)>800||pa_net_init())return 2;
    signal(SIGINT,stop_server);signal(SIGTERM,stop_server);
#ifndef _WIN32
    signal(SIGPIPE,SIG_IGN);
#endif
    if(pa_mkdirs(root)){char message[160];snprintf(message,sizeof(message),"Prospero Achievements: falha no diretorio de dados, errno=%d.",errno);notify(message);return 3;}
    int lock=pa_lock_root(root);if(lock<0){notify("Prospero Achievements: diretorio em uso ou indisponivel.");return 4;}
    char p[1024];const char *dirs[]={"catalogs","assets","users"};for(unsigned i=0;i<3;i++){
        snprintf(p,sizeof(p),"%s/%s",root,dirs[i]);if(pa_mkdirs(p))return 5;
    }
    pa_log_open(root);
    pa_socket listener=socket(AF_INET,SOCK_STREAM,0);if(listener==PA_INVALID){notify("Prospero Achievements: falha ao abrir socket.");return 6;}
    int reuse=1;setsockopt(listener,SOL_SOCKET,SO_REUSEADDR,(const char*)&reuse,sizeof(reuse));
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons((uint16_t)port);a.sin_addr.s_addr=htonl(INADDR_ANY);
#ifdef PA_PS5
    a.sin_len=sizeof(a);
#endif
    if(bind(listener,(struct sockaddr*)&a,sizeof(a))||listen(listener,8)){pa_socket_close(listener);pa_log("bind failed port=%u",port);notify("Prospero Achievements: porta indisponivel.");return 7;}
    started=pa_millis();snprintf(instance,sizeof(instance),"%ld-%llu-%lld",(long)getpid(),(unsigned long long)started,(long long)time(NULL));
    pa_log("START version=%s api=1 port=%u instance=%s root=%s",PA_VERSION,port,instance,root);
    char message[160];snprintf(message,sizeof(message),"Prospero Achievements %s ativo. Interface web na porta %u.",PA_VERSION,port);notify(message);
    while(running){
        fd_set set;FD_ZERO(&set);FD_SET(listener,&set);struct timeval t={1,0};
        int r=select((int)listener+1,&set,NULL,NULL,&t);if(r<=0)continue;
        struct sockaddr_in peer;
#ifdef _WIN32
        int size=sizeof(peer);
#else
        socklen_t size=sizeof(peer);
#endif
        pa_socket s=accept(listener,(struct sockaddr*)&peer,&size);if(s==PA_INVALID)continue;
        pa_net_timeout(s,2500);handle(s,root,(ntohl(peer.sin_addr.s_addr)>>24)==127);pa_socket_close(s);
    }
    pa_log("STOP instance=%s",instance);pa_socket_close(listener);
#ifdef _WIN32
    _close(lock);
#else
    close(lock);
#endif
    return 0;
}
