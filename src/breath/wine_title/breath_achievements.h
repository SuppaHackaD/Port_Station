#ifndef BREATH_ACHIEVEMENTS_H
#define BREATH_ACHIEVEMENTS_H
#include <stdint.h>
typedef void (*BreathAchievementMessage)(const char *);
typedef struct BreathAchievements {
    char events[1024], ledger[1024];
    uint32_t user, seen;
    long offset;
    int active, discarding, handshake;
    BreathAchievementMessage log, notify;
} BreathAchievements;
int breath_achievements_open(BreathAchievements *,const char *root,const char *prefix,
                             int32_t user,BreathAchievementMessage log,BreathAchievementMessage notify);
int breath_achievements_poll(BreathAchievements *);
int breath_achievements_ps5_open(const char *root,const char *prefix,int32_t user);
void breath_achievements_ps5_tick(uint64_t now);
#endif
