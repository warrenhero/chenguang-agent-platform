from datetime import datetime, timedelta, timezone

import jwt

# openssl 生成随机32位 16进制字符串密钥；CMD命令
# openssl rand -hex 32

SECRET_KEY = "ba875b50832e5f97cd50aabc461ed3eca982a5ddd4c72e43268d701731ff76ce"
ALGORITHM = "HS256"

# 配置OAuth2 Bearer 模式
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 编码JWT，创建一个令牌，登陆成功后，把用户信息传递过来。生成的令牌以后发给前端
# 每次请求都需要携带自己的授权令牌
def encode_jwt(payload: dict) -> str:
    payload_copy = payload.copy()
    # 更新过期时间为30分钟后。注意使用 utc 时间
    payload_copy["exp"] = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload_copy["iat"] = datetime.now(timezone.utc)

    token = jwt.encode(payload_copy, key =SECRET_KEY, algorithm=ALGORITHM)
    return token

# 解码JWT，验证令牌是否合法，是否过期 【从令牌中获取用户信息】
# 返回当时用户的信息（payload中不要放敏感数据）
def verify_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("token已经过期")
    except jwt.InvalidTokenError:
        raise Exception("非法token")
    except Exception as e:
        raise Exception(f"token校验失败: {str(e)}")
