/* SPDX-License-Identifier: MIT
 * Port Station: virtual desktop policy, independent of the PS5 scanout buffers.
 */
#ifndef PORT_STATION_DISPLAY_POLICY_H
#define PORT_STATION_DISPLAY_POLICY_H
#include <stdint.h>
enum { STATION_FRAME_MAX_WIDTH=3840, STATION_FRAME_MAX_HEIGHT=2160 };
typedef struct StationDesktop { uint32_t width, height; int detected; } StationDesktop;
static inline StationDesktop station_desktop_resolve(int status, uint32_t width, uint32_t height)
{
    StationDesktop result={1920,1080,0};
    if(status!=0 || width<320 || height<200 || width>16384 || height>16384)return result;
    /* Bound future output modes without changing aspect ratio. */
    if(width>STATION_FRAME_MAX_WIDTH) {
        height=(uint32_t)((uint64_t)height*STATION_FRAME_MAX_WIDTH/width);
        width=STATION_FRAME_MAX_WIDTH;
    }
    if(height>STATION_FRAME_MAX_HEIGHT) {
        width=(uint32_t)((uint64_t)width*STATION_FRAME_MAX_HEIGHT/height);
        height=STATION_FRAME_MAX_HEIGHT;
    }
    if(width<320 || height<200)return result;
    result.width=width;result.height=height;result.detected=1;return result;
}
#endif
