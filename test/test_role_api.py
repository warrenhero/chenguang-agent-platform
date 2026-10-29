import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_role(client):
    code = f"admin_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/roles",
        json={"code": code, "name": "管理员", "description": "系统管理员"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert isinstance(data["id"], int)
    assert data["code"] == code
    assert data["name"] == "管理员"
    assert data["description"] == "系统管理员"
    assert data["permissions"] == []


async def test_create_role_duplicate_code(client, make_role):
    await make_role(code="dup:role")

    resp = await client.post(
        "/api/v1/roles",
        json={"code": "dup:role", "name": "重复角色"},
    )

    body = resp.json()
    assert body["code"] == 400
    assert "已经存在" in body["message"]
    assert body["data"] is None


async def test_get_role(client, make_role):
    role = await make_role(name="详情角色")

    resp = await client.get(f"/api/v1/roles/{role['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["id"] == role["id"]
    assert body["data"]["name"] == "详情角色"
    assert body["data"]["permissions"] == []


async def test_get_role_not_found(client):
    resp = await client.get("/api/v1/roles/999999999")

    body = resp.json()
    assert body["code"] == 404
    assert "不存在" in body["message"]


async def test_list_roles(client, make_role):
    first = await make_role(name="列表角色A")
    second = await make_role(name="列表角色B")

    resp = await client.get("/api/v1/roles")

    body = resp.json()
    assert body["code"] == 200
    ids = [item["id"] for item in body["data"]]
    assert first["id"] in ids
    assert second["id"] in ids


async def test_update_role(client, make_role):
    role = await make_role(name="旧名称", description="旧描述")

    resp = await client.put(
        f"/api/v1/roles/{role['id']}",
        json={"name": "新名称", "description": "新描述"},
    )

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["name"] == "新名称"
    assert body["data"]["description"] == "新描述"
    assert body["data"]["code"] == role["code"]


async def test_update_role_partial_keeps_other_fields(client, make_role):
    role = await make_role(name="旧名称", description="保留描述")

    resp = await client.put(
        f"/api/v1/roles/{role['id']}",
        json={"name": "只改名称"},
    )

    body = resp.json()
    assert body["data"]["name"] == "只改名称"
    assert body["data"]["description"] == "保留描述"


async def test_update_role_not_found(client):
    resp = await client.put("/api/v1/roles/999999999", json={"name": "不存在"})

    assert resp.json()["code"] == 404


async def test_delete_role(client, make_role):
    role = await make_role()

    resp = await client.delete(f"/api/v1/roles/{role['id']}")

    body = resp.json()
    assert body["code"] == 200
    assert body["data"] is None

    resp = await client.get(f"/api/v1/roles/{role['id']}")
    assert resp.json()["code"] == 404


async def test_delete_role_not_found(client):
    resp = await client.delete("/api/v1/roles/999999999")

    assert resp.json()["code"] == 404


async def test_assign_permissions(client, make_role, make_permission):
    role = await make_role()
    first = await make_permission()
    second = await make_permission()

    resp = await client.put(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permission_ids": [first["id"], second["id"]]},
    )

    body = resp.json()
    assert body["code"] == 200
    assert sorted(p["id"] for p in body["data"]["permissions"]) == sorted(
        [first["id"], second["id"]]
    )

    # 详情接口应能读到已分配的权限
    resp = await client.get(f"/api/v1/roles/{role['id']}")
    ids = [p["id"] for p in resp.json()["data"]["permissions"]]
    assert sorted(ids) == sorted([first["id"], second["id"]])


async def test_assign_permissions_replaces_previous(client, make_role, make_permission):
    role = await make_role()
    first = await make_permission()
    second = await make_permission()

    await client.put(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permission_ids": [first["id"]]},
    )
    resp = await client.put(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permission_ids": [second["id"]]},
    )

    ids = [p["id"] for p in resp.json()["data"]["permissions"]]
    assert ids == [second["id"]]


async def test_assign_permissions_with_invalid_id(client, make_role):
    role = await make_role()

    resp = await client.put(
        f"/api/v1/roles/{role['id']}/permissions",
        json={"permission_ids": [999999999]},
    )

    body = resp.json()
    assert body["code"] == 400
    assert "无效 ID" in body["message"]


async def test_assign_permissions_role_not_found(client, make_permission):
    permission = await make_permission()

    resp = await client.put(
        "/api/v1/roles/999999999/permissions",
        json={"permission_ids": [permission["id"]]},
    )

    assert resp.json()["code"] == 404


async def test_search_roles(client, make_role):
    keyword = f"search{uuid.uuid4().hex[:8]}"
    first = await make_role(code=f"role:{keyword}:1")
    second = await make_role(code=f"role:{keyword}:2")
    await make_role()

    resp = await client.get(
        "/api/v1/roles/search",
        params={"page": 1, "page_size": 10, "keyword": keyword},
    )

    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert {r["id"] for r in data["items"]} == {first["id"], second["id"]}
    # 角色搜索结果应返回角色结构（含权限列表）
    assert "permissions" in data["items"][0]
