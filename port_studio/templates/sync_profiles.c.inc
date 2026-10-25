/* Profiles and the Studio's injected bridge scripts are package-owned.
 * Never replace original game content, fonts, registry or user saves here. */
#ifdef _WIN32
#include <windows.h>
#define profile_replace(a,b) (MoveFileExA(a,b,MOVEFILE_REPLACE_EXISTING)?0:-1)
#else
#define profile_replace(a,b) rename(a,b)
#endif
static int sync_profiles(const char *root){
 const char *names[]={"profiles/@SLUG@.profile","profiles/profiles.lst"@STUDIO_FILES@};
 const char *roots[]={STUDIO_PACKAGE_ROOT,"/mnt/sandbox/@TITLE_ID@_000/app0"};
 char source[1024],dest[1024],temp[1060];static unsigned char bytes[262145];
 for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);i++){
  FILE *in=NULL;
  for(unsigned j=0;j<2&&!in;j++){snprintf(source,sizeof(source),"%s/seed/%s",roots[j],names[i]);in=fopen(source,"rb");}
  if(!in)return -20;
  size_t n=fread(bytes,1,sizeof(bytes),in);int error=(ferror)(in);fclose(in);
  if(error||!n||n>262144)return -21;
  snprintf(dest,sizeof(dest),"%s/%s",root,names[i]);snprintf(temp,sizeof(temp),"%s.port-studio-profile",dest);
  if(folders(dest))return -22;
  FILE *out=fopen(temp,"wb");if(!out)return -23;
  int ok=fwrite(bytes,1,n,out)==n;int closed=fclose(out);
  if(!ok||closed||profile_replace(temp,dest))return -24;
 }
 return 0;
}
