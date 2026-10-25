#include "tcoal_close.h"
#undef NDEBUG
#include <assert.h>
#include <stdio.h>
int main(void) {
    TcoalClose s = {0}; const uint32_t combo = TCOAL_CLOSE_MASK;
    assert(!tcoal_close_update(&s, 0, 1, TCOAL_OPTIONS | 1u));
    assert(!tcoal_close_update(&s, 0, 1, TCOAL_OPTIONS));
    assert(!tcoal_close_update(&s, 0, 1, TCOAL_TOUCHPAD));
    assert(!tcoal_close_update(&s, 100, 1, combo));
    assert(!tcoal_close_update(&s, 999000100, 1, combo));
    assert(tcoal_close_update(&s, 1000000100, 1, combo));
    assert(!tcoal_close_update(&s, 2000000100, 1, combo));
    assert(!tcoal_close_update(&s, 2000000200, 0, combo));
    assert(!tcoal_close_update(&s, 3000000000, 1, combo));
    assert(!tcoal_close_update(&s, 3900000000, 1, TCOAL_OPTIONS));
    assert(!tcoal_close_update(&s, 4000000000, 1, combo));
    assert(!tcoal_close_update(&s, 4500000000, 1, combo));
    assert(tcoal_close_update(&s, 5100000000, 1, combo));
    assert(!tcoal_close_update(&s, 100, 1, combo)); /* clock reset */
    assert(!tcoal_close_update(&s, 0, 1, combo));
    assert(tcoal_close_update(&s, 1000000000, 1, combo));
    puts("Close gesture: timing, release, disconnect, once-only and old-chord checks passed.");
    return 0;
}
