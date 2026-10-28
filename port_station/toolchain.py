"""Invoke the pinned compiler and linker directly, preserving each path argument."""
from pathlib import Path
from .project import WORKSPACE


def compile_payload(sources, output, run, *, includes=(), defines=()):
    """Build a public-SDK C payload without its shell-based linker adapter."""
    root = WORKSPACE
    sdk = root / 'tools/sdk-v0.44/ps5-payload-sdk'
    llvm = root / 'tools/llvm-18.1.8/bin'
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    common = [llvm / 'clang.exe', '-target', 'x86_64-sie-ps5',
              '-isysroot', sdk, '-isystem', sdk / 'target/include',
              '-fno-stack-protector', '-fno-plt', '-femulated-tls',
              '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror']
    common += ['-I' + str(p) for p in includes]
    common += ['-D' + value for value in defines]
    objects = []
    for number, source in enumerate(sources):
        obj = output.parent / f'payload-{number}.o'
        run([*common, '-c', source, '-o', obj])
        objects.append(obj)
    # Clang's PS5 driver selects prospero-lld even with --ld-path. That SDK
    # adapter joins argv and calls system(), losing quoting around spaced paths.
    # Keep the SDK's same ELF settings, but pass argv directly to LLVM lld.
    run([llvm / 'ld.lld.exe', '-m', 'elf_x86_64', '-pie', '--eh-frame-hdr',
         '-z', 'max-page-size=0x4000', '-T', sdk / 'ldscripts/elf_x86_64.x',
         '-L', sdk / 'target/lib', '-L', sdk / 'target/user/homebrew/lib',
         '-o', output, *objects, '-lc', '-lkernel_web',
         sdk / 'target/lib/crt1.o', '-lSceLibcInternal', '-lSceNet'])
