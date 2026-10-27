/* SPDX-License-Identifier: MIT
 * Durable Windows-side publisher for PA_FILE_*_V1, inside the game's Wine prefix.
 * The caller supplies its owned folder and game ID; context binds the user.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

static int valid_id(const char *s,int lower){
 if(!s||!*s||strlen(s)>64||strstr(s,".."))return 0;
 for(unsigned i=0;s[i];i++)if(!((s[i]>='a'&&s[i]<='z')||(!lower&&s[i]>='A'&&s[i]<='Z')||(s[i]>='0'&&s[i]<='9')||(i&&(s[i]=='_'||s[i]=='-'||s[i]=='.'))))return 0;
 return 1;
}
static int context(const char *folder,const char *game,char user[9]){
 if(!folder||!*folder||strlen(folder)>700||!valid_id(game,1))return -1;
 char path[800],text[160]={0},found[65]={0},canonical[160];
 snprintf(path,sizeof(path),"%s/%s-context-v1.txt",folder,game);FILE *in=fopen(path,"rb");if(!in)return -2;
 size_t n=fread(text,1,sizeof(text),in);int error=(ferror)(in);fclose(in);
 if(error||n==sizeof(text)||sscanf(text,"PA_FILE_CONTEXT_V1\t%64s\t%8s",found,user)!=2||strcmp(found,game)||strlen(user)!=8)return -3;
 for(unsigned i=0;i<8;i++)if(!((user[i]>='0'&&user[i]<='9')||(user[i]>='a'&&user[i]<='f')))return -3;
 int size=snprintf(canonical,sizeof(canonical),"PA_FILE_CONTEXT_V1\t%s\t%s\n",game,user);
 return n==(size_t)size&&!memcmp(text,canonical,n)?0:-3;
}
static void trace(const char *folder,const char *game,const char *user,const char *id,int status){
 static int previous=-999;static unsigned count;
 if(!valid_id(game,1)||!folder||strlen(folder)>700)return;
 if(status<0&&status==previous)return;
 if(count++>1024)return;previous=status;
 char path[800];snprintf(path,sizeof(path),"%s/%s-bridge.log",folder,game);
 FILE *out=fopen(path,"ab");if(!out)return;
 fprintf(out,"PA_WIN_EVENTS rc=%d user=%s id=%s\n",status,user?user:"-",id?id:"ready");fclose(out);
}
static int publish(const char *folder,const char *game,const char *id){
 char user[9]={0};int rc=context(folder,game,user);
 if(rc){trace(folder,game,NULL,id,rc);return rc;}
 if(id&&!valid_id(id,0))return -1;
 char path[840],record[512];snprintf(path,sizeof(path),"%s/%s-%s.tsv",folder,game,user);
 int n=snprintf(record,sizeof(record),"\nPA_FILE_BRIDGE_V1\t%s\t%s\n",game,user);
 if(id)n+=snprintf(record+n,sizeof(record)-(size_t)n,"PA_FILE_UNLOCK_V1\t%s\t%s\t%s\n",game,user,id);
 if(n<=0||(size_t)n>=sizeof(record))return -1;
 HANDLE file=CreateFileA(path,GENERIC_WRITE,FILE_SHARE_READ,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
 if(file==INVALID_HANDLE_VALUE){trace(folder,game,user,id,-4);return -4;}
 LARGE_INTEGER end;end.QuadPart=0;
 if(!SetFilePointerEx(file,end,NULL,FILE_END)){CloseHandle(file);trace(folder,game,user,id,-5);return -5;}
 DWORD at=0;rc=0;
 while(at<(DWORD)n){DWORD wrote=0;if(!WriteFile(file,record+at,(DWORD)n-at,&wrote,NULL)||!wrote){rc=-5;break;}at+=wrote;}
 if(!rc&&!FlushFileBuffers(file))rc=-6;
 if(!CloseHandle(file)&&!rc)rc=-7;
 trace(folder,game,user,id,rc);return rc;
}
__declspec(dllexport) int pa_event_ready_v1(const char *folder,const char *game){return publish(folder,game,NULL);}
__declspec(dllexport) int pa_event_unlock_v1(const char *folder,const char *game,const char *id){
 if(!valid_id(id,0))return -1;return publish(folder,game,id);
}
