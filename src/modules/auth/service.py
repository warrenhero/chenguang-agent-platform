from datetime import datetime

from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BizException
from src.modules.auth.schema import LoginRequest, TokenResponse
from src.modules.captcha.schema import VerifyCaptchaRequest
from src.modules.captcha.service import CaptchaService
from src.modules.user.repository import UserRepository
from src.utils.jwt_utils import encode_jwt
from src.utils.password_utils import verify_password


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.captcha_svc = CaptchaService(redis)
        self.user_repo = UserRepository(db)

    async def login(self, data: LoginRequest) -> TokenResponse:
        # 1. 验证验证码
        captcha_verify_req = VerifyCaptchaRequest(
            key=data.captcha_key, 
            code=data.captcha_code,
        )
        await self.captcha_svc.verify_captcha(captcha_verify_req)

        # 走到这说明校验通过
        # 2. 查找用户
        user = await self.user_repo.get_by_username(data.username)
        if not user:
            raise BizException(code=400, message="用户不存在")

        # 3. 校验密码
        if not verify_password(data.password, user.hashed_password):
            raise BizException(code=400, message="密码错误")

        # 4. 检查账号状态
        if not user.is_active:
            raise BizException(code=400, message="账号已被禁用")

        # 5. 更新最后登录时间
        user.last_login = datetime.now()
        await self.db.flush()

        # 6. 签发 JWT [强制必须 sub 是 str 类型]
        token = encode_jwt({"sub": str(user.id), "username": user.username, "email": user.email})
        logger.info(f"用户 {user.username} 登录成功，签发 JWT: {token}")

        return TokenResponse(access_token=token)
