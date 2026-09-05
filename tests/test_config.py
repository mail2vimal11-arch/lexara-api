"""Config tests — CORS origin computation (QA-BUG-4 follow-up)."""

from app.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(secret_key="test", _env_file=None, **overrides)


class TestCorsOrigins:
    def test_site_origins_present_by_default(self):
        origins = _settings().cors_origins()
        assert "https://lexara.tech" in origins
        assert "https://www.lexara.tech" in origins

    def test_stale_env_cannot_lock_out_the_site(self):
        # The exact prod failure: a deployment .env still listing only the
        # pre-rename domain must not remove the site's own origins.
        origins = _settings(
            allowed_origins="http://localhost:3000,https://lexrisk.com"
        ).cors_origins()
        assert "https://lexara.tech" in origins
        assert "https://www.lexara.tech" in origins
        assert "https://lexrisk.com" in origins  # env additions still honored

    def test_env_origins_are_kept_and_not_duplicated(self):
        origins = _settings(
            allowed_origins="https://lexara.tech,https://staging.example.com"
        ).cors_origins()
        assert origins.count("https://lexara.tech") == 1
        assert "https://staging.example.com" in origins

    def test_whitespace_and_empty_entries_are_dropped(self):
        origins = _settings(allowed_origins=" https://a.example , ,").cors_origins()
        assert "https://a.example" in origins
        assert "" not in origins
