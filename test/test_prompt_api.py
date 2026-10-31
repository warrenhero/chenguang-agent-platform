import uuid

import pytest
from sqlalchemy import select

from src.core.bootstrap import DEFAULT_PERMISSIONS, apply_rbac_seed
from src.modules.prompt.model import PromptVersion
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
        ("POST", "/api/v1/prompts/1/rollback", {"version": "v1.0"}),
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


async def test_get_missing_prompt_returns_404(client):
    resp = await client.get("/api/v1/prompts/999999")

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == 404


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


async def _create_published_prompt(client, publish_times: int = 1) -> dict:
    create_body = (await client.post("/api/v1/prompts", json=_payload())).json()
    assert create_body["code"] == 200, create_body
    prompt = create_body["data"]
    for i in range(publish_times):
        publish_body = (
            await client.post(
                f"/api/v1/prompts/{prompt['id']}/publish",
                json={"changelog": f"发布 {i + 1}"},
            )
        ).json()
        assert publish_body["code"] == 200, publish_body
    return prompt


async def test_delete_prompt_with_versions_cascades(client, db_session):
    prompt = await _create_published_prompt(client, publish_times=2)

    resp = await client.delete(f"/api/v1/prompts/{prompt['id']}")

    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 200

    result = await db_session.execute(
        select(PromptVersion).where(PromptVersion.prompt_id == prompt["id"])
    )
    assert result.scalars().all() == []

    get_resp = await client.get(f"/api/v1/prompts/{prompt['id']}")
    assert get_resp.status_code == 404, get_resp.text
    assert get_resp.json()["code"] == 404


async def test_list_prompts_with_multiple_versions(client):
    prompt = await _create_published_prompt(client, publish_times=3)

    resp = await client.get("/api/v1/prompts")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    ids = [item["id"] for item in body["data"]["items"]]
    assert prompt["id"] in ids


async def _publish(client, prompt_id: int, changelog: str = "") -> dict:
    resp = await client.post(
        f"/api/v1/prompts/{prompt_id}/publish",
        json={"changelog": changelog},
    )
    return resp.json()


async def _create_prompt(client) -> dict:
    body = (await client.post("/api/v1/prompts", json=_payload())).json()
    assert body["code"] == 200, body
    return body["data"]


async def test_first_publish_is_v1_0(client):
    prompt = await _create_prompt(client)

    body = await _publish(client, prompt["id"])

    assert body["code"] == 200, body
    assert body["data"]["version"] == "v1.0"


async def test_consecutive_publishes_increment_minor(client):
    prompt = await _create_prompt(client)

    versions = [(await _publish(client, prompt["id"]))["data"]["version"] for _ in range(3)]

    assert versions == ["v1.0", "v1.1", "v1.2"]


async def test_republish_after_rollback_does_not_reuse_version(client):
    prompt = await _create_published_prompt(client, publish_times=2)  # v1.0, v1.1

    rollback_resp = await client.post(
        f"/api/v1/prompts/{prompt['id']}/rollback",
        json={"version": "v1.0"},
    )
    assert rollback_resp.json()["data"]["version"] == "v1.0", rollback_resp.text

    body = await _publish(client, prompt["id"])

    assert body["code"] == 200, body
    assert body["data"]["version"] == "v1.2"


async def test_rollback_by_version_restores_snapshot(client):
    prompt = await _create_prompt(client)
    original_content = prompt["content"]
    assert (await _publish(client, prompt["id"]))["data"]["version"] == "v1.0"

    update_body = (
        await client.put(f"/api/v1/prompts/{prompt['id']}", json={"content": "第二版内容"})
    ).json()
    assert update_body["code"] == 200, update_body
    assert (await _publish(client, prompt["id"]))["data"]["version"] == "v1.1"

    resp = await client.post(
        f"/api/v1/prompts/{prompt['id']}/rollback",
        json={"version": "v1.0"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["version"] == "v1.0"
    assert body["data"]["content"] == original_content


async def test_rollback_unknown_version_returns_404(client):
    prompt = await _create_published_prompt(client, publish_times=1)

    resp = await client.post(
        f"/api/v1/prompts/{prompt['id']}/rollback",
        json={"version": "v9.9"},
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == 404


async def test_rollback_rejects_legacy_version_id_payload(client):
    prompt = await _create_published_prompt(client, publish_times=1)

    resp = await client.post(
        f"/api/v1/prompts/{prompt['id']}/rollback",
        json={"version_id": 1},
    )

    assert resp.status_code == 422, resp.text


async def test_version_list_has_unique_versions(client):
    prompt = await _create_published_prompt(client, publish_times=3)

    versions = (await client.get(f"/api/v1/prompts/{prompt['id']}/versions")).json()["data"]
    numbers = [v["version"] for v in versions]

    assert len(numbers) == len(set(numbers))
    assert sorted(numbers) == ["v1.0", "v1.1", "v1.2"]


async def test_create_prompt_rejects_overlong_name(client):
    payload = _payload()
    payload["name"] = "p" * 201

    resp = await client.post("/api/v1/prompts", json=payload)

    assert resp.status_code == 422, resp.text


async def test_create_prompt_accepts_name_at_max_length(client):
    payload = _payload()
    payload["name"] = "p" * 200

    resp = await client.post("/api/v1/prompts", json=payload)

    body = resp.json()
    assert body["code"] == 200, body
    assert body["data"]["name"] == "p" * 200


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", "d" * 501),
        ("category", "c" * 51),
        ("category", ""),
        ("content", ""),
    ],
)
async def test_create_prompt_rejects_invalid_values(client, field, value):
    payload = _payload()
    payload[field] = value

    resp = await client.post("/api/v1/prompts", json=payload)

    assert resp.status_code == 422, resp.text


async def test_create_prompt_rejects_overlong_variable_name(client):
    payload = _payload()
    payload["variables"][0]["name"] = "v" * 101

    resp = await client.post("/api/v1/prompts", json=payload)

    assert resp.status_code == 422, resp.text


async def test_create_prompt_rejects_overlong_variable_description(client):
    payload = _payload()
    payload["variables"][0]["description"] = "d" * 501

    resp = await client.post("/api/v1/prompts", json=payload)

    assert resp.status_code == 422, resp.text


async def test_update_prompt_rejects_overlong_name(client):
    prompt = await _create_prompt(client)

    resp = await client.put(
        f"/api/v1/prompts/{prompt['id']}", json={"name": "p" * 201}
    )

    assert resp.status_code == 422, resp.text


async def test_publish_rejects_overlong_changelog(client):
    prompt = await _create_prompt(client)

    resp = await client.post(
        f"/api/v1/prompts/{prompt['id']}/publish",
        json={"changelog": "c" * 501},
    )

    assert resp.status_code == 422, resp.text


async def test_publish_accepts_changelog_at_max_length(client):
    prompt = await _create_prompt(client)

    resp = await client.post(
        f"/api/v1/prompts/{prompt['id']}/publish",
        json={"changelog": "c" * 500},
    )

    body = resp.json()
    assert body["code"] == 200, body
    assert body["data"]["version"] == "v1.0"


async def _get_versions(client, prompt_id: int) -> list[dict]:
    resp = await client.get(f"/api/v1/prompts/{prompt_id}/versions")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def test_prompt_crud_lifecycle(client):
    payload = _payload()
    create_body = (await client.post("/api/v1/prompts", json=payload)).json()
    assert create_body["code"] == 200, create_body
    created = create_body["data"]
    assert created["name"] == payload["name"]
    assert created["description"] == payload["description"]
    assert created["category"] == payload["category"]
    assert created["tags"] == payload["tags"]
    assert created["content"] == payload["content"]
    assert created["variables"] == payload["variables"]
    assert created["version"] == "v0.1"
    assert created["status"] == "draft"

    detail = (await client.get(f"/api/v1/prompts/{created['id']}")).json()["data"]
    assert detail == created

    new_tags = ["updated", "crud"]
    update_body = (
        await client.put(
            f"/api/v1/prompts/{created['id']}",
            json={
                "name": f"更新_{uuid.uuid4().hex[:8]}",
                "description": "更新后的描述",
                "category": "updated",
                "tags": new_tags,
                "content": "更新后的内容 {name}",
            },
        )
    ).json()
    assert update_body["code"] == 200, update_body
    updated = update_body["data"]
    assert updated["description"] == "更新后的描述"
    assert updated["category"] == "updated"
    assert updated["tags"] == new_tags
    assert updated["content"] == "更新后的内容 {name}"

    updated_detail = (
        await client.get(f"/api/v1/prompts/{created['id']}")
    ).json()["data"]
    assert updated_detail == updated

    delete_resp = await client.delete(f"/api/v1/prompts/{created['id']}")
    assert delete_resp.status_code == 200, delete_resp.text
    assert delete_resp.json()["code"] == 200

    listed = (
        await client.get("/api/v1/prompts", params={"keyword": updated["name"]})
    ).json()["data"]
    assert listed["total"] == 0
    assert listed["items"] == []


async def test_list_prompts_paginates(client):
    token = uuid.uuid4().hex[:8]
    created = []
    for i in range(3):
        payload = _payload()
        payload["name"] = f"分页_{i}_{token}"
        body = (await client.post("/api/v1/prompts", json=payload)).json()
        assert body["code"] == 200, body
        created.append(body["data"])

    first = (
        await client.get(
            "/api/v1/prompts",
            params={"keyword": token, "page": 1, "page_size": 2},
        )
    ).json()["data"]
    second = (
        await client.get(
            "/api/v1/prompts",
            params={"keyword": token, "page": 2, "page_size": 2},
        )
    ).json()["data"]

    assert first["total"] == 3
    assert second["total"] == 3
    assert [item["id"] for item in first["items"]] == [
        created[2]["id"],
        created[1]["id"],
    ]
    assert [item["id"] for item in second["items"]] == [created[0]["id"]]


async def test_list_prompts_keyword_matches_name_and_category(client):
    token = uuid.uuid4().hex[:8]
    payload_name = _payload()
    payload_name["name"] = f"关键词_{token}"
    by_name = (await client.post("/api/v1/prompts", json=payload_name)).json()["data"]

    payload_category = _payload()
    payload_category["category"] = f"cat_{token}"
    by_category = (
        await client.post("/api/v1/prompts", json=payload_category)
    ).json()["data"]

    await client.post("/api/v1/prompts", json=_payload())

    resp = await client.get("/api/v1/prompts", params={"keyword": token})

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 2
    assert {item["id"] for item in data["items"]} == {
        by_name["id"],
        by_category["id"],
    }


async def test_prompt_tags_and_variables_round_trip(client):
    payload = _payload()
    payload["tags"] = ["a", "b", "中文标签"]
    payload["variables"] = [
        {
            "name": "name",
            "type": "string",
            "description": "",
            "default_value": "世界",
            "required": True,
        },
        {
            "name": "count",
            "type": "number",
            "description": "次数",
            "default_value": None,
            "required": False,
        },
    ]
    created = (await client.post("/api/v1/prompts", json=payload)).json()["data"]

    detail = (await client.get(f"/api/v1/prompts/{created['id']}")).json()["data"]
    assert detail["tags"] == payload["tags"]
    assert detail["variables"] == payload["variables"]

    new_tags = ["c"]
    new_variables = [
        {
            "name": "topic",
            "type": "text",
            "description": "主题",
            "default_value": None,
            "required": True,
        }
    ]
    update_body = (
        await client.put(
            f"/api/v1/prompts/{created['id']}",
            json={"tags": new_tags, "variables": new_variables},
        )
    ).json()
    assert update_body["code"] == 200, update_body

    updated_detail = (
        await client.get(f"/api/v1/prompts/{created['id']}")
    ).json()["data"]
    assert updated_detail["tags"] == new_tags
    assert updated_detail["variables"] == new_variables


async def test_publish_snapshots_content_until_next_publish(client):
    prompt = await _create_prompt(client)
    published_content = "发布时的内容"
    update_body = (
        await client.put(
            f"/api/v1/prompts/{prompt['id']}", json={"content": published_content}
        )
    ).json()
    assert update_body["code"] == 200, update_body
    assert (await _publish(client, prompt["id"]))["data"]["version"] == "v1.0"

    later_body = (
        await client.put(
            f"/api/v1/prompts/{prompt['id']}", json={"content": "发布之后又改的内容"}
        )
    ).json()
    assert later_body["code"] == 200, later_body

    versions = await _get_versions(client, prompt["id"])
    snapshot = next(v for v in versions if v["version"] == "v1.0")
    assert snapshot["content"] == published_content

    detail = (await client.get(f"/api/v1/prompts/{prompt['id']}")).json()["data"]
    assert detail["content"] == "发布之后又改的内容"


async def test_version_list_is_newest_first(client):
    prompt = await _create_published_prompt(client, publish_times=3)

    versions = await _get_versions(client, prompt["id"])

    assert [v["version"] for v in versions] == ["v1.2", "v1.1", "v1.0"]


async def test_publish_keeps_single_current_version(client):
    prompt = await _create_published_prompt(client, publish_times=3)

    versions = await _get_versions(client, prompt["id"])
    current = [v for v in versions if v["is_current"]]

    assert len(current) == 1
    assert current[0]["version"] == "v1.2"


async def test_rollback_moves_current_marker_to_target_version(client):
    prompt = await _create_published_prompt(client, publish_times=3)

    rollback_body = (
        await client.post(
            f"/api/v1/prompts/{prompt['id']}/rollback",
            json={"version": "v1.1"},
        )
    ).json()
    assert rollback_body["code"] == 200, rollback_body
    assert rollback_body["data"]["version"] == "v1.1"

    versions = await _get_versions(client, prompt["id"])
    current = [v for v in versions if v["is_current"]]
    assert len(current) == 1
    assert current[0]["version"] == "v1.1"
