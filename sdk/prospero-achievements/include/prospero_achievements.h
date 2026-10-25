#ifndef PROSPERO_ACHIEVEMENTS_H
#define PROSPERO_ACHIEVEMENTS_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
#define PA_SDK_API_MAJOR 1
#define PA_SDK_VERSION "0.1.2"
#define PA_SDK_DEFAULT_PORT 38765
/* All disk/network methods run on the port's adapter worker, never its render
 * thread. One worker owns one context and outbox. No game memory is inspected. */
typedef struct {
    char root[800],game_id[65],user_id[9],synced_instance[96],synced_catalog[65];
    unsigned port;
    int last_http_status;
    /* Queue diagnostics; method 1=readdir, 2=PS5 getdents fallback. Recompile
     * clients with the matching static archive when this structure changes. */
    int last_errno,directory_method;
    const char *last_stage;
} PA_SDK;
enum { PA_SDK_OK=0, PA_SDK_OFFLINE=-1, PA_SDK_STORAGE=-2,
       PA_SDK_INVALID=-3, PA_SDK_PROTOCOL=-4, PA_SDK_CONFLICT=-5 };
int pa_sdk_init(PA_SDK *,const char *outbox_root,const char *game_id,const char *user_id,unsigned port);
int pa_sdk_asset(PA_SDK *,const void *png,size_t,char sha256_out[65]);
int pa_sdk_catalog(PA_SDK *,const void *json,size_t);
/* event_id is stable across retransmissions and unique per user/game event. */
int pa_sdk_unlock(PA_SDK *,const char *achievement_id,const char *event_id);
int pa_sdk_progress(PA_SDK *,const char *achievement_id,unsigned value,const char *event_id);
/* Synchronize catalog/assets and send persisted pending events. Returns number
 * acknowledged, or a negative error. Failures leave the outbox on disk. */
int pa_sdk_pump(PA_SDK *);
/* Called synchronously on the adapter worker after a matching accepted ACK.
 * Only newly unlocked IDs are reported, never duplicate/replayed awards.
 * Do not reenter SDK methods from the callback; copy strings if retaining them.
 * A lost response may suppress a notification; the committed unlock is retained. */
typedef void (*PA_UnlockCallback)(void *userdata,const char *game_id,const char *user_id,const char *achievement_id);
int pa_sdk_pump_with_callback(PA_SDK *,PA_UnlockCallback,void *userdata);
int pa_sdk_pending(PA_SDK *);
#ifdef __cplusplus
}
#endif
#endif
