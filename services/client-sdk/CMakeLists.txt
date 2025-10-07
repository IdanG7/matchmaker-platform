cmake_minimum_required(VERSION 3.15)
project(MatchmakerClientSDK VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Options
option(BUILD_EXAMPLES "Build example applications" ON)
option(BUILD_TESTS "Build unit tests" ON)

# Dependencies
include(FetchContent)

# httplib (HTTP client)
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.14.3
)

# ixwebsocket (WebSocket client)
FetchContent_Declare(
    ixwebsocket
    GIT_REPOSITORY https://github.com/machinezone/IXWebSocket.git
    GIT_TAG v11.4.5
)

# nlohmann/json (JSON parsing)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)

FetchContent_MakeAvailable(httplib ixwebsocket json)

# Main library
add_library(matchmaker_client STATIC
    src/http_client.cpp
    src/websocket_client.cpp
    src/auth_api.cpp
    src/profile_api.cpp
    src/party_api.cpp
    src/session_api.cpp
    src/event_queue.cpp
    src/matchmaker_client.cpp
)

target_include_directories(matchmaker_client
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(matchmaker_client
    PUBLIC
        httplib::httplib
        ixwebsocket::ixwebsocket
        nlohmann_json::nlohmann_json
)

# Platform-specific libraries
if(UNIX AND NOT APPLE)
    target_link_libraries(matchmaker_client PRIVATE pthread)
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

# Installation
install(TARGETS matchmaker_client
    EXPORT MatchmakerClientTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/
    DESTINATION include
)
