import bcrypt
from starlette.concurrency import run_in_threadpool


# 对密码进行哈希处理，使用 bcrypt 算法
def hash_password(plain_password: str) -> str:
    """明文密码 → bcrypt 哈希"""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),   # 生成随机盐
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码是否匹配哈希"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # 超 72 字节、哈希格式损坏都按“不匹配”处理，绝不让它变成 500
        return False

async def hash_password_async(plain_password: str) -> str:
    return await run_in_threadpool(hash_password, plain_password)

async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    return await run_in_threadpool(verify_password, plain_password, hashed_password)