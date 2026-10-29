import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_permission(client):
    resp = await client.post(
        "/api/v1/permissions",
        json={"code": "user:read", "name": "用户读取", "description": "读取用户信息"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    data = body["data"]
    assert isinstance(data["id"], int)
    assert data["code"] == "user:read"
    assert data["name"] == "用户读取"
    assert data["description"] == "读取用户信息"


async def test_create_permission_duplicate_code(client, make_permission):
    permission = await make_permission(code="dup:code")

    resp = await client.post(
        "/api/v1/permissions",
        json={"code": "dup:code", "name": "重复权限"},
    )

    body = resp.json()
    assert body["code"] == 400
    assert "已" in body["message"]
    assert body["data"] is None
    assert permission["code"] == "dup:code"


async def test_get_permission(client, make_permission):
    permission = await make_permission(name="详情权限")

    resp = await client.get(f"/api/v1/permissions/{permission['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == permission["id"]
    assert body["data"]["name"] == "详情权限"


async def test_get_permission_not_found(client):
    resp = await client.get("/api/v1/permissions/999999999")

    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "权限不存在"


async def test_list_permissions(client, make_permission):
    first = await make_permission(name="列表权限A")
    second = await make_permission(name="列表权限B")

    resp = await client.get("/api/v1/permissions")

    body = resp.json()
    assert body["code"] == 200
    ids = [item["id"] for item in body["data"]]
    assert first["id"] in ids
    assert second["id"] in ids


async def test_update_permission(client, make_permission):
    permission = await make_permission(name="旧名称", description="旧描述")

    resp = await client.put(
        f"/api/v1/permissions/{permission['id']}",
        json={"name": "新名称", "description": "新描述"},
    )

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["name"] == "新名称"
    assert body["data"]["description"] == "新描述"
    assert body["data"]["code"] == permission["code"]


async def test_update_permission_partial_keeps_other_fields(client, make_permission):
    permission = await make_permission(name="旧名称", description="保留描述")

    resp = await client.put(
        f"/api/v1/permissions/{permission['id']}",
        json={"name": "只改名称"},
    )

    body = resp.json()
    assert body["data"]["name"] == "只改名称"
    assert body["data"]["description"] == "保留描述"


async def test_update_permission_not_found(client):
    resp = await client.put(
        "/api/v1/permissions/999999999",
        json={"name": "不存在"},
    )

    assert resp.json()["code"] == 404


async def test_delete_permission(client, make_permission):
    permission = await make_permission()

    resp = await client.delete(f"/api/v1/permissions/{permission['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"] is None

    # 删除后再查应返回 404
    resp = await client.get(f"/api/v1/permissions/{permission['id']}")
    assert resp.json()["code"] == 404


async def test_delete_permission_not_found(client):
    resp = await client.delete("/api/v1/permissions/999999999")

    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "权限不存在"


async def test_search_permissions(client, make_permission):
    keyword = f"search{uuid.uuid4().hex[:8]}"
    first = await make_permission(code=f"perm:{keyword}:1")
    second = await make_permission(code=f"perm:{keyword}:2")
    await make_permission()

    resp = await client.get(
        "/api/v1/permissions/search",
        params={"page": 1, "page_size": 1, "keyword": keyword},
    )

    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["items"]) == 1

    resp = await client.get(
        "/api/v1/permissions/search",
        params={"page": 2, "page_size": 1, "keyword": keyword},
    )
    second_page = resp.json()["data"]
    assert second_page["page"] == 2
    assert len(second_page["items"]) == 1

    ids = {data["items"][0]["id"], second_page["items"][0]["id"]}
    assert ids == {first["id"], second["id"]}


async def test_search_permissions_invalid_page(client):
    resp = await client.get("/api/v1/permissions/search", params={"page": 0})

    assert resp.status_code == 422
