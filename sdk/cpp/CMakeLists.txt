cmake_minimum_required(VERSION 3.20)
project(game-sdk VERSION 0.1.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Options
option(BUILD_TESTS "Build unit tests" ON)
option(BUILD_EXAMPLES "Build example applications" ON)
option(BUILD_SHARED_LIBS "Build shared library" OFF)

# Compiler flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
    # Note: -Werror disabled to avoid issues with third-party dependencies
endif()

# Dependencies
include(FetchContent)

# cpp-httplib for HTTP requests
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.15.3
)

# IXWebSocket for WebSocket.
#
# zlib only backs permessage-deflate, which we do not use, so it is disabled
# rather than dragged in as a platform dependency. TLS is enabled only when
# OpenSSL is already present: without this the build hard-fails on machines
# that have neither, which is what the vcpkg/chocolatey CI workarounds were
# compensating for.
set(USE_ZLIB OFF CACHE BOOL "" FORCE)
set(IXWEBSOCKET_INSTALL OFF CACHE BOOL "" FORCE)

find_package(OpenSSL QUIET)
if(OPENSSL_FOUND)
    message(STATUS "OpenSSL found - enabling TLS (wss:// and https:// supported)")
    set(USE_TLS ON CACHE BOOL "" FORCE)
else()
    message(STATUS "OpenSSL not found - building without TLS (ws:// and http:// only)")
    set(USE_TLS OFF CACHE BOOL "" FORCE)
endif()

FetchContent_Declare(
    ixwebsocket
    GIT_REPOSITORY https://github.com/machinezone/IXWebSocket.git
    GIT_TAG v11.4.6
)

# nlohmann_json for JSON parsing
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)

FetchContent_MakeAvailable(httplib ixwebsocket json)

# Source files
set(SOURCES
    src/sdk.cpp
    src/client.cpp
    src/auth.cpp
)

set(HEADERS
    include/game/sdk.hpp
    include/game/client.hpp
    include/game/auth.hpp
    include/game/types.hpp
)

# Library
if(BUILD_SHARED_LIBS)
    add_library(game-sdk SHARED ${SOURCES} ${HEADERS})
else()
    add_library(game-sdk STATIC ${SOURCES} ${HEADERS})
endif()

target_include_directories(game-sdk
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Link libraries
target_link_libraries(game-sdk
    PUBLIC
        nlohmann_json::nlohmann_json
    PRIVATE
        httplib::httplib
        ixwebsocket
)

# Examples
if(BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Install
install(TARGETS game-sdk
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/game
    DESTINATION include
)
