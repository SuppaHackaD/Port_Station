/*
 * SPDX-License-Identifier: GPL-3.0-or-later
 * PS5 process-lifetime mspace heap, derived from the public allocator integration
 * in ProsperoEden third_party/app_heap.c, Copyright (C) 2026 BlackBearReloaded.
 * Reference revision: a26ba788222465ec7fb94dc813958fc749734e07.
 * Adaptations: explicit initialization after _init_env, sleeping serialization,
 * checked calloc/alignment, owned realloc(p,0), aligned_alloc and startup tracing.
 */
#include "heap.h"
#include "boot_trace.h"
#include <errno.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdio.h>
#ifndef GP_HEAP_HOST_TEST
#include <sys/mman.h>
#else
void *gp_heap_test_map(size_t);
void gp_heap_test_unmap(void *, size_t);
#endif
#ifndef GP_HEAP_SIZE_BYTES
#define GP_HEAP_SIZE_BYTES (128u * 1024u * 1024u)
#endif

void *__real_malloc(size_t);
void *__real_calloc(size_t, size_t);
void *__real_realloc(void *, size_t);
void __real_free(void *);
int __real_posix_memalign(void **, size_t, size_t);
void *__real_aligned_alloc(size_t, size_t);
size_t __real_malloc_usable_size(const void *);
void *sceLibcMspaceCreate(const char *, void *, size_t, unsigned);
void *sceLibcMspaceMalloc(void *, size_t);
void *sceLibcMspaceCalloc(void *, size_t, size_t);
void *sceLibcMspaceRealloc(void *, void *, size_t);
void sceLibcMspaceFree(void *, void *);
int sceLibcMspacePosixMemalign(void *, void **, size_t, size_t);
size_t sceLibcMspaceMallocUsableSize(const void *);
int sceKernelUsleep(unsigned int);

static atomic_int heap_state;
static atomic_flag heap_lock = ATOMIC_FLAG_INIT;
static void *heap_base, *heap_mspace;
static atomic_size_t live_bytes, peak_bytes, blocks, failures, fallbacks;
static void lock_heap(void) {
    while (atomic_flag_test_and_set_explicit(&heap_lock, memory_order_acquire))
        sceKernelUsleep(1000); /* Do not spin on a preempted allocating thread. */
}
static void unlock_heap(void) { atomic_flag_clear_explicit(&heap_lock, memory_order_release); }
static int ready(void) { return atomic_load_explicit(&heap_state, memory_order_acquire) == 2; }
static int owns(const void *address) {
    if (!address || !ready()) return 0;
    uintptr_t value = (uintptr_t)address, base = (uintptr_t)heap_base;
    return value >= base && value-base < (size_t)GP_HEAP_SIZE_BYTES;
}
static void resize_stats(size_t before, size_t after) {
    size_t live = after >= before
        ? atomic_fetch_add_explicit(&live_bytes, after-before, memory_order_relaxed)+after-before
        : atomic_fetch_sub_explicit(&live_bytes, before-after, memory_order_relaxed)-(before-after);
    size_t peak = atomic_load_explicit(&peak_bytes, memory_order_relaxed);
    while (live > peak && !atomic_compare_exchange_weak_explicit(&peak_bytes, &peak, live,
                                                               memory_order_relaxed, memory_order_relaxed)) {}
}
static void *record(void *address, int nonzero) {
    if (address) {
        resize_stats(0, sceLibcMspaceMallocUsableSize(address));
        atomic_fetch_add_explicit(&blocks, 1, memory_order_relaxed);
    } else if (nonzero) atomic_fetch_add_explicit(&failures, 1, memory_order_relaxed);
    return address;
}
static void failed(void) { errno=ENOMEM; atomic_fetch_add_explicit(&failures, 1, memory_order_relaxed); }
static void fallback(void) { atomic_fetch_add_explicit(&fallbacks, 1, memory_order_relaxed); }
int gp_heap_prepare(void) {
    if (ready()) return 1;
    int expected=0;
    if (!atomic_compare_exchange_strong_explicit(&heap_state, &expected, 1,
                                                 memory_order_acq_rel, memory_order_acquire)) return 0;
    gp_boot_trace("[GP heap] before anonymous RW mapping\n");
#ifndef GP_HEAP_HOST_TEST
    void *base=mmap(NULL, GP_HEAP_SIZE_BYTES, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANON, -1, 0);
    if (base == MAP_FAILED) base=NULL;
#else
    void *base=gp_heap_test_map(GP_HEAP_SIZE_BYTES);
#endif
    if (!base) { atomic_store_explicit(&heap_state, -1, memory_order_release); gp_boot_trace("[GP heap] mapping failed\n"); return 0; }
    gp_boot_trace("[GP heap] mapped; before sceLibcMspaceCreate\n");
    void *mspace=sceLibcMspaceCreate("GamePort", base, GP_HEAP_SIZE_BYTES, 0);
    if (!mspace) {
#ifndef GP_HEAP_HOST_TEST
        munmap(base, GP_HEAP_SIZE_BYTES);
#else
        gp_heap_test_unmap(base, GP_HEAP_SIZE_BYTES);
#endif
        atomic_store_explicit(&heap_state, -1, memory_order_release);
        gp_boot_trace("[GP heap] mspace creation failed\n"); return 0;
    }
    heap_base=base; heap_mspace=mspace;
    atomic_store_explicit(&heap_state, 2, memory_order_release);
    gp_boot_trace("[GP heap] mspace ready\n"); return 1;
}
void *__wrap_malloc(size_t size) {
    if (!ready()) { fallback(); return __real_malloc(size); }
    if (size > (size_t)GP_HEAP_SIZE_BYTES) { failed(); return NULL; }
    lock_heap(); void *p=record(sceLibcMspaceMalloc(heap_mspace, size), size!=0); unlock_heap(); return p;
}
void *__wrap_calloc(size_t count, size_t size) {
    if (size && count > SIZE_MAX/size) { failed(); return NULL; }
    if (!ready()) { fallback(); return __real_calloc(count, size); }
    if (count*size > (size_t)GP_HEAP_SIZE_BYTES) { failed(); return NULL; }
    lock_heap(); void *p=record(sceLibcMspaceCalloc(heap_mspace, count, size), count!=0&&size!=0); unlock_heap(); return p;
}
void __wrap_free(void *address) {
    if (!address) return;
    if (!owns(address)) { fallback(); __real_free(address); return; }
    lock_heap(); resize_stats(sceLibcMspaceMallocUsableSize(address), 0);
    atomic_fetch_sub_explicit(&blocks, 1, memory_order_relaxed);
    sceLibcMspaceFree(heap_mspace, address); unlock_heap();
}
void *__wrap_realloc(void *address, size_t size) {
    if (!address) return __wrap_malloc(size);
    if (!owns(address)) { fallback(); return __real_realloc(address, size); }
    if (!size) { __wrap_free(address); return NULL; }
    if (size > (size_t)GP_HEAP_SIZE_BYTES) { failed(); return NULL; }
    lock_heap(); size_t before=sceLibcMspaceMallocUsableSize(address);
    void *p=sceLibcMspaceRealloc(heap_mspace, address, size);
    if (p) resize_stats(before, sceLibcMspaceMallocUsableSize(p)); else failed();
    unlock_heap(); return p;
}
int __wrap_posix_memalign(void **address, size_t alignment, size_t size) {
    if (!address || alignment < sizeof(void *) || (alignment & (alignment-1))) return EINVAL;
    if (!ready()) { fallback(); return __real_posix_memalign(address, alignment, size); }
    if (size > (size_t)GP_HEAP_SIZE_BYTES) { failed(); return ENOMEM; }
    lock_heap(); int result=sceLibcMspacePosixMemalign(heap_mspace, address, alignment, size);
    if (!result) record(*address, size!=0); else if (result==ENOMEM) failed();
    unlock_heap(); return result;
}
void *__wrap_aligned_alloc(size_t alignment, size_t size) {
    if (!alignment || (alignment & (alignment-1)) || size%alignment) { errno=EINVAL; return NULL; }
    if (!ready()) { fallback(); return __real_aligned_alloc(alignment, size); }
    void *address=NULL;
    int result=__wrap_posix_memalign(&address, alignment < sizeof(void *) ? sizeof(void *) : alignment, size);
    if (result) errno=result;
    return result ? NULL : address;
}
size_t __wrap_malloc_usable_size(const void *address) {
    if (!address) return 0;
    if (!owns(address)) { fallback(); return __real_malloc_usable_size(address); }
    lock_heap(); size_t result=sceLibcMspaceMallocUsableSize(address); unlock_heap(); return result;
}
void gp_heap_get_stats(gp_heap_stats *s) {
    if (!s) return;
    s->state=atomic_load_explicit(&heap_state, memory_order_acquire);
    s->capacity=s->state==2 ? GP_HEAP_SIZE_BYTES : 0;
    s->live=atomic_load_explicit(&live_bytes, memory_order_relaxed);
    s->peak=atomic_load_explicit(&peak_bytes, memory_order_relaxed);
    s->blocks=atomic_load_explicit(&blocks, memory_order_relaxed);
    s->failures=atomic_load_explicit(&failures, memory_order_relaxed);
    s->fallbacks=atomic_load_explicit(&fallbacks, memory_order_relaxed);
}
void gp_heap_snapshot(const char *phase) {
    gp_heap_stats s; gp_heap_get_stats(&s); char text[320];
    snprintf(text, sizeof(text), "[GP heap] phase=%s state=%d capacity=%zu live=%zu peak=%zu blocks=%zu failures=%zu fallbacks=%zu\n",
             phase, s.state, s.capacity, s.live, s.peak, s.blocks, s.failures, s.fallbacks);
    gp_boot_trace(text);
}
