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

## 数据库迁移（Alembic）

改完模型后，在**仓库根目录**、已激活虚拟环境的终端中执行：

```bash
# 1. 根据模型变更自动生成迁移脚本（脚本落在 alembic/versions/）
alembic revision --autogenerate -m "add user table"

# 2. 应用到数据库
alembic upgrade head
```

- 连接串由 `alembic/env.py` 从 `src/core/config.py` 读取，自动拼装 `DATABASE_URL`，无需改 `alembic.ini`。
- 新增模块的 model 必须先在 `alembic/env.py` 中 import（如 `import src.modules.user.model`），否则 autogenerate 发现不了新表。
- autogenerate 生成后**务必人工检查** `alembic/versions/` 下的脚本，确认没有误删字段或漏掉索引，再执行 `upgrade`。

## 首次启动与 RBAC 引导

执行 `alembic upgrade head` 后直接启动应用即可。应用启动时会幂等执行 `src/core/bootstrap.py`：

- 补齐接口使用的全部权限编码（`user:read`、`role:assign` 等）
- 创建 `admin` 角色并绑定全部权限
- 按 `.env` 中的 `BOOTSTRAP_SUPERUSER_USERNAME` / `BOOTSTRAP_SUPERUSER_PASSWORD` 创建初始超级管理员（账号已存在则提升为超级管理员）

初始管理员创建成功后，建议从 `.env` 中移除密码并重启。后续新增受保护接口时，记得把权限编码加入 `DEFAULT_PERMISSIONS`，否则新权限不会自动入库。

## 启动后端

在**仓库根目录**、已激活虚拟环境的终端执行：

```bash
# 1. 应用数据库迁移（首次及每次拉取新迁移后）
alembic upgrade head

# 2. 开发模式启动（代码变更自动重载）
fastapi dev src/main.py

# 或者使用 uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- 默认地址：http://127.0.0.1:8000
- 接口文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health
- `fastapi` 命令由 `fastapi[standard]` 提供，`uv sync` 时已安装。
- 注意：`pyproject.toml` 中的 `chenguang-agent-platform = "src.main:main"` 指向已注释的 `main()`，`uv run chenguang-agent-platform` 当前不可用，请使用上面的 `fastapi dev` 或 `uvicorn`。

## 启动前端

```bash
cd app
npm install
npm run dev
```

- 默认地址：http://localhost:5173
- 前端通过 `app/.env` 配置后端地址（注意带上 `/api/v1`）：

```bash
VITE_USE_MOCK=false
VITE_API_BASE=http://localhost:8000/api/v1
```

- 后端已放行 `localhost` / `127.0.0.1` 任意端口的跨域请求，本地联调无需额外配置。
- 登录后 token 保存在 `localStorage`，请求自动携带 `Authorization: Bearer <token>`。
- **注意**：目前除 `auth` 外，多数业务 service 固定使用 Mock（例如 `app/src/services/model.ts`）。需要联调后端时，把对应 service 从 `mockXxxService` 切换为 `./api/xxx` 中的 `apiXxxService`。

其他命令：

```bash
npm run build   # 类型检查 + 生产构建
npm run lint    # ESLint
```

## 运行测试

```bash
# 仓库根目录，已激活虚拟环境
uv run pytest
```

测试使用**独立数据库** `<DB_NAME>_test`（例如 `chenguang` 对应 `chenguang_test`），不会读写开发库：

- 每次 pytest 启动时会自动 `CREATE DATABASE IF NOT EXISTS`，并按 ORM 模型重建全部表。
- 用例在事务内执行并回滚，测试库本身的 ID 消耗不影响开发库。
- 数据库账号需要具备创建数据库的权限（默认 `root` 即可）。
- MySQL 与 Redis 连接信息仍从 `.env` 读取。


