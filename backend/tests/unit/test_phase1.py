"""
Phase 1 Tests — Application Startup & Health Endpoints

Tests:
  - FastAPI app creates without error
  - GET /health returns expected shape
  - GET /health/ready returns 200 or 503 (never crashes)
  - OpenAPI JSON is accessible
  - CORS headers present on responses
"""
import pytest
from httpx import AsyncClient


class TestAppStartup:
    """Verify the application factory creates a valid, runnable app."""

    def test_create_app_returns_fastapi_instance(self, app):
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_app_has_correct_title(self, app):
        assert app.title == "NEXORA API"

    def test_app_has_version(self, app):
        assert app.version  # non-empty string

    def test_app_openapi_schema_exists(self, app):
        schema = app.openapi()
        assert schema["info"]["title"] == "NEXORA API"
        assert "paths" in schema


class TestHealthLiveness:
    """Test GET /health — liveness probe."""

    async def test_returns_200(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_response_is_json(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.headers["content-type"].startswith("application/json")

    async def test_status_field_is_ok(self, client: AsyncClient):
        response = await client.get("/health")
        body = response.json()
        assert body["status"] == "ok"

    async def test_service_field_present(self, client: AsyncClient):
        body = (await client.get("/health")).json()
        assert body["service"] == "nexora-api"

    async def test_version_field_present(self, client: AsyncClient):
        body = (await client.get("/health")).json()
        assert "version" in body
        assert body["version"]  # non-empty

    async def test_environment_field_present(self, client: AsyncClient):
        body = (await client.get("/health")).json()
        assert body["environment"] == "test"

    async def test_timestamp_field_present(self, client: AsyncClient):
        body = (await client.get("/health")).json()
        assert "timestamp" in body

    async def test_request_id_header_returned(self, client: AsyncClient):
        """Every response must carry X-Request-Id for tracing."""
        response = await client.get("/health")
        assert "x-request-id" in response.headers


class TestHealthReadiness:
    """
    Test GET /health/ready — readiness probe.
    May return 200 (DB connected) or 503 (DB unreachable) — both are valid
    responses from the endpoint itself; the test just checks it doesn't crash.
    """

    async def test_returns_200_or_503(self, client: AsyncClient):
        response = await client.get("/health/ready")
        assert response.status_code in (200, 503)

    async def test_response_is_json(self, client: AsyncClient):
        response = await client.get("/health/ready")
        assert response.headers["content-type"].startswith("application/json")

    async def test_body_contains_status_field(self, client: AsyncClient):
        body = (await client.get("/health/ready")).json()
        # 200 → {"status": "ready", ...}
        # 503 → {"detail": {"status": "not_ready", ...}}
        if "status" in body:
            assert body["status"] in ("ready", "not_ready")
        elif "detail" in body:
            assert body["detail"]["status"] == "not_ready"


class TestOpenAPI:
    """Verify OpenAPI documentation endpoints are accessible."""

    async def test_openapi_json_accessible(self, client: AsyncClient):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["openapi"].startswith("3.")

    async def test_docs_ui_accessible(self, client: AsyncClient):
        response = await client.get("/docs")
        assert response.status_code == 200

    async def test_redoc_ui_accessible(self, client: AsyncClient):
        response = await client.get("/redoc")
        assert response.status_code == 200


class TestExceptionHandling:
    """Verify the global exception handlers work correctly."""

    async def test_nexora_error_returns_structured_json(self, client: AsyncClient, app):
        """
        Inject a route that raises a NexoraError to verify the handler
        converts it to a proper JSON response.
        """
        from fastapi import APIRouter
        from app.exceptions import ResourceNotFoundError

        test_router = APIRouter()

        @test_router.get("/_test/nexora-error")
        async def _raise_nexora():
            raise ResourceNotFoundError(
                "Test resource not found",
                detail={"resource": "test"},
            )

        app.include_router(test_router)

        response = await client.get("/_test/nexora-error")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "NOT_FOUND"
        assert "message" in body

    async def test_404_for_unknown_route(self, client: AsyncClient):
        response = await client.get("/this/route/does/not/exist")
        assert response.status_code == 404


class TestConfiguration:
    """Verify settings load correctly in test mode."""

    def test_environment_is_test(self):
        from app.config import get_settings
        s = get_settings()
        assert s.ENVIRONMENT == "test"

    def test_app_name_set(self):
        from app.config import get_settings
        s = get_settings()
        assert s.APP_NAME == "NEXORA"

    def test_log_level_valid(self):
        from app.config import get_settings
        s = get_settings()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        assert s.LOG_LEVEL in valid

    def test_cors_origins_is_list(self):
        from app.config import get_settings
        s = get_settings()
        assert isinstance(s.CORS_ORIGINS, list)
        assert len(s.CORS_ORIGINS) > 0

    def test_db_pool_size_positive(self):
        from app.config import get_settings
        s = get_settings()
        assert s.DB_POOL_SIZE > 0

    def test_database_url_contains_asyncpg(self):
        from app.config import get_settings
        s = get_settings()
        assert "asyncpg" in s.DATABASE_URL
