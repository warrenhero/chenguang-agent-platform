import uuid

import pytest

from src.utils.jwt_utils import encode_jwt

pytestmark = pytest.mark.asyncio


async def test_create_user(client):
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": f"alice_{suffix}",
            "email": f"alice_{suffix}@example.com",
            "password": "Abc@123456",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert isinstance(data["id"], int)
    assert data["username"] == f"alice_{suffix}"
    assert data["email"] == f"alice_{suffix}@example.com"
    assert data["is_active"] is True
    # 响应中不能泄露密码哈希
    assert "hashed_password" not in data
    assert "password" not in data


async def test_create_user_duplicate_username(client, make_user):
    user = await make_user()

    resp = await client.post(
        "/api/v1/users",
        json={
            "username": user["username"],
            "email": f"another_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Abc@123456",
        },
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "用户名已存在"


async def test_create_user_duplicate_email(client, make_user):
    user = await make_user()

    resp = await client.post(
        "/api/v1/users",
        json={
            "username": f"another_{uuid.uuid4().hex[:8]}",
            "email": user["email"],
            "password": "Abc@123456",
        },
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "邮箱已存在"


async def test_get_user(client, make_user):
    user = await make_user()

    resp = await client.get(f"/api/v1/users/{user['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == user["id"]
    assert body["data"]["username"] == user["username"]


async def test_get_user_not_found(client):
    resp = await client.get("/api/v1/users/999999999")

    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "用户不存在"


async def test_list_users(client, make_user):
    first = await make_user()
    second = await make_user()

    resp = await client.get("/api/v1/users")

    body = resp.json()
    assert body["code"] == 200
    ids = [item["id"] for item in body["data"]]
    assert first["id"] in ids
    assert second["id"] in ids


async def test_assign_roles_to_user(client, make_user, make_role):
    user = await make_user()
    first = await make_role()
    second = await make_role()

    resp = await client.put(
        f"/api/v1/users/{user['id']}/roles",
        json={"role_ids": [first["id"], second["id"]]},
    )

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == user["id"]

    # 通过角色列表接口校验分配结果
    resp = await client.get(f"/api/v1/users/{user['id']}/roles")
    body = resp.json()
    assert body["code"] == 200
    role_ids = [r["id"] for r in body["data"][0]["roles"]]
    assert sorted(role_ids) == sorted([first["id"], second["id"]])


async def test_assign_roles_replaces_previous(client, make_user, make_role):
    user = await make_user()
    first = await make_role()
    second = await make_role()

    await client.put(
        f"/api/v1/users/{user['id']}/roles",
        json={"role_ids": [first["id"]]},
    )
    await client.put(
        f"/api/v1/users/{user['id']}/roles",
        json={"role_ids": [second["id"]]},
    )

    resp = await client.get(f"/api/v1/users/{user['id']}/roles")
    role_ids = [r["id"] for r in resp.json()["data"][0]["roles"]]
    assert role_ids == [second["id"]]


async def test_assign_roles_with_invalid_id(client, make_user):
    user = await make_user()

    resp = await client.put(
        f"/api/v1/users/{user['id']}/roles",
        json={"role_ids": [999999999]},
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "角色不存在"


async def test_assign_roles_user_not_found(client, make_role):
    role = await make_role()

    resp = await client.put(
        "/api/v1/users/999999999/roles",
        json={"role_ids": [role["id"]]},
    )

    assert resp.json()["code"] == 404


async def test_delete_user(client, make_user):
    user = await make_user()

    resp = await client.delete(f"/api/v1/users/{user['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"] is None

    # 删除后不可再查询
    resp = await client.get(f"/api/v1/users/{user['id']}")
    assert resp.json()["code"] == 404


async def test_delete_user_not_found(client):
    resp = await client.delete("/api/v1/users/999999999")

    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "用户不存在"


async def test_get_me_with_token(client, make_user):
    user = await make_user()
    token = encode_jwt({"sub": str(user["id"]), "username": user["username"]})

    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == user["id"]


async def test_get_me_without_token(client):
    resp = await client.get("/api/v1/users/me")

    assert resp.status_code == 401


async def test_get_me_with_invalid_token(client):
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    body = resp.json()
    assert body["code"] == 401


async def test_get_user_roles_empty(client, make_user):
    user = await make_user()

    resp = await client.get(f"/api/v1/users/{user['id']}/roles")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"][0]["id"] == user["id"]
    assert body["data"][0]["roles"] == []


async def test_get_user_roles_not_found(client):
    resp = await client.get("/api/v1/users/999999999/roles")

    assert resp.json()["code"] == 404


async def test_search_users(client, make_user):
    keyword = f"search{uuid.uuid4().hex[:8]}"
    first = await make_user(
        username=f"{keyword}_1", email=f"{keyword}_1@example.com"
    )
    second = await make_user(
        username=f"{keyword}_2", email=f"{keyword}_2@example.com"
    )

    resp = await client.get(
        "/api/v1/users/search",
        params={"page": 1, "page_size": 10, "keyword": keyword},
    )

    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert {u["id"] for u in data["items"]} == {first["id"], second["id"]}
    # 用户搜索结果应返回用户结构（不含权限字段等）
    assert "username" in data["items"][0]
