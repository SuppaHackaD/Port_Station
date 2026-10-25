#include "pa_model.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#include <dirent.h>
#ifdef _WIN32
#include <io.h>
#define open _open
#define close _close
#define lseek _lseeki64
#define PA_BINARY _O_BINARY
#else
#define PA_BINARY 0
#endif
static int error_json(cJSON **out,int code,const char *message){
    *out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"error",message);cJSON_AddNumberToObject(*out,"api_major",1);return code;
}
static int text_field(cJSON *j,const char *key,size_t max,int required){
    const char *s=pa_string(j,key);return s?strlen(s)>0&&strlen(s)<=max:!required;
}
void pa_catalog_free(PA_Catalog *c){cJSON_Delete(c->json);c->json=NULL;}
int pa_catalog_parse(const void *blob,size_t n,PA_Catalog *c,char error[160]){
    memset(c,0,sizeof(*c));c->json=pa_json(blob,n);
    int schema=0,meta=0;const char *why="catalogo JSON invalido";
    if(!cJSON_IsObject(c->json))goto fail;
    const char *id=pa_string(c->json,"game_id"),*icon=pa_string(c->json,"icon");
    if(!pa_game_id(id)||!pa_digest(icon)||!text_field(c->json,"title",256,1)||
       pa_integer(c->json,"schema",1,1,&schema)||pa_integer(c->json,"catalog_version",1,1000000,&c->version)){why="metadados do catalogo invalidos";goto fail;}
    strcpy(c->id,id);cJSON *list=cJSON_GetObjectItemCaseSensitive(c->json,"achievements");
    if(!cJSON_IsArray(list)||(c->count=cJSON_GetArraySize(list))<1||c->count>PA_MAX_ACH){why="quantidade de conquistas invalida";goto fail;}
    for(int i=0;i<c->count;i++){
        cJSON *a=cJSON_GetArrayItem(list,i);id=pa_string(a,"id");icon=pa_string(a,"icon");
        cJSON *completion=cJSON_GetObjectItemCaseSensitive(a,"completion");
        cJSON *hidden=cJSON_GetObjectItemCaseSensitive(a,"hidden");
        if(!cJSON_IsObject(a)||!pa_id(id)||!text_field(a,"title",256,1)||!text_field(a,"description",2048,1)||
           (icon&&!pa_digest(icon))||pa_integer(a,"target",1,1000000000,&c->target[i])||
           (completion&&!cJSON_IsBool(completion))||(hidden&&!cJSON_IsBool(hidden))){why="definicao de conquista invalida";goto fail;}
        strcpy(c->achievement[i],id);c->completion[i]=cJSON_IsTrue(completion);
        if(c->completion[i]){meta++;if(c->target[i]!=1){why="conclusao deve ter target 1";goto fail;}}
        for(int j=0;j<i;j++)if(!strcmp(id,c->achievement[j])){why="id de conquista duplicado";goto fail;}
    }
    if(meta>1||meta==c->count){why="regra de conclusao invalida";goto fail;}
    return 0;
fail:
    snprintf(error,160,"%s",why);pa_catalog_free(c);return -1;
}
int pa_catalog_load(const char *root,const char *id,PA_Catalog *c){
    if(!pa_game_id(id))return -1;char path[1200],error[160];size_t n;
    snprintf(path,sizeof(path),"%s/catalogs/%s.json",root,id);unsigned char *b=pa_read(path,PA_MAX_CATALOG,&n);
    if(!b)return -1;int rc=pa_catalog_parse(b,n,c,error);free(b);return rc;
}
static int achievement_index(PA_Catalog *c,const char *id){
    if(!id)return -1;for(int i=0;i<c->count;i++)if(!strcmp(c->achievement[i],id))return i;return -1;
}
static int asset_exists(const char *root,const char *id){
    char p[1200];struct stat st;snprintf(p,sizeof(p),"%s/assets/%s.png",root,id);
    return !stat(p,&st)&&st.st_size>0;
}
int pa_catalog_register(const char *root,const void *blob,size_t n,cJSON **out){
    PA_Catalog *c=calloc(1,sizeof(*c)),*old=calloc(1,sizeof(*old));char why[160];int rc=400;
    if(!c||!old){free(c);free(old);return error_json(out,503,"sem memoria");}
    if(n>PA_MAX_CATALOG||pa_catalog_parse(blob,n,c,why)){rc=error_json(out,400,n>PA_MAX_CATALOG?"catalogo muito grande":why);goto done;}
    if(!asset_exists(root,pa_string(c->json,"icon"))){rc=error_json(out,409,"envie primeiro o icone do jogo");goto done;}
    cJSON *a=NULL;cJSON_ArrayForEach(a,cJSON_GetObjectItemCaseSensitive(c->json,"achievements")){
        const char *icon=pa_string(a,"icon");if(icon&&!asset_exists(root,icon)){rc=error_json(out,409,"icone de conquista ausente");goto done;}
    }
    if(!pa_catalog_load(root,c->id,old)){
        if(cJSON_Compare(c->json,old->json,1)){*out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"status","unchanged");rc=200;goto done;}
        if(c->version<old->version){
            for(int i=0;i<c->count;i++){
                int j=achievement_index(old,c->achievement[i]);
                if(j<0||c->target[i]!=old->target[j]||c->completion[i]!=old->completion[j]){
                    rc=error_json(out,409,"catalogo antigo incompativel");goto done;
                }
            }
            *out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"status","newer_catalog_active");
            cJSON_AddNumberToObject(*out,"catalog_version",old->version);rc=200;goto done;
        }
        if(c->version<=old->version){rc=error_json(out,409,"aumente catalog_version para alterar o catalogo");goto done;}
        for(int i=0;i<old->count;i++){
            int j=achievement_index(c,old->achievement[i]);
            if(j<0||c->target[j]!=old->target[i]||c->completion[j]!=old->completion[i]){
                rc=error_json(out,409,"ids, metas e regras existentes exigem migracao explicita");goto done;
            }
        }
    }else{
        char path[1200];struct stat st;snprintf(path,sizeof(path),"%s/catalogs/%s.json",root,c->id);
        if(!stat(path,&st)){rc=error_json(out,503,"catalogo existente ilegivel; preservado");goto done;}
    }
    char path[1200];snprintf(path,sizeof(path),"%s/catalogs/%s.json",root,c->id);
    char *canonical=cJSON_PrintUnformatted(c->json);
    if(!canonical||pa_atomic(path,canonical,strlen(canonical))){free(canonical);rc=error_json(out,503,"falha ao persistir catalogo");goto done;}
    free(canonical);*out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"status","registered");cJSON_AddStringToObject(*out,"game_id",c->id);
    cJSON_AddNumberToObject(*out,"catalog_version",c->version);pa_log("catalog registered game=%s version=%d",c->id,c->version);rc=201;
done:
    pa_catalog_free(c);pa_catalog_free(old);free(c);free(old);return rc;
}
typedef struct {char id[65],hash[65];} PA_Seen;
typedef struct {
    int progress[PA_MAX_ACH],unlocked[PA_MAX_ACH];
    double at[PA_MAX_ACH];
    PA_Seen seen[PA_MAX_EVENTS];
    int count,torn;
    size_t good;
} PA_State;
static cJSON *normalize_event(cJSON *j,PA_Catalog *c,int *index){
    const char *id=pa_string(j,"event_id"),*game=pa_string(j,"game_id"),*user=pa_string(j,"user_id");
    const char *ach=pa_string(j,"achievement_id"),*type=pa_string(j,"type");int value=0;
    *index=achievement_index(c,ach);
    if(!pa_id(id)||!game||strcmp(game,c->id)||!pa_user(user)||*index<0||c->completion[*index]||!type||
       (strcmp(type,"unlock")&&strcmp(type,"progress")))return NULL;
    if(!strcmp(type,"unlock"))value=c->target[*index];
    else if(pa_integer(j,"value",0,1000000000,&value))return NULL;
    cJSON *v=cJSON_CreateObject();cJSON_AddStringToObject(v,"event_id",id);cJSON_AddStringToObject(v,"game_id",game);
    cJSON_AddStringToObject(v,"user_id",user);cJSON_AddStringToObject(v,"achievement_id",ach);
    cJSON_AddStringToObject(v,"type",type);cJSON_AddNumberToObject(v,"value",value);return v;
}
static int apply_record(PA_Catalog *c,PA_State *s,cJSON *record,const char *user){
    int index;const char *hash=pa_string(record,"body_sha256"),*uid=pa_string(record,"user_id");
    cJSON *normalized=normalize_event(record,c,&index),*at=cJSON_GetObjectItemCaseSensitive(record,"received_at");
    cJSON *awards=cJSON_GetObjectItemCaseSensitive(record,"awards");
    if(!normalized||!pa_digest(hash)||!uid||strcmp(uid,user)||!cJSON_IsNumber(at)||at->valuedouble<0||
       !cJSON_IsArray(awards)||s->count>=PA_MAX_EVENTS){cJSON_Delete(normalized);return -1;}
    char *text=cJSON_PrintUnformatted(normalized),computed[65];if(!text){cJSON_Delete(normalized);return -1;}
    pa_hash(text,strlen(text),computed);free(text);
    if(strcmp(hash,computed)){cJSON_Delete(normalized);return -1;}
    const char *id=pa_string(normalized,"event_id");for(int i=0;i<s->count;i++)if(!strcmp(s->seen[i].id,id)){cJSON_Delete(normalized);return -1;}
    strcpy(s->seen[s->count].id,id);strcpy(s->seen[s->count++].hash,hash);
    int value=cJSON_GetObjectItemCaseSensitive(normalized,"value")->valueint;
    if(value>c->target[index])value=c->target[index];
    if(value>s->progress[index])s->progress[index]=value;
    if(s->progress[index]>=c->target[index]&&!s->unlocked[index]){s->unlocked[index]=1;s->at[index]=at->valuedouble;}
    cJSON *a=NULL;cJSON_ArrayForEach(a,awards){
        int k=cJSON_IsString(a)?achievement_index(c,a->valuestring):-1;
        if(k<0||!c->completion[k]){cJSON_Delete(normalized);return -1;}
        s->progress[k]=1;if(!s->unlocked[k]){s->unlocked[k]=1;s->at[k]=at->valuedouble;}
    }
    cJSON_Delete(normalized);return 0;
}
static uint32_t little32(const unsigned char *b){return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static void write32(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(8*i));}
static int state_load(const char *path,PA_Catalog *c,const char *user,PA_State *s){
    struct stat st;memset(s,0,sizeof(*s));
    if(stat(path,&st))return errno==ENOENT?0:-1;
    size_t n;unsigned char *b=pa_read(path,8u*1024u*1024u,&n);if(!b)return -1;
    size_t pos=0;int rc=0;
    while(pos<n){
        if(n-pos<8){s->torn=1;break;}
        uint32_t len=little32(b+pos),crc=little32(b+pos+4);
        if(len<2||len>4096){rc=-1;break;}
        if(n-pos-8<len){s->torn=1;break;}
        if(pa_crc(b+pos+8,len)!=crc){rc=-1;break;}
        cJSON *record=pa_json(b+pos+8,len);
        if(!record||apply_record(c,s,record,user)){cJSON_Delete(record);rc=-1;break;}
        cJSON_Delete(record);pos+=8+len;s->good=pos;
    }
    free(b);return rc;
}
int pa_event_commit(const char *root,const void *blob,size_t n,cJSON **out){
    cJSON *request=pa_json(blob,n),*normal=NULL,*record=NULL,*awards=NULL;PA_Catalog *c=calloc(1,sizeof(*c));PA_State *s=calloc(1,sizeof(*s));
    int rc=400,index;char *canonical=NULL,*serialized=NULL;char path[1200],folder[1200],hash[65];
    if(!c||!s){rc=error_json(out,503,"sem memoria");goto done;}
    const char *game=pa_string(request,"game_id"),*user=pa_string(request,"user_id");
    if(!pa_game_id(game)||!pa_user(user)){rc=error_json(out,400,"game_id ou user_id invalido");goto done;}
    if(pa_catalog_load(root,game,c)){rc=error_json(out,404,"registre o catalogo primeiro");goto done;}
    normal=normalize_event(request,c,&index);if(!normal){rc=error_json(out,400,"evento invalido; conclusao e calculada pelo backend");goto done;}
    canonical=cJSON_PrintUnformatted(normal);if(!canonical){rc=error_json(out,503,"sem memoria");goto done;}pa_hash(canonical,strlen(canonical),hash);
    snprintf(path,sizeof(path),"%s/users/%s/%s.journal",root,user,game);
    if(state_load(path,c,user,s)){rc=error_json(out,503,"journal ilegivel ou corrompido; preservado");goto done;}
    const char *event=pa_string(normal,"event_id");
    for(int i=0;i<s->count;i++)if(!strcmp(event,s->seen[i].id)){
        if(strcmp(hash,s->seen[i].hash)){rc=error_json(out,409,"event_id reutilizado com outro conteudo");goto done;}
        if(pa_sync_parent(path)){rc=error_json(out,503,"falha ao sincronizar diretorio do journal");goto done;}
        *out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"status","duplicate");cJSON_AddStringToObject(*out,"event_id",event);cJSON_AddArrayToObject(*out,"new_unlocks");rc=200;goto done;
    }
    if(s->count>=PA_MAX_EVENTS){rc=error_json(out,507,"limite de eventos desta versao atingido");goto done;}
    record=cJSON_Duplicate(normal,1);cJSON_AddStringToObject(record,"body_sha256",hash);
    double now=(double)time(NULL);if(now<0)now=0;cJSON_AddNumberToObject(record,"received_at",now);awards=cJSON_AddArrayToObject(record,"awards");
    int value=cJSON_GetObjectItemCaseSensitive(normal,"value")->valueint;
    if(value>c->target[index])value=c->target[index];
    int all=1;for(int i=0;i<c->count;i++)if(!c->completion[i]&&!s->unlocked[i]&&!(i==index&&value>=c->target[i]))all=0;
    for(int i=0;i<c->count;i++)if(all&&c->completion[i]&&!s->unlocked[i])cJSON_AddItemToArray(awards,cJSON_CreateString(c->achievement[i]));
    serialized=cJSON_PrintUnformatted(record);if(!serialized||strlen(serialized)>4096){rc=error_json(out,503,"falha ao serializar evento");goto done;}
    snprintf(folder,sizeof(folder),"%s/users/%s",root,user);if(pa_mkdirs(folder)){rc=error_json(out,503,"falha ao criar diretorio do usuario");goto done;}
    int fd=open(path,O_RDWR|O_CREAT|PA_BINARY,0600);if(fd<0){rc=error_json(out,503,"falha ao abrir journal");goto done;}
    if(s->torn&&(pa_truncate(fd,s->good)||pa_sync(fd))){close(fd);rc=error_json(out,503,"falha ao recuperar escrita interrompida");goto done;}
    if((uint64_t)lseek(fd,0,SEEK_END)!=s->good){close(fd);rc=error_json(out,503,"journal alterado durante a transacao");goto done;}
    unsigned char header[8];size_t len=strlen(serialized);write32(header,(uint32_t)len);write32(header+4,pa_crc(serialized,len));
    if(pa_write_all(fd,header,sizeof(header))||pa_write_all(fd,serialized,len)||pa_sync(fd)){
        (void)pa_truncate(fd,s->good);(void)pa_sync(fd);close(fd);rc=error_json(out,503,"falha ao persistir evento");goto done;
    }
    close(fd);if(pa_sync_parent(path)){rc=error_json(out,503,"falha ao sincronizar diretorio do journal");goto done;}
    *out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"status","accepted");cJSON_AddStringToObject(*out,"event_id",event);
    cJSON *list=cJSON_AddArrayToObject(*out,"new_unlocks");
    if(!s->unlocked[index]&&value>=c->target[index])cJSON_AddItemToArray(list,cJSON_CreateString(c->achievement[index]));
    for(cJSON *a=awards->child;a;a=a->next)cJSON_AddItemToArray(list,cJSON_Duplicate(a,1));
    pa_log("event committed game=%s user=%s event=%s unlocks=%d",game,user,event,cJSON_GetArraySize(list));rc=201;
done:
    free(canonical);free(serialized);cJSON_Delete(request);cJSON_Delete(normal);cJSON_Delete(record);
    if(c){pa_catalog_free(c);free(c);}free(s);return rc;
}
int pa_state_get(const char *root,const char *user,const char *game,cJSON **out){
    if(!pa_game_id(game)||!pa_user(user))return error_json(out,400,"identificador invalido");
    PA_Catalog *c=calloc(1,sizeof(*c));PA_State *s=calloc(1,sizeof(*s));int rc;
    if(!c||!s){free(c);free(s);return error_json(out,503,"sem memoria");}
    if(pa_catalog_load(root,game,c)){rc=error_json(out,404,"jogo desconhecido");goto done;}
    char path[1200];snprintf(path,sizeof(path),"%s/users/%s/%s.journal",root,user,game);
    if(state_load(path,c,user,s)){rc=error_json(out,503,"journal ilegivel ou corrompido; preservado");goto done;}
    *out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"game_id",game);cJSON_AddStringToObject(*out,"user_id",user);
    cJSON_AddNumberToObject(*out,"catalog_version",c->version);cJSON_AddNumberToObject(*out,"event_count",s->count);
    cJSON_AddBoolToObject(*out,"incomplete_tail",s->torn);cJSON *list=cJSON_AddArrayToObject(*out,"achievements");
    for(int i=0;i<c->count;i++){
        cJSON *a=cJSON_CreateObject();cJSON_AddStringToObject(a,"id",c->achievement[i]);cJSON_AddNumberToObject(a,"progress",s->progress[i]);
        cJSON_AddNumberToObject(a,"target",c->target[i]);cJSON_AddBoolToObject(a,"unlocked",s->unlocked[i]);cJSON_AddNumberToObject(a,"unlocked_at",s->at[i]);cJSON_AddItemToArray(list,a);
    }rc=200;
done:
    pa_catalog_free(c);free(c);free(s);return rc;
}
cJSON *pa_games_get(const char *root){
    cJSON *out=cJSON_CreateObject(),*list=cJSON_AddArrayToObject(out,"games");char path[1200];snprintf(path,sizeof(path),"%s/catalogs",root);
    DIR *d=opendir(path);if(!d)return out;struct dirent *entry;
    while((entry=readdir(d))){size_t n=strlen(entry->d_name);if(n<6||n>69||strcmp(entry->d_name+n-5,".json"))continue;
        char id[65];memcpy(id,entry->d_name,n-5);id[n-5]=0;PA_Catalog *c=calloc(1,sizeof(*c));if(!c)break;
        if(!pa_catalog_load(root,id,c)){cJSON_AddItemToArray(list,cJSON_Duplicate(c->json,1));pa_catalog_free(c);}free(c);
    }closedir(d);return out;
}
cJSON *pa_users_get(const char *root){
    cJSON *out=cJSON_CreateObject(),*list=cJSON_AddArrayToObject(out,"users");char path[1200];snprintf(path,sizeof(path),"%s/users",root);
    DIR *d=opendir(path);if(!d)return out;struct dirent *entry;
    while((entry=readdir(d)))if(pa_user(entry->d_name))cJSON_AddItemToArray(list,cJSON_CreateString(entry->d_name));
    closedir(d);return out;
}
static uint32_t big32(const unsigned char *p){return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3];}
static int png_valid(const unsigned char *b,size_t n){
    if(n<45||memcmp(b,"\x89PNG\r\n\x1a\n",8)||big32(b+8)!=13||memcmp(b+12,"IHDR",4)||
       !big32(b+16)||!big32(b+20)||big32(b+16)>1024||big32(b+20)>1024)return 0;
    size_t pos=8;int data=0;
    while(n-pos>=12){
        uint32_t len=big32(b+pos);if((size_t)len>n-pos-12)return 0;
        if(pa_crc(b+pos+4,(size_t)len+4)!=big32(b+pos+8+len))return 0;
        if(!memcmp(b+pos+4,"IDAT",4))data=1;
        if(!memcmp(b+pos+4,"IEND",4))return !len&&data&&pos+12==n;
        pos+=12+len;
    }return 0;
}
int pa_asset_put(const char *root,const char *id,const void *blob,size_t n,cJSON **out){
    char hash[65];pa_hash(blob,n,hash);
    if(!pa_digest(id)||strcmp(id,hash)||n>PA_MAX_BODY||!png_valid(blob,n))return error_json(out,400,"PNG ou SHA-256 invalido");
    char path[1200];snprintf(path,sizeof(path),"%s/assets/%s.png",root,id);
    if(pa_atomic(path,blob,n))return error_json(out,503,"falha ao persistir imagem");
    *out=cJSON_CreateObject();cJSON_AddStringToObject(*out,"sha256",id);return 201;
}
