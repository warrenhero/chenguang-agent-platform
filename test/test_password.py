import pytest

from src.utils.password_utils import hash_password, verify_password


@pytest.mark.parametrize("password", ["123456", "password123", "Abc@123"])
def test_password_utils(password: str):
    # 即使同一个字符串，每次生成的哈希值也应该不同，因为 bcrypt 会使用随机盐，防止彩虹表攻击
    hashed_password = hash_password(password)
    print(f"原密码：{password} 加密后: {hashed_password}")
    assert verify_password(password, hashed_password) is True
    assert verify_password("wrong_password", hashed_password) is False
