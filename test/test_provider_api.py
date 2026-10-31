import uuid

import httpx
import pytest
from sqlalchemy import select

from src.core.bootstrap import DEFAULT_PERMISSIONS, apply_rbac_seed
from src.modules.provider.model import ModelProvider

pytestmark = pytest.mark.asyncio


def _payload(name: str | None = None, **overrides) -> dict:
    return {
        "name": f"供应商_{uuid.uuid4().hex[:8]}" if name is None else name,
        "type": "openai",
        "endpoint": "https://api.example.com/v1",
        "api_key": "sk-plaintext-secret",
        "description": "测试供应商",
        **overrides,
    }


async def _create(client, **overrides) -> dict:
    resp = await client.post("/api/v1/providers", json=_payload(**overrides))
    body = resp.json()
    assert body["code"] == 200, body
    return body["data"]


async def _create_model(client, provider_id: int) -> dict:
    resp = await client.post(
        "/api/v1/models",
        json={
            "name": f"模型_{uuid.uuid4().hex[:8]}",
            "model_id": f"model-{uuid.uuid4().hex[:8]}",
            "provider_id": provider_id,
        },
    )
    body = resp.json()
    assert body["code"] == 200, body
    return body["data"]


class _FakeResponse:
    status_code = 200


class _FakeAsyncClient:
    """记录调用参数的 httpx.AsyncClient 替身。"""

    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, headers=None, **kwargs):
        type(self).calls.append({"url": url, "headers": headers or {}})
        return _FakeResponse()


class _UnreachableAsyncClient(_FakeAsyncClient):
    async def get(self, url, headers=None, **kwargs):
        type(self).calls.append({"url": url, "headers": headers or {}})
        raise httpx.ConnectError("connection refused")


async def test_provider_endpoints_require_auth(anon_client):
    payload = _payload()
    cases = [
        ("GET", "/api/v1/providers", None),
        ("POST", "/api/v1/providers", payload),
        ("GET", "/api/v1/providers/1", None),
        ("PUT", "/api/v1/providers/1", {"description": "x"}),
        ("DELETE", "/api/v1/providers/1", None),
        ("POST", "/api/v1/providers/1/test", None),
    ]

    for method, path, json in cases:
        resp = await anon_client.request(method, path, json=json)
        assert resp.status_code == 401, (method, path, resp.status_code, resp.text)


async def test_bootstrap_seeds_provider_permissions(db_session):
    await apply_rbac_seed(db_session)

    codes = {code for code, _, _ in DEFAULT_PERMISSIONS}
    assert {
        "provider:read",
        "provider:create",
        "provider:update",
        "provider:delete",
    } <= codes


async def test_create_encrypts_api_key_at_rest_and_returns_plaintext(client, db_session):
    data = await _create(client)

    assert data["api_key"] == "sk-plaintext-secret"

    row = (
        await db_session.execute(
            select(ModelProvider).where(ModelProvider.id == data["id"])
        )
    ).scalar_one()
    assert row.api_key
    assert row.api_key != "sk-plaintext-secret"


async def test_get_returns_decrypted_api_key(client):
    created = await _create(client)

    resp = await client.get(f"/api/v1/providers/{created['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["api_key"] == "sk-plaintext-secret"


async def test_list_returns_decrypted_api_key_and_model_count(client):
    created = await _create(client)

    resp = await client.get("/api/v1/providers")

    body = resp.json()
    assert body["code"] == 200
    item = next(i for i in body["data"]["items"] if i["id"] == created["id"])
    assert item["api_key"] == "sk-plaintext-secret"
    assert item["model_count"] == 0


async def test_model_count_reflects_owned_models(client):
    provider = await _create(client)
    first_model = await _create_model(client, provider["id"])
    await _create_model(client, provider["id"])

    list_resp = await client.get("/api/v1/providers")
    list_item = next(
        i for i in list_resp.json()["data"]["items"] if i["id"] == provider["id"]
    )
    detail_body = (
        await client.get(f"/api/v1/providers/{provider['id']}")
    ).json()

    assert list_item["model_count"] == 2
    assert detail_body["data"]["model_count"] == 2

    delete_resp = await client.delete(f"/api/v1/models/{first_model['id']}")
    assert delete_resp.json()["code"] == 200

    detail_body = (
        await client.get(f"/api/v1/providers/{provider['id']}")
    ).json()
    assert detail_body["data"]["model_count"] == 1


async def test_delete_provider(client, db_session):
    created = await _create(client)

    resp = await client.delete(f"/api/v1/providers/{created['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert await db_session.get(ModelProvider, created["id"]) is None


async def test_connection_success_probes_endpoint_and_marks_connected(
    client, db_session, monkeypatch
):
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    created = await _create(client)

    resp = await client.post(f"/api/v1/providers/{created['id']}/test")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["success"] is True
    assert isinstance(body["data"]["latency_ms"], int)
    assert _FakeAsyncClient.calls[0]["url"] == "https://api.example.com/v1"
    assert _FakeAsyncClient.calls[0]["headers"]["Authorization"] == (
        "Bearer sk-plaintext-secret"
    )

    row = await db_session.get(ModelProvider, created["id"])
    assert row.status == "connected"


async def test_connection_failure_marks_error(client, db_session, monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _UnreachableAsyncClient)
    created = await _create(client)

    resp = await client.post(f"/api/v1/providers/{created['id']}/test")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["success"] is False
    assert "连接失败" in body["data"]["message"]

    row = await db_session.get(ModelProvider, created["id"])
    assert row.status == "error"


async def test_create_duplicate_name_returns_400(client):
    name = f"供应商_{uuid.uuid4().hex[:8]}"
    await _create(client, name=name)

    resp = await client.post("/api/v1/providers", json=_payload(name=name))

    body = resp.json()
    assert resp.status_code == 400
    assert body["code"] == 400
    assert "已存在" in body["message"]


async def test_update_to_duplicate_name_returns_400(client):
    first = await _create(client)
    second = await _create(client)

    resp = await client.put(
        f"/api/v1/providers/{second['id']}", json={"name": first["name"]}
    )

    body = resp.json()
    assert resp.status_code == 400
    assert body["code"] == 400
    assert "已存在" in body["message"]


async def test_update_keeping_own_name_is_allowed(client):
    created = await _create(client)

    resp = await client.put(
        f"/api/v1/providers/{created['id']}",
        json={"name": created["name"], "description": "新描述"},
    )

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["name"] == created["name"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", "x" * 101),
        ("type", ""),
        ("type", "unknown"),
        ("endpoint", ""),
        ("endpoint", "h" * 501),
        ("description", "d" * 501),
    ],
)
async def test_create_rejects_invalid_fields_with_422(client, field, value):
    resp = await client.post(
        "/api/v1/providers", json=_payload(**{field: value})
    )

    assert resp.status_code == 422


@pytest.mark.parametrize("value", ["", "x" * 101])
async def test_update_rejects_invalid_name_with_422(client, value):
    created = await _create(client)

    resp = await client.put(
        f"/api/v1/providers/{created['id']}", json={"name": value}
    )

    assert resp.status_code == 422


async def test_missing_provider_returns_404(client):
    missing_id = 999_999_999

    get_resp = await client.get(f"/api/v1/providers/{missing_id}")
    put_resp = await client.put(
        f"/api/v1/providers/{missing_id}", json={"description": "x"}
    )
    delete_resp = await client.delete(f"/api/v1/providers/{missing_id}")

    for resp in (get_resp, put_resp, delete_resp):
        assert resp.status_code == 404
        assert resp.json()["code"] == 404

