/* Private title bootstrap: immutable package seed -> owned writable Wine prefix. */
#include "breath_bootstrap.h"
#include <errno.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#ifdef _WIN32
#include <direct.h>
#define directory_create(p) _mkdir(p)
#else
#define directory_create(p) mkdir(p,0777)
#endif
#ifndef BREATH_DATA_ROOT
#define BREATH_DATA_ROOT "/data/breath-wine"
#endif
#ifndef BREATH_PACKAGE_ROOT
#define BREATH_PACKAGE_ROOT "/app0"
#endif
#ifndef _WIN32
static void status(const char*text){struct{char reserved[45];char message[3075];}request={0};extern int sceKernelSendNotificationRequest(int,void*,size_t,int);snprintf(request.message,sizeof(request.message),"%s",text);sceKernelSendNotificationRequest(0,&request,sizeof(request),0);}
#else
static void status(const char*text){(void)text;}
#endif
static uint32_t crc32(uint32_t c,const unsigned char*p,size_t n){for(size_t i=0;i<n;i++){c^=p[i];for(int j=0;j<8;j++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return c;}
static int folders(const char*path){char b[1024];if(strlen(path)>=sizeof(b))return -1;strcpy(b,path);for(char*p=b+1;*p;p++)if(*p=='/'){*p=0;if(directory_create(b)&&errno!=EEXIST)return -1;*p='/';}return 0;}
static FILE *progress;
static void record(const char *format,...){if(!progress)return;va_list args;va_start(args,format);vfprintf(progress,format,args);va_end(args);fputc('\n',progress);fflush(progress);}
static int install(const char*root){
 static const char identity[]="Breath-Wine-PPSA99397-v1\n";
 static unsigned char buffer[1024*1024];char mark[1024],name[768],source[1024],dest[1024],temp[1060],line[1024];
 if(strcmp(root,BREATH_DATA_ROOT))return -1;
 snprintf(mark,sizeof(mark),"%s/.breath-ready-v1",root);FILE*f=fopen(mark,"rb");if(f){char value[64]={0};size_t n=fread(value,1,sizeof(value),f);fclose(f);return n==sizeof(identity)-1&&!memcmp(value,identity,n)?0:-2;}
 const char*package=NULL;FILE*manifest=NULL;const char*roots[]={BREATH_PACKAGE_ROOT,"/mnt/sandbox/PPSA99397_000/app0"};for(unsigned i=0;i<2;i++){snprintf(source,sizeof(source),"%s/seed-files.tsv",roots[i]);manifest=fopen(source,"rb");if(manifest){package=roots[i];break;}}if(!manifest)return -3;
 snprintf(dest,sizeof(dest),"%s/.breath-install-owner",root);if(folders(dest)){fclose(manifest);return -4;}
 f=fopen(dest,"rb");if(f){char value[64]={0};size_t n=fread(value,1,sizeof(value),f);fclose(f);if(n!=sizeof(identity)-1||memcmp(value,identity,n)){fclose(manifest);return -5;}}
 else{struct stat st;snprintf(temp,sizeof(temp),"%s/prefixes/breath",root);if(!stat(temp,&st)){fclose(manifest);return -6;}f=fopen(dest,"wb");if(!f){fclose(manifest);return -7;}int ok=fwrite(identity,1,sizeof(identity)-1,f)==sizeof(identity)-1;int closed=fclose(f);if(!ok||closed){fclose(manifest);return -8;}}
 snprintf(dest,sizeof(dest),"%s/bootstrap.log",root);progress=fopen(dest,"ab");record("bootstrap v2 package=%s root=%s",package,root);
 status("Breath: preparando os dados do jogo. Aguarde a primeira inicializacao.");unsigned count=0;int result=0;
 while(fgets(line,sizeof(line),manifest)){
  unsigned long long expected;unsigned wanted;if(sscanf(line,"%llu\t%x\t%767[^\n]",&expected,&wanted,name)!=3||strstr(name,"..")||name[0]=='/'||strchr(name,'\\')||strchr(name,'\r')){record("invalid manifest line after %u files",count);result=-9;break;}
  snprintf(source,sizeof(source),"%s/seed/%s",package,name);snprintf(dest,sizeof(dest),"%s/%s",root,name);snprintf(temp,sizeof(temp),"%s.breath-copy",dest);
  if(folders(dest)){record("mkdir failed path=%s errno=%d",dest,errno);result=-10;break;}FILE*in=fopen(source,"rb");int input_errno=errno;FILE*out=fopen(temp,"wb");int output_errno=errno;if(!in||!out){record("open failed path=%s input=%d input_errno=%d output=%d output_errno=%d",name,in!=NULL,input_errno,out!=NULL,output_errno);if(in)fclose(in);if(out)fclose(out);result=-11;break;}
  uint64_t total=0;uint32_t crc=0xffffffffu;size_t n;int ok=1;while((n=fread(buffer,1,sizeof(buffer),in))){crc=crc32(crc,buffer,n);total+=n;if(fwrite(buffer,1,n,out)!=n){ok=0;break;}}
  /* The SDK's C stdio macros inspect a FreeBSD FILE layout. Native titles
   * use SceLibcInternal streams: call its exported function, never that macro. */
  int read_error=(ferror)(in);int read_errno=errno;int input_close=fclose(in);int output_close=fclose(out);int close_errno=errno;
  ok=ok&&!read_error&&!input_close&&!output_close&&total==expected&&(crc^0xffffffffu)==wanted;
  if(!ok){record("copy failed path=%s bytes=%llu expected=%llu crc=%08x expected_crc=%08x read_error=%d read_errno=%d input_close=%d output_close=%d close_errno=%d",name,(unsigned long long)total,expected,crc^0xffffffffu,wanted,read_error,read_errno,input_close,output_close,close_errno);result=-12;break;}
  if(rename(temp,dest)){record("rename failed path=%s errno=%d",name,errno);result=-12;break;}
  if(++count==1||count%100==0)record("copied=%u last=%s",count,name);
 }
 if((ferror)(manifest)){record("manifest read failed errno=%d",errno);result=-13;}fclose(manifest);if(result)return result;
 const char*userdirs[]={"AppData/Local/Temp","AppData/LocalLow","AppData/Roaming","Documents","Saved Games","Desktop"};for(unsigned i=0;i<sizeof(userdirs)/sizeof(userdirs[0]);i++){snprintf(dest,sizeof(dest),"%s/prefixes/breath/drive_c/users/prospero/%s/.folder",root,userdirs[i]);if(folders(dest))return -16;}
 f=fopen(mark,"wb");if(!f)return -14;int ok=fwrite(identity,1,sizeof(identity)-1,f)==sizeof(identity)-1;int closed=fclose(f);return ok&&!closed?0:-15;
}
int breath_bootstrap(const char*root){progress=NULL;int result=install(root);record("bootstrap result=%d errno=%d",result,errno);if(progress){fclose(progress);progress=NULL;}if(result){char text[128];snprintf(text,sizeof(text),"Breath: falha na preparacao (%d). Log: /data/breath-wine/bootstrap.log",result);status(text);}return result;}
