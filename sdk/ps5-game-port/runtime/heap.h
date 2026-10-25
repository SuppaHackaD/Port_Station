/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef GP_NATIVE_HEAP_H
#define GP_NATIVE_HEAP_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct gp_heap_stats {
    int state; /* 0 unprepared, 1 preparing, 2 ready, -1 failed */
    size_t capacity, live, peak, blocks, failures, fallbacks;
} gp_heap_stats;
/* Call after _init_env and before constructors/threads. Mapping lives until process exit. */
int gp_heap_prepare(void);
void gp_heap_get_stats(gp_heap_stats *result);
void gp_heap_snapshot(const char *phase);
/* --wrap entrypoints use the original allocator before preparation and for
 * foreign pointers. Owned realloc(p,0) explicitly frees and returns NULL. */
#ifdef __cplusplus
}
#endif
#endif
