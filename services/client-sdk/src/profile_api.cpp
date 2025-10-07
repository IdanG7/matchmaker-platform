#include "matchmaker/profile_api.hpp"

namespace matchmaker {

ProfileAPI::ProfileAPI(std::shared_ptr<HTTPClient> http_client)
    : http_(std::move(http_client)) {
}

Result<ProfileInfo> ProfileAPI::get_profile() {
    auto result = http_->get("/v1/profile/me");

    if (!result) {
        return Result<ProfileInfo>::Failure(result.error);
    }

    ProfileInfo profile;
    profile.player_id = result.value["player_id"];
    profile.username = result.value["username"];
    profile.email = result.value["email"];
    profile.region = result.value["region"];
    profile.mmr = result.value["mmr"];
    profile.created_at = result.value["created_at"];

    return Result<ProfileInfo>::Success(profile);
}

Result<ProfileInfo> ProfileAPI::update_profile(const ProfileUpdateRequest& request) {
    json body = json::object();

    if (request.region.has_value()) {
        body["region"] = request.region.value();
    }

    auto result = http_->patch("/v1/profile/me", body);

    if (!result) {
        return Result<ProfileInfo>::Failure(result.error);
    }

    ProfileInfo profile;
    profile.player_id = result.value["player_id"];
    profile.username = result.value["username"];
    profile.email = result.value["email"];
    profile.region = result.value["region"];
    profile.mmr = result.value["mmr"];
    profile.created_at = result.value["created_at"];

    return Result<ProfileInfo>::Success(profile);
}

} // namespace matchmaker
