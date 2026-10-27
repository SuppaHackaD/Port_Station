/* Only generated, owned integration files. Stream to a temporary file and check
 * size/CRC before replace. User saves and other assets are not synchronized. */
static int sync_managed(const char *root){
 const struct{const char *name;uint64_t size;uint32_t crc;} files[]={@MANAGED_ROWS@};
 const char *roots[]={STUDIO_PACKAGE_ROOT,"/mnt/sandbox/@TITLE_ID@_000/app0"};
 char source[1024],dest[1024],temp[1060];static unsigned char bytes[65536];
 for(unsigned i=0;i<sizeof(files)/sizeof(files[0]);i++){
  FILE *in=NULL;
  for(unsigned j=0;j<2&&!in;j++){snprintf(source,sizeof(source),"%s/seed/%s",roots[j],files[i].name);in=fopen(source,"rb");}
  if(!in)return -30;
  snprintf(dest,sizeof(dest),"%s/%s",root,files[i].name);snprintf(temp,sizeof(temp),"%s.port-station-managed",dest);
  if(folders(dest)){fclose(in);return -31;}
  FILE *out=fopen(temp,"wb");if(!out){fclose(in);return -32;}
  uint64_t total=0;uint32_t crc=0xffffffffu;size_t n;int ok=1;
  while((n=fread(bytes,1,sizeof(bytes),in))){
   total+=n;if(total>files[i].size){ok=0;break;}
   crc=crc32(crc,bytes,n);if(fwrite(bytes,1,n,out)!=n){ok=0;break;}
  }
  int read_error=(ferror)(in),closed_in=fclose(in),closed_out=fclose(out);
  if(!ok||read_error||closed_in||closed_out||total!=files[i].size||(crc^0xffffffffu)!=files[i].crc){remove(temp);return -33;}
  if(profile_replace(temp,dest))return -34;
 }
 return 0;
}
