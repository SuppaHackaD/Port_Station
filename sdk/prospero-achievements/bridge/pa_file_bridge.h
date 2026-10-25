#ifndef PA_FILE_BRIDGE_H
#define PA_FILE_BRIDGE_H
#include "prospero_achievements.h"
typedef struct {
    PA_SDK *sdk;
    char events[1024],game[65],user[9];
    const char *const *ids;
    unsigned count;
    unsigned char queued[256];
    long offset;
    int handshake,discarding;
} PA_FileBridge;
int pa_file_bridge_open(PA_FileBridge *,PA_SDK *,const char *prefix,const char *game,const char *user,const char *const *ids,unsigned count);
/* Worker only: poll after successful SDK initialization/catalog preparation. */
int pa_file_bridge_poll(PA_FileBridge *);
#endif
