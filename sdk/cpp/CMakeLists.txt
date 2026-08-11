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

# Native transport dependencies.
#
# Under Emscripten neither is used or fetched: the browser build talks to the
# network through emscripten's own fetch and websocket.js, and both of these
# libraries assume BSD sockets and threads.
if(NOT EMSCRIPTEN)
    # cpp-httplib for HTTP requests
    FetchContent_Declare(
        httplib
        GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
        GIT_TAG v0.15.3
    )

    # IXWebSocket for WebSocket.
    #
    # zlib only backs permessage-deflate, which we do not use, so it is
    # disabled rather than dragged in as a platform dependency. TLS is enabled
    # only when OpenSSL is already present: without this the build hard-fails
    # on machines that have neither, which is what the vcpkg/chocolatey CI
    # workarounds were compensating for.
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
endif()

# nlohmann_json for JSON parsing
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)

if(EMSCRIPTEN)
    FetchContent_MakeAvailable(json)
else()
    FetchContent_MakeAvailable(httplib ixwebsocket json)
endif()

# Source files
set(SOURCES
    src/sdk.cpp
    src/client.cpp
    src/auth.cpp
    src/session.cpp
)

# One of two transports, picked by target. Both satisfy src/transport.hpp, so
# nothing above this line knows which is in play.
if(EMSCRIPTEN)
    list(APPEND SOURCES src/transport_wasm.cpp)
else()
    list(APPEND SOURCES src/transport_native.cpp)
endif()

set(HEADERS
    include/game/sdk.hpp
    include/game/client.hpp
    include/game/auth.hpp
    include/game/session.hpp
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
if(EMSCRIPTEN)
    target_link_libraries(game-sdk PUBLIC nlohmann_json::nlohmann_json)

    # ASYNCIFY is what lets the blocking API survive in a browser: the
    # transport yields to the event loop mid-call and resumes afterwards.
    # websocket.js provides emscripten_websocket_*. Both are PUBLIC because
    # anything linking this library needs them at link time too.
    # Link-time only: emcc ignores these while compiling and warns.
    #   ASYNCIFY     lets the blocking API yield to the browser and resume
    #   FETCH        provides emscripten_fetch, used for HTTP
    #   websocket.js provides emscripten_websocket_*
    # PUBLIC because anything linking this library needs them at link time too.
    target_link_options(game-sdk PUBLIC -sASYNCIFY -sFETCH=1 -lwebsocket.js)
else()
    target_link_libraries(game-sdk
        PUBLIC
            nlohmann_json::nlohmann_json
        PRIVATE
            httplib::httplib
            ixwebsocket
    )
endif()

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
