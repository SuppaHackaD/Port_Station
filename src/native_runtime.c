#include <stddef.h>
#include <stdio.h>

int sceSystemServiceLoadExec(const char *, const char *const *);
int sceKernelUsleep(unsigned int);

void ps5_fp_ieee(void) {
    const unsigned int mxcsr = 0x1f80;
    __asm__ volatile("fninit\n\tldmxcsr %0" : : "m"(mxcsr));
}

/* Native titles close through the shell; returning from _start is invalid.
 * Follows the exported-service exit flow documented by PS5_VulkanTemplate. */
__attribute__((noreturn)) void catchReturnFromMain(int status) {
    (void)status;
    fflush(NULL);
    sceSystemServiceLoadExec("exit", NULL);
    for (;;) sceKernelUsleep(100000);
}
