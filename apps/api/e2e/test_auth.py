from e2e.base import IntegrationTest


class TestAuthEndpoints(IntegrationTest):
    def test_whoami_fails_without_auth(self):
        r = self.client.get("/v5/whoami")
        assert r.status_code == 401, "Expected 401 when accessing whoami without auth"

    def test_whoami_with_anonymous_user(self):
        anonymous_user = self.user(anonymous=True)

        r = self.client.get("/v5/whoami", headers=self.auth(anonymous_user))
        assert r.status_code == 200, f"Expected 200 for anonymous user, got {r.status_code}"

        data = r.json()
        assert "client" in data, "Response should contain client field"
        assert data["client"] == anonymous_user.client, "Client ID should match"
        assert data.get("is_anonymous") is True, "Should be marked as anonymous"

    def test_whoami_with_authenticated_user(self):
        authenticated_user = self.user()

        r = self.client.get("/v5/whoami", headers=self.auth(authenticated_user))
        assert r.status_code == 200, f"Expected 200 for authenticated user, got {r.status_code}"

        data = r.json()
        assert "client" in data, "Response should contain client field"
        assert data["client"] == authenticated_user.client, "Client ID should match"
        assert data.get("is_anonymous") is False, "Should not be marked as anonymous"

    def test_multiple_anonymous_users_are_distinct(self):
        user1 = self.user(anonymous=True)
        user2 = self.user(anonymous=True)

        assert user1.client != user2.client, "Different anonymous users should have different client IDs"

    def test_invalid_bearer_token_returns_401(self):
        r = self.client.get("/v5/whoami", headers={"Authorization": "Bearer invalid_token_12345"})
        assert r.status_code == 401, "Expected 401 for invalid bearer token"

    def test_malformed_authorization_header_returns_401(self):
        test_cases = [
            "NotBearer token123",  # Wrong auth scheme
            "Bearer",  # No auth token
            "token123",  # No scheme
        ]

        for auth_header in test_cases:
            r = self.client.get("/v5/whoami", headers={"Authorization": auth_header})
            assert r.status_code == 401, f"Expected 401 for malformed header: {auth_header}"
