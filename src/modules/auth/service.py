from datetime import datetime

from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BizException
from src.core.ratelimit import check, hit, record_failure, reset
from src.modules.auth.schema import LoginRequest, TokenResponse
from src.modules.captcha.schema import VerifyCaptchaRequest
from src.modules.captcha.service import CaptchaService
from src.modules.user.repository import UserRepository
from src.utils.jwt_utils import encode_jwt
from src.utils.password_utils import verify_password_async


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.captcha_svc = CaptchaService(redis)
        self.user_repo = UserRepository(db)

    async def login(self, data: LoginRequest, client_ip: str = "unknown") -> TokenResponse:
        # 1. 验证验证码
        captcha_verify_req = VerifyCaptchaRequest(
            key=data.captcha_key, 
            code=data.captcha_code,
        )
        await self.captcha_svc.verify_captcha(captcha_verify_req)

        # 验证码通过后再按 IP 计数，避免刷爆计数锁死同一出口 IP 的其他用户
        await hit(self.redis, f"rl:login:ip:{client_ip}", 20, 60)

        # 账号维度：先检查失败次数，达到上限直接拒绝，不再执行密码校验
        account_key = f"rl:login:user:{data.username}"
        await check(self.redis, account_key, 5)

        # 走到这说明校验通过
        # 2. 查找用户
        user = await self.user_repo.get_by_username(data.username)
        if not user:
            await record_failure(self.redis, account_key, 900)
            raise BizException(code=400, message="用户名或密码错误")

        # 3. 校验密码
        if not await verify_password_async(data.password, user.hashed_password):
            await record_failure(self.redis, account_key, 900)
            raise BizException(code=400, message="用户名或密码错误")

        # 4. 检查账号状态
        if not user.is_active:
            raise BizException(code=400, message="账号已被禁用")

        # 登录成功，解除该账号的失败计数
        await reset(self.redis, account_key)

        # 5. 更新最后登录时间
        user.last_login = datetime.now()
        await self.db.flush()

        # 6. 签发 JWT [强制必须 sub 是 str 类型]
        token = encode_jwt({"sub": str(user.id), "username": user.username, "email": user.email})
        # token 属凭据，日志只保留前缀，完整值仅返回给客户端
        logger.info(f"用户 {user.username} 登录成功，签发 JWT: {token[:12]}***")

        return TokenResponse(access_token=token)
