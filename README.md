# chenguang-agent-platform

## 基础环境

项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境与依赖，Python 版本固定为 3.13（见 `.python-version`）。

### 安装 uv

```bash
# 官方脚本（Windows PowerShell）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 国内镜像（pip）
pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 创建虚拟环境

```bash
uv venv
```

### 激活虚拟环境

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

### 安装依赖

```bash
uv sync
```

## 环境变量

所有密码与连接信息统一放在 `.env`（已被 `.gitignore` 忽略，不会提交）。

```bash
# 首次初始化（本地开发：放在项目根，供应用读取）
cp .env.example .env
# 然后编辑 .env 填入真实密码
```

`src/core/config.py` 中 `DB_PASSWORD` 无默认值，缺失时启动即报错，不会静默使用弱密码。

远程部署时把 `.env` 与 compose 文件放在同一目录（`docker/`），同步后执行 `chmod 600 docker/.env`。

## 启动依赖服务（Docker）

```bash
# 必须在仓库根目录执行
# --project-directory .  把相对路径基准从 docker/ 改回项目根，
#                        使 ./docker/mysql/data 落到 <项目根>/docker/mysql/data
# --env-file docker/.env .env 与 compose 同目录，须显式指定
#                        （--project-directory . 会让默认查找位置变成项目根）
docker compose --project-directory . -f docker/docker-compose.yaml --env-file docker/.env up -d
```

- compose 中所有密码使用 `${VAR:?msg}` 插值，变量缺失时直接启动失败。
- 端口绑定 `0.0.0.0`，供远程应用主机连接；**务必使用强密码**，否则同网段任何主机都可直连 MySQL / Redis。
- 数据卷统一放在项目根的 `docker/` 下：`docker/mysql/data`、`docker/redis/data`、`docker/minio/data`。

