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


class TestSchemaReconcile:
    """QA-BUG-5: prod `users` predates newer model columns; create_all never
    adds columns to existing tables, so INSERTs 500'd in production only."""

    def _drifted_engine(self, tmp_path):
        from sqlalchemy import create_engine, text
        eng = create_engine(f"sqlite:///{tmp_path}/drift.db")
        with eng.begin() as conn:
            # users as it existed at first deploy — no billing-era columns
            conn.execute(text("""
                CREATE TABLE users (
                    id VARCHAR PRIMARY KEY,
                    username VARCHAR NOT NULL,
                    email VARCHAR NOT NULL,
                    hashed_password VARCHAR NOT NULL,
                    role VARCHAR
                )"""))
            conn.execute(text(
                "INSERT INTO users (id, username, email, hashed_password, role) "
                "VALUES ('u1', 'olduser', 'old@example.com', 'x', 'procurement')"))
        return eng

    def test_reconcile_adds_missing_columns_and_backfills(self, tmp_path):
        from sqlalchemy import inspect, text
        from app.database.session import reconcile_schema
        eng = self._drifted_engine(tmp_path)

        reconcile_schema(bind=eng)

        cols = {c["name"] for c in inspect(eng).get_columns("users")}
        assert {"plan_id", "stripe_customer_id", "is_active",
                "created_at", "updated_at"} <= cols
        with eng.connect() as conn:
            row = conn.execute(text(
                "SELECT plan_id, is_active FROM users WHERE id='u1'")).one()
        assert row.plan_id == "free"        # scalar default backfilled
        assert row.is_active in (True, 1)   # sqlite stores bool as int

    def test_reconcile_is_idempotent(self, tmp_path):
        from app.database.session import reconcile_schema
        eng = self._drifted_engine(tmp_path)
        reconcile_schema(bind=eng)
        reconcile_schema(bind=eng)  # second run must be a clean no-op
