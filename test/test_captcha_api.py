import pytest

pytestmark = pytest.mark.asyncio


async def test_get_captcha(client, redis_client):
    resp = await client.get("/api/v1/captcha")

    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["key"]
    assert data["images"].startswith("data:image/png;base64,")

    # 验证码已写入 Redis，用例结束前清理
    stored = await redis_client.get(f"captcha:{data['key']}")
    assert stored is not None
    await redis_client.delete(f"captcha:{data['key']}")


async def test_verify_captcha_success(client, make_captcha):
    captcha = await make_captcha(code="AB12")

    resp = await client.post(
        "/api/v1/captcha/verify",
        json={"key": captcha["key"], "code": "ab12"},
    )

    body = resp.json()
    assert body["code"] == 200
    assert body["data"] is True


async def test_verify_captcha_wrong_code(client, make_captcha):
    captcha = await make_captcha(code="AB12")

    resp = await client.post(
        "/api/v1/captcha/verify",
        json={"key": captcha["key"], "code": "ZZZZ"},
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "验证码错误"


async def test_verify_captcha_not_found(client):
    resp = await client.post(
        "/api/v1/captcha/verify",
        json={"key": "not-exist-key", "code": "AB12"},
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "验证码不存在或已过期"
