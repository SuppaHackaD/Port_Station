#include "pa_file_bridge.h"
#include "tcoal_pa_assets.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned notices;
static void unlocked(void *userdata,const char *game,const char *user,const char *id){
    (void)userdata;(void)game;(void)user;if(id&&*id)notices++;
}
int main(int argc,char **argv){
    if(argc!=5)return 9;PA_SDK sdk;PA_FileBridge bridge;
    int rc=pa_file_bridge_open(&bridge,&sdk,argv[2],"tcoal",argv[3],tcoal_ids,sizeof(tcoal_ids)/sizeof(tcoal_ids[0]));
    if(!rc)rc=pa_sdk_init(&sdk,argv[1],"tcoal",argv[3],(unsigned)strtoul(argv[4],NULL,10));
    for(size_t i=0;!rc&&i<sizeof(tcoal_assets)/sizeof(tcoal_assets[0]);i++){char hash[65];rc=pa_sdk_asset(&sdk,tcoal_assets[i].data,tcoal_assets[i].size,hash);}
    if(!rc)rc=pa_sdk_catalog(&sdk,tcoal_catalog,sizeof(tcoal_catalog)-1);
    printf("open=%d\n",rc);fflush(stdout);if(rc)return 1;
    char line[32];while(fgets(line,sizeof(line),stdin)){
        if(!strcmp(line,"exit\n"))break;
        int polled=pa_file_bridge_poll(&bridge),sent=!strcmp(line,"pump\n")?pa_sdk_pump_with_callback(&sdk,unlocked,NULL):0;
        printf("poll=%d sent=%d pending=%d handshake=%d notices=%u\n",polled,sent,pa_sdk_pending(&sdk),bridge.handshake,notices);fflush(stdout);
    }return 0;
}
