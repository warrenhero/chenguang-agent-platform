import uuid

import pytest

from src.core.bootstrap import DEFAULT_PERMISSIONS, apply_rbac_seed
from src.core.exceptions import _HTTP_STATUS
from src.modules.user.model import User
from src.utils.jwt_utils import encode_jwt

pytestmark = pytest.mark.asyncio

MISSING_ID = 999_999_999


def _model_payload(provider_id: int = 1) -> dict:
    return {
        "name": f"模型_{uuid.uuid4().hex[:8]}",
        "model_id": f"model-{uuid.uuid4().hex[:8]}",
        "provider_id": provider_id,
        "capabilities": ["streaming"],
        "context_length": 8192,
        "input_price": 0.001,
        "output_price": 0.002,
        "currency": "USD",
        "is_default": False,
        "description": "测试模型",
    }


async def test_model_endpoints_require_auth(anon_client):
    payload = _model_payload()
    cases = [
        ("POST", "/api/v1/models", payload),
        ("GET", "/api/v1/models", None),
        ("GET", "/api/v1/models/1", None),
        ("PUT", "/api/v1/models/1", {"description": "x"}),
        ("DELETE", "/api/v1/models/1", None),
    ]

    for method, path, json in cases:
        resp = await anon_client.request(method, path, json=json)
        assert resp.status_code == 401, (method, path, resp.status_code, resp.text)


async def test_bootstrap_seeds_model_permissions(db_session):
    await apply_rbac_seed(db_session)

    codes = {code for code, _, _ in DEFAULT_PERMISSIONS}
    assert {
        "model:read",
        "model:create",
        "model:update",
        "model:delete",
    } <= codes


async def _create_provider(client) -> dict:
    resp = await client.post(
        "/api/v1/providers",
        json={
            "name": f"供应商_{uuid.uuid4().hex[:8]}",
            "type": "openai",
            "endpoint": "https://api.example.com/v1",
            "api_key": "sk-plaintext-secret",
        },
    )
    body = resp.json()
    assert body["code"] == 200, body
    return body["data"]


async def test_conflict_code_maps_to_http_409():
    assert _HTTP_STATUS[409] == 409


async def test_get_missing_model_returns_404(client):
    resp = await client.get(f"/api/v1/models/{MISSING_ID}")

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == 404


async def test_create_duplicate_model_id_returns_400(client):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    created = await client.post("/api/v1/models", json=payload)
    assert created.json()["code"] == 200, created.text

    resp = await client.post("/api/v1/models", json=payload)

    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == 400


async def test_create_model_with_missing_provider_returns_400(client):
    resp = await client.post("/api/v1/models", json=_model_payload(MISSING_ID))

    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == 400


async def test_user_without_permission_forbidden(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"plain_{suffix}",
        email=f"plain_{suffix}@example.com",
        hashed_password="not-used",
    )
    db_session.add(user)
    await db_session.flush()
    headers = {"Authorization": f"Bearer {encode_jwt({'sub': str(user.id)})}"}

    resp = await client.get("/api/v1/models", headers=headers)

    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == 403
    assert "model:read" in body["message"]


async def _create_model(
    client, provider_id: int, name: str, model_id: str | None = None
) -> dict:
    payload = _model_payload(provider_id)
    payload["name"] = name
    payload["model_id"] = model_id or f"model-{uuid.uuid4().hex[:12]}"
    resp = await client.post("/api/v1/models", json=payload)
    body = resp.json()
    assert body["code"] == 200, body
    return body["data"]


async def test_list_models_filters_by_provider(client):
    provider_a = await _create_provider(client)
    provider_b = await _create_provider(client)
    await _create_model(client, provider_a["id"], f"模型A1_{uuid.uuid4().hex[:8]}")
    await _create_model(client, provider_a["id"], f"模型A2_{uuid.uuid4().hex[:8]}")
    await _create_model(client, provider_b["id"], f"模型B1_{uuid.uuid4().hex[:8]}")

    resp = await client.get("/api/v1/models", params={"provider_id": provider_a["id"]})

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert {item["provider_id"] for item in data["items"]} == {provider_a["id"]}


async def test_list_models_provider_and_keyword_compose(client):
    provider_a = await _create_provider(client)
    provider_b = await _create_provider(client)
    token = uuid.uuid4().hex[:8]
    alpha_a = await _create_model(client, provider_a["id"], f"alpha_{token}")
    await _create_model(client, provider_a["id"], f"beta_{token}")
    await _create_model(client, provider_b["id"], f"alpha_{token}")

    resp = await client.get(
        "/api/v1/models",
        params={"provider_id": provider_a["id"], "keyword": f"alpha_{token}"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 1
    assert [item["id"] for item in data["items"]] == [alpha_a["id"]]


async def test_list_models_empty_result_keeps_requested_pagination(client):
    provider = await _create_provider(client)

    resp = await client.get(
        "/api/v1/models",
        params={"provider_id": provider["id"], "page": 3, "page_size": 5},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 3
    assert data["page_size"] == 5


async def test_list_models_rejects_page_size_over_limit(client):
    resp = await client.get("/api/v1/models", params={"page_size": 101})

    assert resp.status_code == 422, resp.text


async def test_create_model_rejects_overlong_name(client):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    payload["name"] = "名" * 101

    resp = await client.post("/api/v1/models", json=payload)

    assert resp.status_code == 422, resp.text


async def test_create_model_accepts_name_at_max_length(client):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    payload["name"] = "名" * 100

    resp = await client.post("/api/v1/models", json=payload)

    body = resp.json()
    assert body["code"] == 200, body
    assert body["data"]["name"] == "名" * 100


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("input_price", -0.001),
        ("output_price", -1),
        ("context_length", 0),
        ("currency", ""),
    ],
)
async def test_create_model_rejects_invalid_values(client, field, value):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    payload[field] = value

    resp = await client.post("/api/v1/models", json=payload)

    assert resp.status_code == 422, resp.text


async def test_create_model_rejects_overlong_capability(client):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    payload["capabilities"] = ["a" * 51]

    resp = await client.post("/api/v1/models", json=payload)

    assert resp.status_code == 422, resp.text


async def test_create_model_rejects_capabilities_exceeding_column_limit(client):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    # 每个元素都合法，但逗号拼接后超长，仍不能落库
    payload["capabilities"] = ["a" * 50] * 11

    resp = await client.post("/api/v1/models", json=payload)

    assert resp.status_code == 422, resp.text


async def test_create_model_accepts_capabilities_joined_at_column_limit(client):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    # 9 * 50 + 41 + 9 个逗号 = 500，恰好等于列宽
    payload["capabilities"] = ["a" * 50] * 9 + ["a" * 41]

    resp = await client.post("/api/v1/models", json=payload)

    body = resp.json()
    assert body["code"] == 200, body
    assert len(",".join(body["data"]["capabilities"])) == 500


async def test_update_model_rejects_invalid_status(client):
    provider = await _create_provider(client)
    model = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    resp = await client.put(f"/api/v1/models/{model['id']}", json={"status": "broken"})

    assert resp.status_code == 422, resp.text


async def test_update_model_accepts_valid_status(client):
    provider = await _create_provider(client)
    model = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    resp = await client.put(
        f"/api/v1/models/{model['id']}", json={"status": "rate_limited"}
    )

    body = resp.json()
    assert body["code"] == 200, body
    assert body["data"]["status"] == "rate_limited"


async def test_update_model_rejects_overlong_name(client):
    provider = await _create_provider(client)
    model = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    resp = await client.put(f"/api/v1/models/{model['id']}", json={"name": "a" * 101})

    assert resp.status_code == 422, resp.text


async def test_update_model_rejects_capabilities_exceeding_column_limit(client):
    provider = await _create_provider(client)
    model = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    resp = await client.put(
        f"/api/v1/models/{model['id']}",
        json={"capabilities": ["a" * 50] * 11},
    )

    assert resp.status_code == 422, resp.text


async def test_create_model_echoes_all_fields(client):
    provider = await _create_provider(client)
    payload = _model_payload(provider["id"])
    payload.update(
        capabilities=["streaming", "vision"],
        context_length=16384,
        input_price=0.001,
        output_price=0.002,
        currency="CNY",
        description="字段回显模型",
    )

    resp = await client.post("/api/v1/models", json=payload)

    body = resp.json()
    assert body["code"] == 200, body
    data = body["data"]
    assert data["name"] == payload["name"]
    assert data["model_id"] == payload["model_id"]
    assert data["provider_id"] == provider["id"]
    assert data["provider_name"] == provider["name"]
    assert data["capabilities"] == ["streaming", "vision"]
    assert data["context_length"] == 16384
    assert data["status"] == "available"
    assert data["input_price"] == 0.001
    assert data["output_price"] == 0.002
    assert data["currency"] == "CNY"
    assert data["is_default"] is False
    assert data["description"] == "字段回显模型"


async def test_get_model_detail_matches_created(client):
    provider = await _create_provider(client)
    model = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    resp = await client.get(f"/api/v1/models/{model['id']}")

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == model


async def test_update_model_returns_updated_fields(client):
    provider = await _create_provider(client)
    model = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")
    new_name = f"新名称_{uuid.uuid4().hex[:8]}"

    resp = await client.put(
        f"/api/v1/models/{model['id']}",
        json={
            "name": new_name,
            "capabilities": ["function_call", "vision"],
            "context_length": 32768,
            "input_price": 0.003,
            "output_price": 0.006,
            "currency": "CNY",
            "description": "更新后的描述",
        },
    )

    body = resp.json()
    assert body["code"] == 200, body
    data = body["data"]
    assert data["name"] == new_name
    assert data["capabilities"] == ["function_call", "vision"]
    assert data["context_length"] == 32768
    assert data["input_price"] == 0.003
    assert data["output_price"] == 0.006
    assert data["currency"] == "CNY"
    assert data["description"] == "更新后的描述"

    detail = (await client.get(f"/api/v1/models/{model['id']}")).json()["data"]
    assert detail == data


async def test_setting_default_model_unsets_previous_default(client):
    provider = await _create_provider(client)
    first = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")
    second = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    first_resp = await client.put(
        f"/api/v1/models/{first['id']}", json={"is_default": True}
    )
    assert first_resp.json()["data"]["is_default"] is True

    second_resp = await client.put(
        f"/api/v1/models/{second['id']}", json={"is_default": True}
    )
    assert second_resp.json()["data"]["is_default"] is True

    first_after = (await client.get(f"/api/v1/models/{first['id']}")).json()["data"]
    second_after = (await client.get(f"/api/v1/models/{second['id']}")).json()["data"]
    assert first_after["is_default"] is False
    assert second_after["is_default"] is True


async def test_delete_model_removes_it(client):
    provider = await _create_provider(client)
    model = await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    resp = await client.delete(f"/api/v1/models/{model['id']}")

    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 200

    get_resp = await client.get(f"/api/v1/models/{model['id']}")
    assert get_resp.status_code == 404, get_resp.text
    assert get_resp.json()["code"] == 404


async def test_list_models_paginates(client):
    provider = await _create_provider(client)
    created = [
        await _create_model(client, provider["id"], f"模型{i}_{uuid.uuid4().hex[:8]}")
        for i in range(3)
    ]

    first = (
        await client.get(
            "/api/v1/models",
            params={"provider_id": provider["id"], "page": 1, "page_size": 2},
        )
    ).json()["data"]
    second = (
        await client.get(
            "/api/v1/models",
            params={"provider_id": provider["id"], "page": 2, "page_size": 2},
        )
    ).json()["data"]

    assert first["total"] == 3
    assert second["total"] == 3
    assert [item["id"] for item in first["items"]] == [
        created[2]["id"],
        created[1]["id"],
    ]
    assert [item["id"] for item in second["items"]] == [created[0]["id"]]


async def test_list_models_keyword_searches_name_and_model_id(client):
    provider = await _create_provider(client)
    token = uuid.uuid4().hex[:8]
    by_name = await _create_model(client, provider["id"], f"检索_{token}")
    by_model_id = await _create_model(
        client,
        provider["id"],
        f"普通_{uuid.uuid4().hex[:8]}",
        model_id=f"ref-{token}",
    )
    await _create_model(client, provider["id"], f"无关_{uuid.uuid4().hex[:8]}")

    resp = await client.get("/api/v1/models", params={"keyword": token})

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 2
    assert {item["id"] for item in data["items"]} == {by_name["id"], by_model_id["id"]}


async def test_list_models_returns_provider_name(client):
    provider = await _create_provider(client)
    await _create_model(client, provider["id"], f"模型_{uuid.uuid4().hex[:8]}")

    resp = await client.get(
        "/api/v1/models", params={"provider_id": provider["id"]}
    )

    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]["items"]
    assert [item["provider_name"] for item in items] == [provider["name"]]
