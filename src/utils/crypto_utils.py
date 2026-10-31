import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from src.core.config import get_settings


def _fernet() -> Fernet:
    """用 JWT 密钥派生 Fernet 密钥，避免新增必填环境变量。"""
    digest = hashlib.sha256(get_settings().JWT_SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str | None) -> str | None:
    """加密敏感字符串；None 原样返回。"""
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str | None) -> str | None:
    """解密敏感字符串；兼容历史上已明文写入的数据。"""
    if ciphertext is None:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ciphertext
