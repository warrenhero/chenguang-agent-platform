import base64
import random
import string
import uuid

from captcha.image import ImageCaptcha
from redis.asyncio import Redis

from src.core.exceptions import BizException
from src.modules.captcha.schema import CaptchaRead, VerifyCaptchaRequest


class CaptchaService:
    # 验证码过期时间（秒）
    CAPTCHA_EXPIRE: int = 300
    # 验证码键前缀
    CAPTCHA_KEY_PREFIX: str = "captcha:"

    def __init__(self, redis: Redis):
        self.redis = redis

    def _random_code(self, length: int = 4) -> str:
        # 生成随机字母+数字验证码
        chars = string.ascii_uppercase + string.digits
        # 去掉容易混淆的字符
        chars = (
            chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
        )
        return "".join(random.choices(chars, k=length))

    # 创建验证码
    async def create_captcha(self) -> CaptchaRead:
        # 1.得到4位随机验证码
        code = self._random_code()
        # 2.验证码的唯一ID
        captcha_id: str = str(uuid.uuid4())
        # 3.生成验证码键：captcha:${captcha_id}
        key: str = f"{self.CAPTCHA_KEY_PREFIX}{captcha_id}"
        # 4.将验证码存储到Redis中
        await self.redis.set(key, code, ex=self.CAPTCHA_EXPIRE)

        # ======以上该服务端保存验证码到redis完成======
        # ======生成验证码图片，并编码为base64字符串======
        # 5.生成验证码图片
        image_captcha = ImageCaptcha(width=162, height=54)
        image_data = image_captcha.generate(code)
        b64 = base64.b64encode(image_data.read()).decode()
        # 6.返回验证码响应模型
        return CaptchaRead(key=captcha_id, images=f"data:image/png;base64,{b64}")

    # 验证验证码
    async def verify_captcha(self, captcha: VerifyCaptchaRequest) -> bool:
        # 1.生成验证码键：captcha:${captcha_id}
        key: str = f"{self.CAPTCHA_KEY_PREFIX}{captcha.key}"
        # 2.从Redis中获取验证码
        stored_code: str | None = await self.redis.get(key)
        if stored_code is None:
            raise BizException(message="验证码不存在或已过期")
        # 3.删除Redis中的验证码，防暴力重试
        await self.redis.delete(key)
        # 4.比较验证码是否匹配（忽略大小写）
        if stored_code.lower() != captcha.code.lower():
            raise BizException(message="验证码错误")
        return True
