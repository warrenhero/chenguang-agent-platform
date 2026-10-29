import pytest

pytestmark = pytest.mark.asyncio

ORIGIN = "http://localhost:5173"


async def test_cors_allows_frontend_origin(client):
    resp = await client.get("/health", headers={"Origin": ORIGIN})

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == ORIGIN


async def test_cors_preflight(client):
    resp = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == ORIGIN
    assert "POST" in resp.headers.get("access-control-allow-methods", "")


async def test_cors_allows_any_local_port(client):
    resp = await client.get("/health", headers={"Origin": "http://localhost:4321"})

    assert resp.headers.get("access-control-allow-origin") == "http://localhost:4321"


async def test_cors_rejects_external_origin(client):
    resp = await client.get("/health", headers={"Origin": "https://evil.example.com"})

    assert "access-control-allow-origin" not in resp.headers
