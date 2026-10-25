#include "pa_common.h"
#include "vendor/sha256.h"
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#include <dirent.h>
#ifdef _WIN32
#include <windows.h>
#include <io.h>
#include <direct.h>
#define open _open
#define close _close
#define read _read
#define write _write
#define PA_BINARY _O_BINARY
#else
#include <sys/file.h>
#include <sys/time.h>
#define PA_BINARY 0
#endif
static int log_fd=-1;
void pa_names_free(PA_Names *n){free(n->name);memset(n,0,sizeof(*n));}
static int names_add(PA_Names *n,const char *name,size_t len){
    if(!len||len>=80||name[0]=='.')return 0;
    if(n->count==n->capacity){
        size_t cap=n->capacity?n->capacity*2:16;if(cap>8192){errno=EOVERFLOW;return -1;}
        void *p=realloc(n->name,cap*sizeof(*n->name));if(!p){errno=ENOMEM;return -1;}n->name=p;n->capacity=cap;
    }
    memcpy(n->name[n->count],name,len);n->name[n->count++][len]=0;return 0;
}
int pa_names_dirents(const unsigned char *b,size_t size,PA_Names *n){
    size_t pos=0;
    while(pos<size){
        if(size-pos<8){errno=EINVAL;return -1;}
        unsigned length=(unsigned)b[pos+4]|(unsigned)b[pos+5]<<8;
        unsigned type=b[pos+6],namelen=b[pos+7];
        if(length<8||length>size-pos||8u+namelen>=length||b[pos+8+namelen]!=0||memchr(b+pos+8,0,namelen)){errno=EINVAL;return -1;}
        if((type==0||type==8)&&names_add(n,(const char*)b+pos+8,namelen))return -1;
        pos+=length;
    }
    return 0;
}
int pa_names_get(const char *path,PA_Names *n){
    memset(n,0,sizeof(*n));errno=0;DIR *d=opendir(path);
    if(d){
        struct dirent *e;int failed=0;
        for(;;){
            errno=0;e=readdir(d);
            if(!e){failed=errno!=0;break;}
            if(names_add(n,e->d_name,strlen(e->d_name))){failed=1;break;}
        }
        int saved=errno;closedir(d);
        if(!failed){n->method=1;return 0;}errno=saved;
    }
#ifdef PA_PS5
    /* PS5 filesystems can require a 64 KiB directory block. Use the same
     * FreeBSD record layout and block size as the tested Wine library scan. */
    pa_names_free(n);n->method=2;
    int fd=open(path,O_RDONLY|O_DIRECTORY);if(fd<0)return -1;
    unsigned char *buffer=malloc(64*1024);if(!buffer){close(fd);errno=ENOMEM;return -1;}
    extern int getdents(int,char *,int);
    int got,rc=0;
    for(;;){
        got=getdents(fd,(char*)buffer,64*1024);if(got<0&&errno==EINTR)continue;
        if(got<0){rc=-1;break;}if(!got)break;
        if(pa_names_dirents(buffer,(size_t)got,n)){rc=-1;break;}
    }
    int saved=errno;free(buffer);close(fd);errno=saved;return rc;
#else
    return -1;
#endif
}
void pa_hash(const void *b,size_t n,char out[65]){
    SHA256_CTX c;unsigned char hash[32];static const char h[]="0123456789abcdef";
    sha256_init(&c);sha256_update(&c,b,n);sha256_final(&c,hash);
    for(unsigned i=0;i<32;i++){out[i*2]=h[hash[i]>>4];out[i*2+1]=h[hash[i]&15];}out[64]=0;
}
uint32_t pa_crc(const void *b,size_t n){
    const unsigned char *p=b;uint32_t c=~0u;
    for(size_t i=0;i<n;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}
    return ~c;
}
int pa_id(const char *s){
    if(!s||!s[0]||strlen(s)>64)return 0;
    for(size_t i=0;s[i];i++)if(!((s[i]>='a'&&s[i]<='z')||(s[i]>='A'&&s[i]<='Z')||(s[i]>='0'&&s[i]<='9')||(i&&(s[i]=='.'||s[i]=='_'||s[i]=='-'))))return 0;
    return strstr(s,"..")==NULL;
}
int pa_game_id(const char *s){if(!pa_id(s))return 0;for(size_t i=0;s[i];i++)if(s[i]>='A'&&s[i]<='Z')return 0;return 1;}
int pa_user(const char *s){if(!s||strlen(s)!=8)return 0;for(unsigned i=0;i<8;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;return 1;}
int pa_digest(const char *s){if(!s||strlen(s)!=64)return 0;for(unsigned i=0;i<64;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;return 1;}
int pa_mkdirs(const char *path){
    char b[1024];if(!path||strlen(path)>=sizeof(b))return -1;strcpy(b,path);
    for(char *p=b+1;;p++){
        if(*p=='/'||!*p){char last=*p;*p=0;
#ifdef _WIN32
            int r=_mkdir(b);
#else
            int r=mkdir(b,0700);
#endif
            if(r&&errno!=EEXIST)return -1;
#ifndef _WIN32
            if(!r&&pa_sync_parent(b))return -1;
#endif
            *p=last;if(!last)break;
        }
    }return 0;
}
int pa_write_all(int fd,const void *blob,size_t n){
    const unsigned char *p=blob;
    while(n){long r=(long)write(fd,p,(unsigned)n);if(r<0&&errno==EINTR)continue;if(r<=0)return -1;p+=r;n-=(size_t)r;}return 0;
}
int pa_sync(int fd){
#ifdef _WIN32
    return _commit(fd);
#else
    return fsync(fd);
#endif
}
int pa_sync_parent(const char *path){
#ifdef _WIN32
    (void)path;return 0; /* MoveFileEx WRITE_THROUGH is used for atomic files. */
#else
    char parent[1024];if(strlen(path)>=sizeof(parent))return -1;strcpy(parent,path);
    char *slash=strrchr(parent,'/');if(!slash)return -1;if(slash==parent)slash[1]=0;else *slash=0;
    int fd=open(parent,O_RDONLY);if(fd<0)return -1;int rc=fsync(fd);close(fd);return rc;
#endif
}
int pa_truncate(int fd,size_t n){
#ifdef _WIN32
    return _chsize_s(fd,n)?-1:0;
#else
    return ftruncate(fd,(off_t)n);
#endif
}
unsigned char *pa_read(const char *p,size_t max,size_t *n){
    struct stat st;*n=0;if(stat(p,&st)||st.st_size<0||(uint64_t)st.st_size>max)return NULL;
    int fd=open(p,O_RDONLY|PA_BINARY);if(fd<0)return NULL;
    unsigned char *b=malloc((size_t)st.st_size+1);if(!b){close(fd);return NULL;}
    size_t wanted=(size_t)st.st_size;
    while(*n<wanted){long r=(long)read(fd,b+*n,(unsigned)(wanted-*n));if(r<0&&errno==EINTR)continue;if(r<=0){free(b);close(fd);return NULL;}*n+=(size_t)r;}
    close(fd);b[*n]=0;return b;
}
int pa_atomic(const char *path,const void *data,size_t n){
    char temp[1100];static unsigned seq;snprintf(temp,sizeof(temp),"%s.tmp.%llu.%u",path,(unsigned long long)pa_millis(),++seq);
    int fd=open(temp,O_WRONLY|O_CREAT|O_EXCL|PA_BINARY,0600);if(fd<0)return -1;
    int r=pa_write_all(fd,data,n);if(!r)r=pa_sync(fd);if(close(fd)&&!r)r=-1;
    if(r){remove(temp);return -1;}
#ifdef _WIN32
    if(!MoveFileExA(temp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)){remove(temp);return -1;}
#else
    if(rename(temp,path)){remove(temp);return -1;}
    if(pa_sync_parent(path))return -1;
#endif
    return 0;
}
int pa_lock_root(const char *root){
    char p[1024];snprintf(p,sizeof(p),"%s/.service.lock",root);int fd=open(p,O_RDWR|O_CREAT|PA_BINARY,0600);if(fd<0)return -1;
#ifdef _WIN32
    OVERLAPPED o={0};if(!LockFileEx((HANDLE)_get_osfhandle(fd),LOCKFILE_EXCLUSIVE_LOCK|LOCKFILE_FAIL_IMMEDIATELY,0,1,0,&o)){close(fd);return -1;}
#else
    if(flock(fd,LOCK_EX|LOCK_NB)){close(fd);return -1;}
#endif
    return fd;
}
uint64_t pa_millis(void){
#ifdef _WIN32
    return (uint64_t)GetTickCount64();
#else
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
#endif
}
static int json_keys(cJSON *j,unsigned depth){
    if(depth>32)return 0;
    if(cJSON_IsObject(j))for(cJSON *a=j->child;a;a=a->next){if(!a->string)return 0;for(cJSON *b=a->next;b;b=b->next)if(b->string&&!strcmp(a->string,b->string))return 0;}
    for(cJSON *a=j->child;a;a=a->next)if(!json_keys(a,depth+1))return 0;
    return 1;
}
cJSON *pa_json(const void *blob,size_t n){
    if(!blob||!n||memchr(blob,0,n))return NULL;
    /* Embedded NULs in decoded JSON strings cannot be represented by C strings. */
    const unsigned char *s=blob;for(size_t i=0;i+5<n;i++)if(s[i]=='\\'&&s[i+1]=='u'&&!memcmp(s+i+2,"0000",4))return NULL;
    for(size_t i=0;i<n;i++){
        unsigned char a=s[i];if(a<0x80)continue;unsigned count;uint32_t value,min;
        if(a>=0xc2&&a<=0xdf){count=1;value=a&31;min=0x80;}
        else if(a>=0xe0&&a<=0xef){count=2;value=a&15;min=0x800;}
        else if(a>=0xf0&&a<=0xf4){count=3;value=a&7;min=0x10000;}
        else return NULL;
        if(i+count>=n)return NULL;
        for(unsigned j=0;j<count;j++){unsigned char next=s[++i];if((next&0xc0)!=0x80)return NULL;value=(value<<6)|(next&63);}
        if(value<min||value>0x10ffff||(value>=0xd800&&value<=0xdfff))return NULL;
    }
    char *b=malloc(n+1);if(!b)return NULL;memcpy(b,blob,n);b[n]=0;
    const char *end=NULL;cJSON *j=cJSON_ParseWithLengthOpts(b,n+1,&end,1);free(b);
    if(j&&!json_keys(j,0)){cJSON_Delete(j);j=NULL;}return j;
}
const char *pa_string(const cJSON *j,const char *key){cJSON *v=cJSON_GetObjectItemCaseSensitive(j,key);return cJSON_IsString(v)?v->valuestring:NULL;}
int pa_integer(const cJSON *j,const char *key,int min,int max,int *out){
    cJSON *v=cJSON_GetObjectItemCaseSensitive(j,key);if(!cJSON_IsNumber(v)||v->valuedouble<min||v->valuedouble>max||v->valuedouble!=(double)v->valueint)return -1;*out=v->valueint;return 0;
}
void pa_log_open(const char *root){char p[1024];snprintf(p,sizeof(p),"%s/service.log",root);log_fd=open(p,O_WRONLY|O_CREAT|O_APPEND|PA_BINARY,0600);}
void pa_log(const char *fmt,...){
    char line[1024];int len=snprintf(line,sizeof(line),"%lld ",(long long)time(NULL));va_list a;va_start(a,fmt);
    int r=vsnprintf(line+len,sizeof(line)-(size_t)len,fmt,a);va_end(a);if(r<0)return;
    size_t n=strlen(line);if(n+1<sizeof(line))line[n++]='\n';if(log_fd>=0)(void)pa_write_all(log_fd,line,n);
    printf("%.*s",(int)n,line);
}
int pa_net_init(void){
#ifdef _WIN32
    WSADATA w;return WSAStartup(MAKEWORD(2,2),&w)?-1:0;
#else
    return 0;
#endif
}
void pa_net_timeout(pa_socket s,unsigned ms){
#ifdef SO_NOSIGPIPE
    int one=1;setsockopt(s,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof(one));
#endif
#ifdef _WIN32
    DWORD v=ms;setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,(const char*)&v,sizeof(v));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,(const char*)&v,sizeof(v));
#else
    struct timeval v={ms/1000,(ms%1000)*1000};setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&v,sizeof(v));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,&v,sizeof(v));
#endif
}
pa_socket pa_connect(unsigned port){
    pa_socket s=socket(AF_INET,SOCK_STREAM,0);if(s==PA_INVALID)return PA_INVALID;
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons((uint16_t)port);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
#ifdef PA_PS5
    a.sin_len=sizeof(a);
#endif
#ifdef _WIN32
    u_long one=1;ioctlsocket(s,FIONBIO,&one);
#else
    int old=fcntl(s,F_GETFL,0);fcntl(s,F_SETFL,old|O_NONBLOCK);
#endif
    int rc=connect(s,(struct sockaddr*)&a,sizeof(a));
    if(rc){
        fd_set w;FD_ZERO(&w);FD_SET(s,&w);struct timeval t={2,0};
        if(select((int)s+1,NULL,&w,NULL,&t)<=0){pa_socket_close(s);return PA_INVALID;}
        int error=0;
#ifdef _WIN32
        int n=sizeof(error);if(getsockopt(s,SOL_SOCKET,SO_ERROR,(char*)&error,&n))error=1;
#else
        socklen_t n=sizeof(error);if(getsockopt(s,SOL_SOCKET,SO_ERROR,&error,&n))error=1;
#endif
        if(error){pa_socket_close(s);return PA_INVALID;}
    }
#ifdef _WIN32
    one=0;ioctlsocket(s,FIONBIO,&one);
#else
    fcntl(s,F_SETFL,old);
#endif
    pa_net_timeout(s,2000);return s;
}
int pa_send_all(pa_socket s,const void *blob,size_t n){
    const char *p=blob;while(n){
#ifdef MSG_NOSIGNAL
        int r=(int)send(s,p,(int)n,MSG_NOSIGNAL);
#else
        int r=(int)send(s,p,(int)n,0);
#endif
        if(r<=0)return -1;p+=r;n-=(size_t)r;
    }return 0;
}
