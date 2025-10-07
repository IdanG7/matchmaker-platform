#pragma once

#include "types.hpp"
#include "http_client.hpp"
#include <memory>

namespace matchmaker {

/**
 * Profile API wrapper.
 * Handles profile retrieval and updates.
 */
class ProfileAPI {
public:
    explicit ProfileAPI(std::shared_ptr<HTTPClient> http_client);
    ~ProfileAPI() = default;

    /**
     * Get current user's profile.
     *
     * @return ProfileInfo on success, error on failure
     */
    Result<ProfileInfo> get_profile();

    /**
     * Update current user's profile.
     *
     * @param request Update details (only non-null fields are updated)
     * @return Updated ProfileInfo on success, error on failure
     */
    Result<ProfileInfo> update_profile(const ProfileUpdateRequest& request);

private:
    std::shared_ptr<HTTPClient> http_;
};

} // namespace matchmaker
