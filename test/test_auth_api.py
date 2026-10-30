import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_login_success(client, make_user, make_captcha):
    user = await make_user(password="Abc@123456")
    captcha = await make_captcha(code="AB12")

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": user["username"],
            "password": "Abc@123456",
            "captcha_key": captcha["key"],
            "captcha_code": "ab12",
        },
    )

    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["access_token"]
    assert body["data"]["token_type"] == "bearer"


async def test_login_wrong_password(client, make_user, make_captcha):
    user = await make_user(password="Abc@123456")
    captcha = await make_captcha()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": user["username"],
            "password": "Wrong@123456",
            "captcha_key": captcha["key"],
            "captcha_code": captcha["code"],
        },
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "用户名或密码错误"


async def test_login_user_not_found(client, make_captcha):
    captcha = await make_captcha()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": f"ghost_{uuid.uuid4().hex[:8]}",
            "password": "Abc@123456",
            "captcha_key": captcha["key"],
            "captcha_code": captcha["code"],
        },
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "用户名或密码错误"


async def test_login_wrong_captcha(client, make_user, make_captcha):
    user = await make_user(password="Abc@123456")
    captcha = await make_captcha(code="AB12")

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": user["username"],
            "password": "Abc@123456",
            "captcha_key": captcha["key"],
            "captcha_code": "ZZZZ",
        },
    )

    body = resp.json()
    assert body["code"] == 400
    assert body["message"] == "验证码错误"
