from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# 常见占位密钥片段：出现任意一个都视为未替换
_JWT_SECRET_PLACEHOLDERS = (
    "change-me",
    "changeme",
    "your-secret",
    "secret-key",
    "example",
)


class Settings(BaseSettings):
    APP_NAME: str = "MyApp"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    DB_HOST: str = "192.168.10.102"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    # 不设默认值：缺失时启动即报错，避免静默使用弱密码
    DB_PASSWORD: str = ""
    DB_NAME: str = "chenguang"

    LOG_LEVEL: str = "DEBUG"
    LOG_DIR: str = "logs"

    # Redis
    REDIS_HOST: str = "192.168.10.102"
    REDIS_PORT: int = 6379
    # 不设默认值：缺失时启动即报错，避免静默使用弱密码
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # 无默认值：缺失、过短或仍是占位值时启动直接 ValidationError
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = Field(default=30, ge=1)

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _reject_placeholder_secret(cls, v: str) -> str:
        lowered = v.lower()
        if any(placeholder in lowered for placeholder in _JWT_SECRET_PLACEHOLDERS):
            raise ValueError(
                "JWT_SECRET_KEY 仍是占位值，请执行 openssl rand -hex 32 生成真实密钥"
            )
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def _check_algorithm(cls, v: str) -> str:
        if v not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM 仅支持 HS256/HS384/HS512")
        return v

    # 测试环境可关闭，生产保持开启
    RATE_LIMIT_ENABLED: bool = True

    # 首次启动时创建/提升的超级管理员；留空则跳过
    BOOTSTRAP_SUPERUSER_USERNAME: str = ""
    BOOTSTRAP_SUPERUSER_PASSWORD: str = ""
    BOOTSTRAP_SUPERUSER_EMAIL: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    # 指定环境变量文件；extra="ignore" 允许 .env 同时存放 docker compose 使用的变量
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# 保存到内存缓存中。以后直接获取。这是一种单例的实现
@lru_cache
def get_settings() -> Settings:
    return Settings()
