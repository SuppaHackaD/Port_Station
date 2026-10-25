cmake_minimum_required(VERSION 3.25)
project(TcoalWineTitle LANGUAGES C CXX)
include("${CMAKE_CURRENT_LIST_DIR}/../../../sdk/ps5-game-port/cmake/PS5GamePort.cmake")
set(upstream "${GP_WORKSPACE}/build/prospero-evaluation/source-v020")
set(files native/pw_diagnostics.c native/pw_audio_ps5.c native/pw_pad_ps5.c native/pw_agc_ps5.c native/pw_agc_submit_lifecycle.c native/pw_videoout_ps5.c native/pw_data_mount.c native/pw_lapy_elevation.c native/pw_wine_display.c native/pw_wine_library.c native/pw_hid_ps5.c native/pw_wine_prefix.c src/pw_result.c src/pw_wine_start.c src/pw_wine_launch.c src/pw_game_profile.c src/pw_prefix_temp.c src/pw_app_profile.c src/pw_profile_catalog.c src/pw_launcher_render.c src/pw_present.c src/pw_pad.c src/pw_hid.c src/pw_spinner.c src/pw_script_input.c src/pw_tsc_calibrate.c wine/ps5/pw_wine_prx.c native/ps5log/ps5log.c native/ps5log/ps5log_ps5_net.c)
set(generated "${GP_WORKSPACE}/build/tcoal-wine-title/generated")
set(sources "${generated}/wine64_main.c" "${generated}/tcoal_bootstrap.c" "${CMAKE_CURRENT_LIST_DIR}/tcoal_close.c")
foreach(file IN LISTS files)
 list(APPEND sources "${upstream}/${file}")
endforeach()
ps5_game_port_title(tcoal_wine TITLE_ID PPSA99400 TITLE_NAME "The Coffin of Andy and Leyley"
 SOURCES ${sources}
 CONTENT_NOTE "Private standalone Wine compatibility build of user-owned TCOAL; Canvas and original Faustina font; Options + touchpad to close."
 LIBRARIES -lSceAgc -lSceAgcDriver -lSceVideoOut -lScePad -lSceUserService -lSceAudioOut -lSceSysmodule -lSceNet -lkernel)
target_include_directories(tcoal_wine_objects PRIVATE "${upstream}/include" "${upstream}/src" "${upstream}/native" "${upstream}/native/ps5log" "${CMAKE_CURRENT_LIST_DIR}" "${generated}")
target_compile_definitions(tcoal_wine_objects PRIVATE GP_BOOT_LOG="/data/tcoal-wine-boot.log" PW_BUILD_ID="tcoal-standalone-v1" PW_WINE64_SCRIPT=0 PW_WINE64_SECONDS=0 PW_WINE64_SCRIPT_CYCLES=2 PW_WINE64_WAIT_WATCHDOG=0)
target_compile_options(tcoal_wine_objects PRIVATE -Wno-unused-function)
set_source_files_properties("${upstream}/native/ps5log/ps5log.c" PROPERTIES COMPILE_OPTIONS "-include;${upstream}/native/ps5log/ps5log_ps5_net.h")
