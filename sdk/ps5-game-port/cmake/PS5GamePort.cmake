include_guard(GLOBAL)
get_filename_component(GP_NATIVE_SDK "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
get_filename_component(GP_WORKSPACE "${GP_NATIVE_SDK}/../.." ABSOLUTE)
set(GP_NATIVE_SOURCE "${GP_WORKSPACE}/tools/PS5_Vulkan/tooling/native")
set(GP_NATIVE_TOOL "${GP_WORKSPACE}/build/host/ps5-native-tool.exe")
set(GP_LIBC "${GP_WORKSPACE}/build/host/libc.prx")
set(GP_PYTHON "" CACHE FILEPATH "Python 3 host executable")
if(NOT EXISTS "${GP_PYTHON}")
    message(FATAL_ERROR "Set GP_PYTHON to a host Python executable")
endif()
foreach(path IN ITEMS "${GP_NATIVE_TOOL}" "${GP_LIBC}" "${GP_NATIVE_SOURCE}/ps5-pie.ld")
    if(NOT EXISTS "${path}")
        message(FATAL_ERROR "Missing native dependency: ${path}; run scripts/build-native-tools.ps1")
    endif()
endforeach()
file(SHA256 "${GP_LIBC}" libc_digest)
if(NOT libc_digest STREQUAL "e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036")
    message(FATAL_ERROR "Generated libc.prx differs from the validated public-source runtime")
endif()

function(ps5_game_port_title target)
    cmake_parse_arguments(TITLE "" "TITLE_ID;TITLE_NAME;ASSET_DIRECTORY;CONTENT_NOTE;HEAP_MIB" "SOURCES;LIBRARIES;SHADERS;ASSETS;LINK_DEPENDS;STUBS" ${ARGN})
    if(NOT TITLE_TITLE_ID MATCHES "^PPSA[0-9][0-9][0-9][0-9][0-9]$")
        message(FATAL_ERROR "TITLE_ID must be PPSA plus five digits")
    endif()
    set(work "${CMAKE_CURRENT_BINARY_DIR}/${target}-work")
    set(dist "${CMAKE_CURRENT_BINARY_DIR}/dist/${TITLE_TITLE_ID}")
    file(MAKE_DIRECTORY "${work}")
    file(WRITE "${work}/local.map" "{ local: *; };\n")
    set(shader_outputs "")
    set(asset_commands "")
    set(asset_inputs "")
    if(TITLE_ASSET_DIRECTORY)
        if(TITLE_ASSETS)
            message(FATAL_ERROR "Choose ASSETS or ASSET_DIRECTORY")
        endif()
        get_filename_component(asset_root "${TITLE_ASSET_DIRECTORY}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
        if(NOT IS_DIRECTORY "${asset_root}")
            message(FATAL_ERROR "Asset directory does not exist: ${asset_root}")
        endif()
        file(GLOB_RECURSE asset_inputs CONFIGURE_DEPENDS "${asset_root}/*")
        list(APPEND asset_commands COMMAND "${CMAKE_COMMAND}" -E copy_directory "${asset_root}" "${dist}/assets")
    endif()
    if(TITLE_ASSETS)
        list(APPEND asset_commands COMMAND "${CMAKE_COMMAND}" -E make_directory "${dist}/assets")
        set(asset_names "")
        foreach(asset IN LISTS TITLE_ASSETS)
            get_filename_component(asset_path "${asset}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
            get_filename_component(asset_name "${asset_path}" NAME)
            if(NOT EXISTS "${asset_path}" OR IS_DIRECTORY "${asset_path}" OR asset_name IN_LIST asset_names)
                message(FATAL_ERROR "Missing, non-file, or duplicate asset: ${asset}")
            endif()
            list(APPEND asset_names "${asset_name}")
            list(APPEND asset_inputs "${asset_path}")
            list(APPEND asset_commands COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${asset_path}" "${dist}/assets/${asset_name}")
        endforeach()
    endif()
    set(content_arguments "")
    if(TITLE_CONTENT_NOTE)
        list(APPEND content_arguments --content-note "${TITLE_CONTENT_NOTE}")
    endif()
    foreach(shader IN LISTS TITLE_SHADERS)
        set(glslang "${GP_WORKSPACE}/tools/glslang/16.6.0-source-built/bin/glslang.exe")
        if(NOT EXISTS "${glslang}")
            message(FATAL_ERROR "Missing public GLSL compiler: ${glslang}")
        endif()
        get_filename_component(shader_path "${shader}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
        get_filename_component(shader_name "${shader}" NAME)
        set(shader_output "${dist}/shaders/${shader_name}.spv")
        add_custom_command(OUTPUT "${shader_output}"
            COMMAND "${CMAKE_COMMAND}" -E make_directory "${dist}/shaders"
            COMMAND "${glslang}" -V --target-env vulkan1.1 "${shader_path}" -o "${shader_output}"
            DEPENDS "${shader_path}" "${glslang}" VERBATIM)
        list(APPEND shader_outputs "${shader_output}")
    endforeach()
    set(heap_sources "")
    set(heap_link_options "")
    if(TITLE_HEAP_MIB)
        if(NOT TITLE_HEAP_MIB MATCHES "^[0-9]+$" OR TITLE_HEAP_MIB LESS 16 OR TITLE_HEAP_MIB GREATER 256)
            message(FATAL_ERROR "HEAP_MIB must be an integer from 16 to 256")
        endif()
        math(EXPR heap_bytes "${TITLE_HEAP_MIB} * 1024 * 1024")
        list(APPEND content_arguments --heap-mib "${TITLE_HEAP_MIB}")
        list(APPEND heap_sources "${GP_NATIVE_SDK}/runtime/heap.c")
        foreach(symbol IN ITEMS malloc calloc realloc free posix_memalign aligned_alloc malloc_usable_size)
            list(APPEND heap_link_options "--wrap=${symbol}")
        endforeach()
    endif()
    add_library(${target}_objects OBJECT ${TITLE_SOURCES} ${heap_sources}
        "${GP_NATIVE_SDK}/runtime/crt.cpp" "${GP_NATIVE_SDK}/runtime/trace.c"
        "${GP_WORKSPACE}/src/native_runtime.c")
    target_compile_features(${target}_objects PRIVATE cxx_std_20)
    target_compile_options(${target}_objects PRIVATE -Wall -Wextra -Werror -fno-builtin)
    target_include_directories(${target}_objects PRIVATE "${GP_NATIVE_SDK}/runtime")
    target_include_directories(${target}_objects PRIVATE "${GP_NATIVE_SDK}/include")
    if(TITLE_HEAP_MIB)
        target_compile_definitions(${target}_objects PRIVATE GP_APP_HEAP=1 GP_HEAP_SIZE_BYTES=${heap_bytes})
    endif()
    set(extra_stub_arguments "")
    foreach(stub IN LISTS TITLE_STUBS)
        if(NOT EXISTS "${stub}")
            message(FATAL_ERROR "Missing additional public ABI stub: ${stub}")
        endif()
        list(APPEND extra_stub_arguments --stub "${stub}")
    endforeach()
    add_custom_command(OUTPUT "${dist}/eboot.bin" "${dist}/sce_module/libc.prx" "${dist}/sce_sys/param.json"
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${dist}/sce_module"
        COMMAND "${GP_LLVM}/ld.lld.exe" -m elf_x86_64 -pie "-T${GP_NATIVE_SOURCE}/ps5-pie.ld"
            --eh-frame-hdr -z max-page-size=0x4000 -mllvm -emulated-tls --hash-style=gnu --exclude-libs=ALL
            "--defsym=__eh_frame_start=ADDR(.eh_frame)" "--defsym=__eh_frame_end=ADDR(.eh_frame)+SIZEOF(.eh_frame)"
            "--defsym=__eh_frame_hdr_start=ADDR(.eh_frame_hdr)" "--defsym=__eh_frame_hdr_end=ADDR(.eh_frame_hdr)+SIZEOF(.eh_frame_hdr)"
            "--version-script=${work}/local.map" "-Map=${work}/link.map" "-L${GP_SDK_ROOT}/target/lib"
            -e _start $<TARGET_OBJECTS:${target}_objects> ${heap_link_options} ${TITLE_LIBRARIES}
            --start-group -lc++ -lc++abi -lunwind -lc --end-group
            --as-needed -lSceSystemService -lkernel -lSceLibcInternal -lSceNet -lc -o "${work}/llvm-pie.elf"
        COMMAND "${GP_NATIVE_TOOL}" link --in "${work}/llvm-pie.elf" --out "${work}/eboot.elf"
            --stub-dir "${GP_SDK_ROOT}/target/lib" ${extra_stub_arguments} --module-sdk 0x02000009 --companion-sdk 0x08050001 --file-name eboot.elf
        COMMAND "${GP_NATIVE_TOOL}" self --sign --in "${work}/eboot.elf" --out "${dist}/eboot.bin" --magic 0x1D3D154F
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${GP_LIBC}" "${dist}/sce_module/libc.prx"
        ${asset_commands}
        COMMAND "${GP_PYTHON}" "${GP_NATIVE_SDK}/host/package_title.py" --directory "${dist}"
            --title-id "${TITLE_TITLE_ID}" --title-name "${TITLE_TITLE_NAME}" --workspace "${GP_WORKSPACE}" ${content_arguments}
        COMMAND "${GP_NATIVE_TOOL}" self --inspect --file "${dist}/eboot.bin"
        DEPENDS ${target}_objects $<TARGET_OBJECTS:${target}_objects>
            "${GP_NATIVE_TOOL}" "${GP_LIBC}" "${GP_NATIVE_SOURCE}/ps5-pie.ld"
            "${GP_NATIVE_SDK}/host/package_title.py" ${shader_outputs} ${asset_inputs} ${TITLE_LINK_DEPENDS} ${TITLE_STUBS}
        COMMAND_EXPAND_LISTS VERBATIM)
    add_custom_target(${target} ALL DEPENDS "${dist}/eboot.bin" "${dist}/sce_module/libc.prx" "${dist}/sce_sys/param.json")
endfunction()
