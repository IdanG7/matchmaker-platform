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

# nats.c - the official NATS client. TLS and streaming are off: this service
# talks to NATS over the internal network and uses plain core pub/sub.
set(NATS_BUILD_WITH_TLS OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_STREAMING OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_LIB_SHARED OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_LIB_STATIC ON CACHE BOOL "" FORCE)

# nats.c registers its own 300+ tests through the standard CTest option, and
# they need a live nats-server. Left on, `ctest` here runs those instead of
# this service's tests and fails. This service's own tests use BUILD_TESTS.
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)

FetchContent_Declare(
    cnats
    GIT_REPOSITORY https://github.com/nats-io/nats.c.git
    GIT_TAG v3.8.2
)
FetchContent_MakeAvailable(cnats)

# Source files
set(SOURCES
    src/main.cpp
    src/queue_manager.cpp
    src/team_builder.cpp
    src/nats_client.cpp
)

set(HEADERS
    include/matchmaker/nats_client.hpp
    include/matchmaker/queue_manager.hpp
    include/matchmaker/team_builder.hpp
)

# Main executable
add_executable(matchmaker ${SOURCES} ${HEADERS})

target_include_directories(matchmaker
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        # nats.c exposes its public header as src/nats.h in the source tree and
        # only relocates it to nats/nats.h on install, and the static target
        # does not carry an interface include path.
        ${cnats_SOURCE_DIR}/src
)

# Link libraries
target_link_libraries(matchmaker
    PRIVATE
        spdlog::spdlog
        nlohmann_json::nlohmann_json
        nats_static
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
