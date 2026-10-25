#ifndef PA_MODEL_H
#define PA_MODEL_H
#include "pa_common.h"
typedef struct {
    cJSON *json;
    char id[65];
    int version,count;
    char achievement[PA_MAX_ACH][65];
    int target[PA_MAX_ACH],completion[PA_MAX_ACH];
} PA_Catalog;
int pa_catalog_parse(const void *,size_t,PA_Catalog *,char error[160]);
void pa_catalog_free(PA_Catalog *);
int pa_catalog_load(const char *,const char *,PA_Catalog *);
int pa_catalog_register(const char *,const void *,size_t,cJSON **);
int pa_event_commit(const char *,const void *,size_t,cJSON **);
int pa_state_get(const char *,const char *,const char *,cJSON **);
cJSON *pa_games_get(const char *);
cJSON *pa_users_get(const char *);
int pa_asset_put(const char *,const char *,const void *,size_t,cJSON **);
#endif
