cmake_minimum_required(VERSION 3.20)

# GoogleTest
include(FetchContent)
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.15.2
)
FetchContent_MakeAvailable(googletest)

# Silence AppleClang 21 -Wcharacter-conversion warning in gtest-printers.h
# (char8_t -> char32_t implicit cast). gtest is third-party; don't fail on its warnings.
# These are GCC/Clang spellings; MSVC rejects -Wno-error outright, which broke
# the Windows build of gtest itself.
foreach(_gtest_target gtest gtest_main gmock gmock_main)
    if(TARGET ${_gtest_target})
        if(MSVC)
            target_compile_options(${_gtest_target} PRIVATE /w)
        else()
            target_compile_options(${_gtest_target} PRIVATE -Wno-error -w)
        endif()
    endif()
endforeach()

# Test executable
add_executable(matchmaker_tests
    test_main.cpp
    ../src/queue_manager.cpp
    ../src/team_builder.cpp
)

target_include_directories(matchmaker_tests
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

target_link_libraries(matchmaker_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        spdlog::spdlog
        nlohmann_json::nlohmann_json
)

# Discover tests
include(GoogleTest)
gtest_discover_tests(matchmaker_tests)
