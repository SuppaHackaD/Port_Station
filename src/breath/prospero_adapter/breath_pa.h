#ifndef BREATH_PA_H
#define BREATH_PA_H
#include "prospero_achievements.h"
#include <stdint.h>
typedef struct { const unsigned char *data; size_t size; const char *hash; } BreathPAAsset;
typedef struct {
    PA_SDK sdk;
    uint32_t queued;
    int ready;
} BreathPA;
int breath_pa_open(BreathPA *,const char *root,uint32_t user,unsigned port);
int breath_pa_capture(BreathPA *,uint32_t earned_mask);
int breath_pa_pump(BreathPA *);
int breath_pa_pump_with_callback(BreathPA *,PA_UnlockCallback,void *userdata);
const char *breath_pa_title(const char *achievement_id);
int breath_pa_notification(char *message,size_t capacity,const char *achievement_id);
void breath_pa_close(void);
#endif
