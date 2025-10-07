#include <gtest/gtest.h>
#include "matchmaker/types.hpp"

using namespace matchmaker;

TEST(TypesTest, ResultSuccess) {
    auto result = Result<int>::Success(42);

    EXPECT_TRUE(result.success);
    EXPECT_TRUE(static_cast<bool>(result));
    EXPECT_EQ(result.value, 42);
}

TEST(TypesTest, ResultFailure) {
    APIError error{404, "Not Found", "Resource not found"};
    auto result = Result<int>::Failure(error);

    EXPECT_FALSE(result.success);
    EXPECT_FALSE(static_cast<bool>(result));
    EXPECT_EQ(result.error.status_code, 404);
    EXPECT_EQ(result.error.error, "Not Found");
}

TEST(TypesTest, ResultVoidSuccess) {
    auto result = Result<void>::Success();

    EXPECT_TRUE(result.success);
    EXPECT_TRUE(static_cast<bool>(result));
}

TEST(TypesTest, ResultVoidFailure) {
    APIError error{500, "Internal Error", ""};
    auto result = Result<void>::Failure(error);

    EXPECT_FALSE(result.success);
    EXPECT_FALSE(static_cast<bool>(result));
    EXPECT_EQ(result.error.status_code, 500);
}

TEST(TypesTest, APIErrorToString) {
    APIError error{403, "Forbidden", "Access denied"};
    std::string str = error.to_string();

    EXPECT_NE(str.find("403"), std::string::npos);
    EXPECT_NE(str.find("Forbidden"), std::string::npos);
    EXPECT_NE(str.find("Access denied"), std::string::npos);
}
