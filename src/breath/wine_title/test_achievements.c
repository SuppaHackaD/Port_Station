#include "breath_achievements.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void log_line(const char *text){fprintf(stderr,"log:%s\n",text);}
static void notify(const char *text){printf("notify:%s\n",text);}
int main(int argc,char **argv){
    if(argc!=4)return 2;BreathAchievements a;
    int rc=breath_achievements_open(&a,argv[1],argv[2],(int32_t)strtol(argv[3],NULL,10),log_line,notify);
    printf("open=%d seen=%x\n",rc,a.seen);fflush(stdout);if(rc)return 1;
    char command[32];while(fgets(command,sizeof(command),stdin)){
        if(!strcmp(command,"exit\n"))break;
        rc=breath_achievements_poll(&a);printf("poll=%d seen=%x offset=%ld handshake=%d\n",rc,a.seen,a.offset,a.handshake);fflush(stdout);
    }return 0;
}
