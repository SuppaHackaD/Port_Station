/* SPDX-License-Identifier: MIT
 * Port Station: virtual desktop policy, independent of the PS5 scanout buffers.
 */
#ifndef PORT_STATION_DISPLAY_POLICY_H
#define PORT_STATION_DISPLAY_POLICY_H
#include <stdint.h>
enum { STATION_FRAME_MAX_WIDTH=3840, STATION_FRAME_MAX_HEIGHT=2160 };
typedef struct StationDesktop { uint32_t width, height; int detected; } StationDesktop;
static inline StationDesktop station_desktop_resolve_bounded(int status, uint32_t width, uint32_t height,
                                                            uint32_t max_width, uint32_t max_height)
{
    StationDesktop result={1920,1080,0};
    if(status!=0 || width<320 || height<200 || width>16384 || height>16384)return result;
    /* Bound future output modes without changing aspect ratio. */
    if(width>max_width) {
        height=(uint32_t)((uint64_t)height*max_width/width);
        width=max_width;
    }
    if(height>max_height) {
        width=(uint32_t)((uint64_t)width*max_height/height);
        height=max_height;
    }
    if(width<320 || height<200)return result;
    result.width=width;result.height=height;result.detected=1;return result;
}
static inline StationDesktop station_desktop_resolve(int status, uint32_t width, uint32_t height)
{
    return station_desktop_resolve_bounded(status,width,height,STATION_FRAME_MAX_WIDTH,STATION_FRAME_MAX_HEIGHT);
}
static inline StationDesktop station_desktop_resolve_software(int status, uint32_t width, uint32_t height)
{
    /* NW.js/Canvas uses CPU-backed surfaces. TCOAAL boots at 720p/1080p on
     * console, while a 4K virtual desktop exhausts its mapping budget. */
    return station_desktop_resolve_bounded(status,width,height,1920,1080);
}
#endif
