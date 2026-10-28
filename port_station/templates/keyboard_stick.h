/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef STATION_KEYBOARD_STICK_H
#define STATION_KEYBOARD_STICK_H
#include <stdint.h>

/* Merge stick directions with physical buttons before generating edges. This
 * keeps a key held when either source still holds it, and releases all keys
 * when the pad disconnects or system UI intercepts it. */
typedef struct { uint32_t stick, held; } StationKeyboardStick;
static uint32_t station_keyboard_axis(uint8_t raw, uint32_t old,
                                      uint32_t negative, uint32_t positive)
{
    int delta = (int)raw - 128;
    if (delta <= -48 || ((old & negative) && delta < -32)) return negative;
    if (delta >= 48 || ((old & positive) && delta > 32)) return positive;
    return 0;
}
static void station_keyboard_stick(StationKeyboardStick *state, int connected,
                                   uint8_t x, uint8_t y, uint32_t buttons,
                                   uint32_t *pressed, uint32_t *released)
{
    uint32_t stick = connected ?
        station_keyboard_axis(x, state->stick, 0x80u, 0x20u) |
        station_keyboard_axis(y, state->stick, 0x10u, 0x40u) : 0;
    uint32_t held = connected ? buttons | stick : 0;
    *pressed = held & ~state->held;
    *released = state->held & ~held;
    state->held = held;
    state->stick = stick;
}
#endif
