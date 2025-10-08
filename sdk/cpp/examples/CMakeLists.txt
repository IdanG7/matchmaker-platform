cmake_minimum_required(VERSION 3.20)

# Simple example application
add_executable(example_client
    simple_client.cpp
)

target_include_directories(example_client
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

target_link_libraries(example_client
    PRIVATE
        game-sdk
)

# Party test application
add_executable(party_test
    party_test.cpp
)

target_include_directories(party_test
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

target_link_libraries(party_test
    PRIVATE
        game-sdk
)
