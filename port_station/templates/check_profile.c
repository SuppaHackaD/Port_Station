#include "pw_game_profile.h"
#include <stdio.h>
int main(int argc,char **argv){
    unsigned char bytes[8193];PwGameProfile profile;
    if(argc!=2)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 3;
    size_t n=fread(bytes,1,sizeof(bytes),f);int error=ferror(f);fclose(f);
    if(error||n>8192)return 4;
    int rc=pw_game_profile_parse(bytes,n,&profile);
    if(rc){fprintf(stderr,"Wine profile rejected by upstream parser: rc=%d\n",rc);return 5;}
    printf("Wine profile accepted: %s\n",profile.app.id);return 0;
}
