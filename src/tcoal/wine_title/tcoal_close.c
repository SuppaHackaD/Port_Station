#include "tcoal_close.h"
int tcoal_close_update(TcoalClose *s, uint64_t now, int valid, uint32_t buttons) {
    if (!s) return 0;
    if (!valid || (buttons & TCOAL_CLOSE_MASK) != TCOAL_CLOSE_MASK) {
        s->active = s->fired = 0; return 0;
    }
    if (!s->active || now < s->since) { s->since = now; s->active = 1; s->fired = 0; return 0; }
    if (!s->fired && now - s->since >= 1000000000ull) { s->fired = 1; return 1; }
    return 0;
}
