/* Refresh only the fingerprint-verified files listed by the build preparer. */
static int compat_matches(const char *name,uint64_t expected,uint32_t wanted,int full){
 FILE *in=fopen(name,"rb");if(!in)return 0;
 if(!full){int ok=!fseek(in,0,SEEK_END)&&(uint64_t)ftell(in)==expected;fclose(in);return ok;}
 unsigned char b[65536];uint64_t total=0;uint32_t crc=0xffffffffu;size_t n;
 while((n=fread(b,1,sizeof(b),in))){total+=n;if(total>expected)break;crc=crc32(crc,b,n);}
 int ok=!(ferror)(in)&&total==expected&&(crc^0xffffffffu)==wanted;fclose(in);return ok;
}
static int sync_compat(const char *root){
 const struct{const char *name;uint64_t size;uint32_t crc;} files[]={@COMPAT_ROWS@};
 const char *roots[]={STUDIO_PACKAGE_ROOT,"/mnt/sandbox/@TITLE_ID@_000/app0"};
 const char *expected=@COMPAT_STAMP@;char mark[1024],stamp[65]={0},source[1024],dest[1024],temp[1060];
 snprintf(mark,sizeof(mark),"%s/.port-station-love-ready",root);FILE *in=fopen(mark,"rb");
 int ready=in&&fread(stamp,1,64,in)==64&&!memcmp(stamp,expected,64);if(in)fclose(in);
 for(unsigned i=0;ready&&i<sizeof(files)/sizeof(files[0]);i++){
  snprintf(dest,sizeof(dest),"%s/%s",root,files[i].name);ready=compat_matches(dest,files[i].size,files[i].crc,0);
 }
 if(ready)return 0;
 static unsigned char bytes[65536];
 for(unsigned i=0;i<sizeof(files)/sizeof(files[0]);i++){
  snprintf(dest,sizeof(dest),"%s/%s",root,files[i].name);
  if(compat_matches(dest,files[i].size,files[i].crc,1))continue;
  in=NULL;for(unsigned j=0;j<2&&!in;j++){snprintf(source,sizeof(source),"%s/seed/%s",roots[j],files[i].name);in=fopen(source,"rb");}
  if(!in)return -40;
  snprintf(temp,sizeof(temp),"%s.port-station-compat",dest);
  if(folders(dest)){fclose(in);return -41;}FILE *out=fopen(temp,"wb");if(!out){fclose(in);return -42;}
  uint64_t total=0;uint32_t crc=0xffffffffu;size_t n;int ok=1;
  while((n=fread(bytes,1,sizeof(bytes),in))){total+=n;if(total>files[i].size){ok=0;break;}crc=crc32(crc,bytes,n);if(fwrite(bytes,1,n,out)!=n){ok=0;break;}}
  int bad=(ferror)(in),ci=fclose(in),co=fclose(out);
  if(!ok||bad||ci||co||total!=files[i].size||(crc^0xffffffffu)!=files[i].crc){remove(temp);return -43;}
  if(profile_replace(temp,dest))return -44;
 }
 snprintf(temp,sizeof(temp),"%s.new",mark);FILE *out=fopen(temp,"wb");if(!out)return -45;
 int ok=fwrite(expected,1,64,out)==64;int closed=fclose(out);
 if(!ok||closed||profile_replace(temp,mark))return -46;
 return 0;
}
