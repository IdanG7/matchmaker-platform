cmake_minimum_required(VERSION 3.20)
project(game-sdk VERSION 0.1.0 LANGUAGES CXX)

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
    GIT_TAG v0.14.3
)

# IXWebSocket for WebSocket
FetchContent_Declare(
    ixwebsocket
    GIT_REPOSITORY https://github.com/machinezone/IXWebSocket.git
    GIT_TAG v11.4.5
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
    src/websocket.cpp
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
