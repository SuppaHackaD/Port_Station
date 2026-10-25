cmake_minimum_required(VERSION 3.25)
project(ProsperoAchievementsSDKTest LANGUAGES C CXX)
include("${CMAKE_CURRENT_LIST_DIR}/../../ps5-game-port/cmake/PS5GamePort.cmake")
set(pa "${GP_WORKSPACE}/src/prospero_achievements")
set(sdk "${GP_WORKSPACE}/sdk/prospero-achievements")
ps5_game_port_title(pa_sdk_test TITLE_ID PPSA99401 TITLE_NAME "Prospero Achievements - SDK Test"
 SOURCES "${pa}/pa_probe.c"
 CONTENT_NOTE "Diagnostic SDK client only; synthetic catalog and separate test profile. No game or system trophies altered."
 LIBRARIES "${GP_WORKSPACE}/build/prospero-achievements/ps5/libprospero_achievements.a" -lSceNet -lkernel
 LINK_DEPENDS "${GP_WORKSPACE}/build/prospero-achievements/ps5/libprospero_achievements.a")
target_include_directories(pa_sdk_test_objects PRIVATE "${sdk}/include" "${GP_WORKSPACE}/build/prospero-achievements/generated")
target_compile_definitions(pa_sdk_test_objects PRIVATE PA_PS5=1 PA_NATIVE_TITLE=1 CJSON_NESTING_LIMIT=32 GP_BOOT_LOG="/download0/pa-sdk-test-boot.log")
target_compile_options(pa_sdk_test_objects PRIVATE -Wno-unreachable-code-generic-assoc)
