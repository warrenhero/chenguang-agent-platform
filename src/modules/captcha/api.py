
import random
import string

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis

from src.core.base_schema import ResponseSchema
from src.core.exceptions import BizException
from src.core.ratelimit import hit
from src.infra.redis_cache import get_redis
from src.modules.captcha.schema import CaptchaRead, VerifyCaptchaRequest
from src.modules.captcha.service import CaptchaService

router = APIRouter(prefix="/captcha", tags=["Captcha"])


def get_captcha_service(redis: Redis = Depends(get_redis)) -> CaptchaService:
    """获取验证码服务"""
    return CaptchaService(redis)

@router.get("", response_model=ResponseSchema[CaptchaRead], summary="获取验证码")
async def get_captcha(
    request: Request,
    redis: Redis = Depends(get_redis),
    svc: CaptchaService = Depends(get_captcha_service),
) :
    """获取图片验证码，返回 key 和 base64 图片"""
    client_ip = request.client.host if request.client else "unknown"
    await hit(redis, f"rl:captcha:ip:{client_ip}", 10, 60)
    captcha = await svc.create_captcha()
    return ResponseSchema[CaptchaRead](data=captcha)

@router.post("/verify", response_model=ResponseSchema[bool], summary="验证验证码")
async def verify_captcha(
    request: VerifyCaptchaRequest,
    svc: CaptchaService = Depends(get_captcha_service),
) -> ResponseSchema[bool]:
    """验证验证码"""
    is_valid = await svc.verify_captcha(request)
    if not is_valid:
        raise BizException(message="验证码错误或已过期")
    return ResponseSchema[bool](data=True)
