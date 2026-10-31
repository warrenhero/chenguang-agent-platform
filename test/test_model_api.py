import uuid

import pytest

from src.core.bootstrap import DEFAULT_PERMISSIONS, apply_rbac_seed
from src.modules.user.model import User
from src.utils.jwt_utils import encode_jwt

pytestmark = pytest.mark.asyncio


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
