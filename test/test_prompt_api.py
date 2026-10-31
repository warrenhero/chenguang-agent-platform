import uuid

import pytest

from src.core.bootstrap import DEFAULT_PERMISSIONS, apply_rbac_seed
from src.utils.jwt_utils import verify_jwt

pytestmark = pytest.mark.asyncio


def _payload() -> dict:
    return {
        "name": f"prompt_{uuid.uuid4().hex[:8]}",
        "description": "测试 Prompt",
        "category": "general",
        "tags": ["test"],
        "content": "你好，{name}",
        "variables": [
            {
                "name": "name",
                "type": "string",
                "description": "用户名",
                "default_value": None,
                "required": True,
            }
        ],
    }


def _username(headers: dict) -> str:
    token = headers["Authorization"].split(" ", 1)[1]
    return verify_jwt(token)["username"]


async def test_prompt_endpoints_require_auth(anon_client):
    payload = _payload()
    cases = [
        ("POST", "/api/v1/prompts", payload),
        ("GET", "/api/v1/prompts", None),
        ("GET", "/api/v1/prompts/1", None),
        ("PUT", "/api/v1/prompts/1", {"description": "x"}),
        ("DELETE", "/api/v1/prompts/1", None),
        ("POST", "/api/v1/prompts/1/publish", {"changelog": "x"}),
        ("GET", "/api/v1/prompts/1/versions", None),
        ("POST", "/api/v1/prompts/1/rollback", {"version_id": 1}),
    ]

    for method, path, json in cases:
        resp = await anon_client.request(method, path, json=json)
        assert resp.status_code == 401, (method, path, resp.status_code, resp.text)


async def test_bootstrap_seeds_prompt_permissions(db_session):
    await apply_rbac_seed(db_session)

    codes = {code for code, _, _ in DEFAULT_PERMISSIONS}
    assert {
        "prompt:read",
        "prompt:create",
        "prompt:update",
        "prompt:delete",
    } <= codes


async def test_prompt_audit_fields_record_superuser(client, superuser_headers):
    username = _username(superuser_headers)

    create_resp = await client.post("/api/v1/prompts", json=_payload())
    create_body = create_resp.json()
    assert create_body["code"] == 200, create_body
    created = create_body["data"]
    assert created["created_by"] == username

    publish_resp = await client.post(
        f"/api/v1/prompts/{created['id']}/publish",
        json={"changelog": "首次发布"},
    )
    publish_body = publish_resp.json()
    assert publish_body["code"] == 200, publish_body

    versions_resp = await client.get(f"/api/v1/prompts/{created['id']}/versions")
    versions = versions_resp.json()["data"]
    current = next(v for v in versions if v["is_current"])
    assert current["published_by"] == username
