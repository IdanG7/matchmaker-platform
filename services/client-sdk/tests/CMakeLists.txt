# Unit tests for client SDK

FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)

# Test executable
add_executable(sdk_tests
    test_types.cpp
    test_event_queue.cpp
)

target_link_libraries(sdk_tests
    PRIVATE
        matchmaker_client
        gtest
        gtest_main
)

# Register tests with CTest
include(GoogleTest)
gtest_discover_tests(sdk_tests)
