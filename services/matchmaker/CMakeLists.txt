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

# Dependencies (to be added as needed)
# find_package(hiredis REQUIRED)
# find_package(nats REQUIRED)
# find_package(spdlog REQUIRED)
# find_package(nlohmann_json REQUIRED)

# Source files
set(SOURCES
    src/main.cpp
    # Add more source files as implemented
)

set(HEADERS
    include/matchmaker/matchmaker.hpp
    # Add more headers as implemented
)

# Main executable
add_executable(matchmaker ${SOURCES} ${HEADERS})

target_include_directories(matchmaker
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Link libraries (uncomment as dependencies are added)
# target_link_libraries(matchmaker
#     PRIVATE
#         hiredis::hiredis
#         nats::nats
#         spdlog::spdlog
#         nlohmann_json::nlohmann_json
# )

# Tests
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Install
install(TARGETS matchmaker
    RUNTIME DESTINATION bin
)
