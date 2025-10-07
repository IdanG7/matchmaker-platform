cmake_minimum_required(VERSION 3.20)
project(matchmaker VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Options
option(BUILD_TESTS "Build unit tests" ON)
option(ENABLE_ASAN "Enable AddressSanitizer" OFF)

# Compiler flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra -Wpedantic -Werror)
    if(ENABLE_ASAN)
        add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
        add_link_options(-fsanitize=address)
    endif()
endif()

# Dependencies - use FetchContent for cross-platform compatibility
include(FetchContent)

# Try to find system packages first, fall back to FetchContent
find_package(spdlog QUIET)
if(NOT spdlog_FOUND)
    message(STATUS "spdlog not found, fetching from GitHub...")
    FetchContent_Declare(
        spdlog
        GIT_REPOSITORY https://github.com/gabime/spdlog.git
        GIT_TAG v1.12.0
    )
    FetchContent_MakeAvailable(spdlog)
endif()

find_package(nlohmann_json QUIET)
if(NOT nlohmann_json_FOUND)
    message(STATUS "nlohmann_json not found, fetching from GitHub...")
    FetchContent_Declare(
        nlohmann_json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG v3.11.3
    )
    FetchContent_MakeAvailable(nlohmann_json)
endif()

# Note: hiredis and nats.c will be added via FetchContent for easier cross-platform builds

# Source files
set(SOURCES
    src/main.cpp
    src/queue_manager.cpp
    src/team_builder.cpp
)

set(HEADERS
    include/matchmaker/matchmaker.hpp
    include/matchmaker/queue_manager.hpp
    include/matchmaker/team_builder.hpp
)

# Main executable
add_executable(matchmaker ${SOURCES} ${HEADERS})

target_include_directories(matchmaker
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Link libraries
target_link_libraries(matchmaker
    PRIVATE
        spdlog::spdlog
        nlohmann_json::nlohmann_json
)

# Tests
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Install
install(TARGETS matchmaker
    RUNTIME DESTINATION bin
)
