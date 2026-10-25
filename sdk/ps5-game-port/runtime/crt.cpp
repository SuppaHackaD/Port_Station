/*
 * ps5-native-app-boilerplate - Native application startup.
 * Copyright (C) 2026 BlackBearReloaded
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Sets the IEEE floating-point state, initializes the platform runtime, runs
 * static constructors and main, and hands normal process termination back to
 * the platform runtime.
 */

#include <cstddef>
#include <cstdint>
#include "boot_trace.h"
#ifdef GP_APP_HEAP
#include "heap.h"
#endif

using Destructor = void (*)();
using Initializer = void (*)();

extern "C"
{
    void _init_env(void *process_parameters);
    void ps5_fp_ieee(void);
    int atexit(Destructor callback);
    [[noreturn]] void exit(int status);
    int application_main(int argc, char **argv, char **envp) __asm__("main");

    extern Initializer __preinit_array_start[] __attribute__((weak));
    extern Initializer __preinit_array_end[] __attribute__((weak));
    extern Initializer __init_array_start[] __attribute__((weak));
    extern Initializer __init_array_end[] __attribute__((weak));
    extern Initializer __fini_array_start[] __attribute__((weak));
    extern Initializer __fini_array_end[] __attribute__((weak));
}

namespace
{
void run_forward(Initializer *first, Initializer *last) noexcept
{
    if (first == nullptr || last == nullptr)
        return;
    while (first != last)
        (*first++)();
}

void run_reverse(Initializer *first, Initializer *last) noexcept
{
    if (first == nullptr || last == nullptr)
        return;
    while (last != first)
        (*--last)();
}
} // namespace

extern "C" __attribute__((weak)) void catchReturnFromMain(int status)
{
    (void)status;
}

extern "C" void _init()
{
    ps5_fp_ieee();
    gp_boot_trace("[GP SDK] _init: before initializer arrays\n");
    run_forward(__preinit_array_start, __preinit_array_end);
    run_forward(__init_array_start, __init_array_end);
    gp_boot_trace("[GP SDK] _init: initializer arrays finished\n");
}

extern "C" void _fini()
{
    run_reverse(__fini_array_start, __fini_array_end);
}

extern "C" [[noreturn]] __attribute__((visibility("default"))) void
_start(void *process_parameters, Destructor loader_teardown)
{
    gp_boot_trace("[GP SDK] _start entered\n");
    const int argc = *static_cast<const int *>(process_parameters);
    auto *parameters = static_cast<std::uint8_t *>(process_parameters);
    auto **argv = reinterpret_cast<char **>(parameters + sizeof(std::uint64_t));

    /* The console starts a title with flush-to-zero and denormals-are-zero
     * on; the code linked here expects the IEEE state (PS5 platform, fp.h). */
    ps5_fp_ieee();
    gp_boot_trace("[GP SDK] before _init_env\n");
    _init_env(process_parameters);
    gp_boot_trace("[GP SDK] after _init_env\n");
#ifdef GP_APP_HEAP
    if (!gp_heap_prepare()) {
        gp_boot_trace("[GP SDK] application heap unavailable; closing through shell\n");
        catchReturnFromMain(90);
    }
    gp_heap_snapshot("before-constructors");
#endif
    if (loader_teardown != nullptr)
        (void)atexit(loader_teardown);
    (void)atexit(_fini);
    _init();
    gp_boot_trace("[GP SDK] before main\n");
    const int status = application_main(argc, argv, nullptr);
    gp_boot_trace("[GP SDK] main returned; closing through shell\n");
    catchReturnFromMain(status);
    exit(status);
}

