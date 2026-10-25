/* Early logging uses exported kernel services without libc/heap initialization. */
#include <stddef.h>
#include "boot_trace.h"
int sceKernelDebugOutText(int channel, const char *message);
int sceKernelOpen(const char *path, int flags, int mode);
long sceKernelWrite(int fd, const void *data, size_t length);
int sceKernelFsync(int fd);
static int descriptor = -1;
static int attempted;
#ifndef GP_BOOT_LOG
#define GP_BOOT_LOG "/data/ps5-game-port-sdk.log"
#endif
void gp_boot_trace(const char *message) {
    sceKernelDebugOutText(0, message);
    if (!attempted) {
        attempted = 1;
        descriptor = sceKernelOpen(GP_BOOT_LOG, 0x209, 0666);
    }
    if (descriptor < 0) return;
    size_t length = 0;
    while (message[length]) ++length;
    while (length) {
        long written = sceKernelWrite(descriptor, message, length);
        if (written <= 0 || (size_t)written > length) break;
        message += written;
        length -= (size_t)written;
    }
    sceKernelFsync(descriptor);
}
