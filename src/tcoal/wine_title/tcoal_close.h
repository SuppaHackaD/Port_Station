#ifndef TCOAL_CLOSE_H
#define TCOAL_CLOSE_H
#include <stdint.h>
typedef struct { uint64_t since; unsigned active, fired; } TcoalClose;
enum { TCOAL_OPTIONS = 0x8u, TCOAL_TOUCHPAD = 0x100000u,
       TCOAL_CLOSE_MASK = TCOAL_OPTIONS | TCOAL_TOUCHPAD };
int tcoal_close_update(TcoalClose *, uint64_t now_ns, int valid, uint32_t buttons);
#endif
