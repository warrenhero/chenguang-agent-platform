from functools import lru_cache

from pydantic_settings import BaseSettings


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
