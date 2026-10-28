
from pydantic import BaseModel


class CaptchaRead(BaseModel):
    """验证码响应模型"""
    key: str
    images: str     # data:image/png;base64,...

class VerifyCaptchaRequest(BaseModel):
    """验证码验证请求模型"""
    key: str
    code: str