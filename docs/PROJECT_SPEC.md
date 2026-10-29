# 辰光Agent平台 — 项目说明书

> 本文档旨在帮助开发者（或大模型）快速理解项目全貌，以便高效地阅读和修改代码。
> 最后核对时间：2026-10-30，内容已与仓库实际代码对齐。

---

## 一、项目概述

辰光Agent平台（Chenguang Agent Platform）是一个企业级 AI Agent 管理平台，提供 Agent 全生命周期管理、知识库(RAG)管理、Prompt 工程、模型管理、工具编排、对话日志分析、数据统计等能力。

项目采用前后端分离架构：
- **后端**：Python FastAPI（异步），位于根目录 `src/`
- **前端**：React 19 + TypeScript + Vite，位于 `app/` 目录
- **基础设施**：Docker Compose 编排 MySQL 8.4 + Redis + MinIO

当前实际进度：后端已完成 RBAC（用户/角色/权限，含用户删除）与认证；前端全部页面已完成。前端默认连接真实后端（`app/.env` 中 `VITE_USE_MOCK=false`）：认证与系统管理（用户/角色/权限/个人资料）走真实 API；后端尚未实现的模块（Agent/模型/Prompt/知识库/工具/对话/统计/Dashboard）服务入口固定使用 Mock。

---

## 二、技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.13（`.python-version` 固定） | 运行时 |
| FastAPI | 0.135.1（`fastapi[standard]`） | Web 框架（异步） |
| SQLAlchemy | 2.0.48（async） | ORM |
| asyncmy | >=0.2.17 | MySQL 异步驱动 |
| Alembic | >=1.20.1 | 数据库迁移 |
| Pydantic v2 + pydantic-settings | 2.16.1（传递依赖） | 数据校验 / 配置管理 |
| Redis | >=8.1.0（redis.asyncio） | 缓存（验证码等） |
| PyJWT | >=2.15.1 | JWT 令牌签发/验证 |
| bcrypt | >=5.0.0 | 密码哈希 |
| captcha | >=0.7.1 | 图形验证码生成 |
| Loguru | >=0.7.3 | 日志 |
| pytest / pytest-asyncio | >=9.1.1 / >=1.4.1 | 测试 |

> **依赖管理用 uv，不是 pip**：`pyproject.toml` + `uv.lock`，安装方式是 `uv sync`。
> 项目根目录**没有** `requirements.txt`。

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.2 | UI 框架 |
| TypeScript | 5.9 | 类型系统 |
| Vite | 7.2 | 构建工具 |
| React Router | 7.13（react-router-dom） | 路由 |
| Tailwind CSS | 4.1（@tailwindcss/postcss） | 样式 |
| Shadcn UI（radix-ui 1.4） | — | 组件库 |
| Lucide React | 0.563 | 图标 |

### 基础设施
| 服务 | 镜像/版本 | 说明 |
|------|-----------|------|
| MySQL | mysql:8.4 | 主数据库，库名 `chenguang`，端口 3306 |
| Redis | redis:8.10-alpine | 缓存，开启 appendonly，端口 6379 |
| MinIO | RELEASE.2024-12-18T13-15-44Z | 对象存储，端口 9000（API）/ 9001（控制台） |

---

## 三、目录结构

```
/                           # 项目根目录
├── src/                    # ===== 后端 Python 代码 =====
│   ├── main.py             # FastAPI 应用入口，注册路由/中间件/异常处理
│   ├── core/               # 核心基础设施
│   │   ├── config.py       # 环境变量配置（pydantic-settings，lru_cache 单例）
│   │   ├── base_model.py   # ORM 基类（Base + TimestampMixin + BaseModel）
│   │   ├── base_repository.py  # 通用 CRUD + 分页搜索 Repository（泛型）
│   │   ├── base_schema.py  # ResponseSchema<T> + PageResult<T>
│   │   ├── deps.py         # 依赖注入：get_current_user、PageParams
│   │   ├── exceptions.py   # BizException + 全局异常处理器
│   │   └── logger.py       # Loguru 日志配置（控制台 + 文件轮转）
│   ├── infra/              # 基础设施连接
│   │   ├── database.py     # 异步引擎 + 会话工厂 + get_db（自动提交/回滚）
│   │   └── redis_cache.py  # Redis 连接池 + get_redis
│   ├── middlewares/
│   │   └── logging.py      # 请求日志中间件（记录方法/路径/状态/耗时）
│   ├── modules/            # 业务模块（api/service/repository/schema/model）
│   │   ├── auth/           # 认证（只有 api/service/schema，无 model/repository）
│   │   ├── captcha/        # 图形验证码（只有 api/service/schema）
│   │   ├── user/           # 用户管理
│   │   ├── role/           # 角色管理（含两张关联表定义）
│   │   └── permission/     # 权限管理
│   └── utils/
│       ├── jwt_utils.py    # JWT 编码/解码 + oauth2_scheme
│       ├── password_utils.py  # bcrypt 密码哈希/校验
│       └── async_sample.py # 异步示例（与业务无关）
│
├── alembic/                # 数据库迁移脚本（env.py 从 config 读取连接串）
├── alembic.ini             # Alembic 配置
├── docker/
│   ├── docker-compose.yaml # MySQL + Redis + MinIO 容器编排
│   ├── mysql/              # data + init 挂载目录
│   ├── redis/              # data 挂载目录
│   └── minio/              # data 挂载目录
├── test/                   # pytest 测试（conftest + 10 个用例文件）
├── logs/                   # 运行日志输出目录
├── pyproject.toml          # 依赖与项目元数据（uv 管理）
├── uv.lock                 # 依赖锁文件
├── .python-version         # 3.13
├── .env / .env.example     # 后端环境变量（.env 被 git 忽略）
│
├── app/                    # ===== 前端 React 代码 =====
│   ├── src/
│   │   ├── main.tsx        # 应用入口
│   │   ├── App.tsx         # 路由定义（含 AuthGuard 保护）
│   │   ├── index.css       # 全局样式（Tailwind + Shadcn 主题变量）
│   │   ├── layouts/
│   │   │   └── DashboardLayout.tsx  # 主布局（侧边栏 + 面包屑 + 头像菜单）
│   │   ├── components/
│   │   │   ├── AuthGuard.tsx   # 未登录跳转 /login
│   │   │   ├── Pagination.tsx  # 通用分页组件
│   │   │   └── ui/         # Shadcn UI 组件（19 个）
│   │   ├── pages/          # 页面组件（按模块分文件夹）
│   │   │   ├── Dashboard.tsx / Login.tsx / Profile.tsx / Settings.tsx
│   │   │   ├── agent/      # List/Create/Detail/Test/Versions/Monitor
│   │   │   ├── model/      # List/Create/Providers/Test
│   │   │   ├── prompt/     # List/Create/Versions
│   │   │   ├── knowledge/  # List/Create/Detail/Documents/Segments/Test
│   │   │   ├── tool/       # List/Create/Detail
│   │   │   ├── conversation/  # List/Detail
│   │   │   ├── analytics/  # Usage/Costs/Evaluation
│   │   │   └── system/     # Users/Roles/Permissions/ApiKeys/Audit/Alerts/Settings
│   │   ├── services/       # 数据服务层（核心设计，见 5.2）
│   │   ├── hooks/use-mobile.ts
│   │   └── lib/utils.ts    # cn() 工具函数
│   ├── package.json
│   ├── .env / .env.example # 前端环境变量（默认连接真实后端）
│   └── docs/               # 前端功能设计文档
│       ├── 00-架构总览.md
│       ├── 01~09 各模块设计文档
│       ├── 10-API接口规范.md
│       └── 其他补充说明文档
└── docs/                   # 本文档所在目录（PROJECT_SPEC.md、swagger-openapi.json）
```

---

## 四、后端架构详解

### 4.1 分层架构

每个含数据表的业务模块遵循统一分层：

```
modules/{module}/
├── api.py          # 路由层：接收请求，调用 Service，封装响应
├── service.py      # 业务层：业务逻辑，调用 Repository
├── repository.py   # 数据层：继承 BaseRepository，数据库操作
├── model.py        # ORM 模型：继承 BaseModel
└── schema.py       # Pydantic 模型：请求/响应数据结构
```

调用链路：`API (Router) → Service → Repository → Database`

例外：`auth` 与 `captcha` 没有 model/repository（auth 复用 user 的 Repository，captcha 只用 Redis）。

### 4.2 基类设计

**BaseModel**（`core/base_model.py`）：
```python
class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # created_at / updated_at 由 TimestampMixin 提供（server_default=func.now()）
```

**BaseRepository**（`core/base_repository.py`，泛型 `BaseRepository[T]`）：
```
get_by_id(id)
get_all(offset=0, limit=100)
create(obj) / update(obj) / delete(obj)
get_page(offset, limit, keyword, search_fields) -> (items, total)
```
> 注意：**没有** `delete_by_id()`，删除请用 `delete(obj)`；分页统一走 `get_page`，结果按 `id desc` 排序。

**ResponseSchema**（`core/base_schema.py`）：
```python
class ResponseSchema(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
```

**PageResult**（`core/base_schema.py`）：
```python
class PageResult(BaseModel, Generic[T]):
    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
```

### 4.3 已实现的后端模块

| 模块 | 路由前缀 | 功能 |
|------|---------|------|
| auth | `/api/v1/auth` | 登录（用户名+密码+验证码 → JWT） |
| captcha | `/api/v1/captcha` | 图形验证码生成与校验（Redis 存储，5 分钟过期） |
| user | `/api/v1/users` | 用户 CRUD（含删除）、角色分配、当前用户、分页搜索 |
| role | `/api/v1/roles` | 角色 CRUD、权限分配、分页搜索 |
| permission | `/api/v1/permissions` | 权限 CRUD、分页搜索 |

### 4.4 数据库模型关系

```
User ──M:N──> Role ──M:N──> Permission
     (user_roles)    (role_permissions)
```

- `users` 表：username, email, hashed_password, is_active, is_superuser, last_login
- `roles` 表：code, name, description
- `permissions` 表：code, name, description
- `user_roles` 关联表：user_id, role_id（复合主键，`ondelete=CASCADE`）
- `role_permissions` 关联表：role_id, permission_id（复合主键，`ondelete=CASCADE`）

关联关系使用 `lazy="selectin"`（`User.roles`、`Role.permissions`），避免 N+1。

### 4.5 认证流程

1. 前端 `GET /api/v1/captcha` 获取验证码：返回 `{key, images}`（`images` 为 `data:image/png;base64,...`）
2. 前端 `POST /api/v1/auth/login` 提交 `{username, password, captcha_key, captcha_code}`
3. 后端：校验验证码（Redis，校验后立即删除防重试）→ 查询用户 → 校验密码（bcrypt）→ 更新 `last_login` → 签发 JWT（30 分钟有效，`sub` 为用户 id 字符串）
4. 前端后续请求携带 `Authorization: Bearer <token>`
5. 受保护接口通过 `Depends(get_current_user)` 解析 token 获取当前用户（校验存在性与 is_active）

### 4.6 依赖注入模式

```python
# 每个模块的 api.py 中定义 Service 工厂函数
def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)

# 路由中注入
@router.post("")
async def create_user(data: UserCreate, svc: UserService = Depends(get_user_service)):
    ...
```

### 4.7 分页规范（已落地）

基础设施：
- `PageResult[T]`：`core/base_schema.py`
- `PageParams`：`core/deps.py`，字段 `page`(>=1, 默认 1)、`page_size`(1~100, 默认 10)、`keyword`
- `BaseRepository.get_page()`：一次查询返回 `(items, total)`

执行流程：
1. 前端 `GET /xxx/search?page=1&page_size=10&keyword=abc`
2. API 接收 `params: PageParams = Depends()`
3. Service 调用 `Repo.search_page(offset=params.offset, limit=params.page_size, keyword=params.keyword)`
4. Repo 调用 `get_page()`，返回 `(items, total)`
5. Service 组装 `PageResult[T](items, total, page, page_size)`
6. API 返回 `ResponseSchema[PageResult[XxxRead]]`

各 Repository 定义自己的 `SEARCH_FIELDS`：
```python
class UserRepository(BaseRepository[User]):
    SEARCH_FIELDS = ["username", "email"]

    async def search_page(self, offset, limit, keyword):
        return await self.get_page(offset=offset, limit=limit,
                                   keyword=keyword, search_fields=self.SEARCH_FIELDS)
```
- user：`["username", "email"]`
- role：`["name", "code"]`
- permission：`["name", "code"]`

---

## 五、前端架构详解

### 5.1 路由结构

路由定义在 `app/src/App.tsx`，除 `/login` 外全部由 `AuthGuard` + `DashboardLayout` 包裹（未登录跳 `/login`）：

```
/login                          → Login（独立页面，无侧边栏）
/                               → AuthGuard + DashboardLayout 包裹
  ├── /                         → Dashboard（工作台）
  ├── /profile                  → Profile
  ├── /settings                 → Settings
  ├── /agents                   → AgentList
  ├── /agents/create            → AgentCreate
  ├── /agents/:id               → AgentDetail
  ├── /agents/:id/edit          → AgentCreate（复用）
  ├── /agents/:id/test          → AgentTest
  ├── /agents/:id/versions      → AgentVersions
  ├── /agents/:id/monitor       → AgentMonitor
  ├── /models                   → ModelList
  ├── /models/create            → ModelCreate
  ├── /models/:id/edit          → ModelCreate（复用）
  ├── /models/:id/test          → ModelTest
  ├── /models/providers         → ModelProviders
  ├── /prompts                  → PromptList
  ├── /prompts/create           → PromptCreate
  ├── /prompts/:id/edit         → PromptCreate（复用，编辑模式）
  ├── /prompts/:id/versions     → PromptVersions
  ├── /knowledge                → KnowledgeList
  ├── /knowledge/create         → KnowledgeCreate
  ├── /knowledge/:id            → KnowledgeDetail
  ├── /knowledge/:id/documents  → KnowledgeDocuments
  ├── /knowledge/:id/segments   → KnowledgeSegments
  ├── /knowledge/:id/test       → KnowledgeTest
  ├── /tools                    → ToolList
  ├── /tools/create             → ToolCreate
  ├── /tools/:id                → ToolDetail
  ├── /conversations            → ConversationList
  ├── /conversations/:id        → ConversationDetail
  ├── /analytics                → AnalyticsUsage（默认落在用量页）
  ├── /analytics/costs          → AnalyticsCosts
  ├── /analytics/evaluation     → AnalyticsEvaluation
  ├── /system/users             → SystemUsers
  ├── /system/roles             → SystemRoles
  ├── /system/permissions       → SystemPermissions
  ├── /system/api-keys          → SystemApiKeys
  ├── /system/audit             → SystemAudit
  ├── /system/alerts            → SystemAlerts
  ├── /system/settings          → SystemSettings
  └── *                         → 「页面开发中...」占位
```

### 5.2 数据服务层（Mock/API 双轨设计）

所有页面通过 `services/` 获取数据，不直接引用 Mock。

**切换机制**（`services/config.ts`）：
```typescript
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'
```
> 未定义 `VITE_USE_MOCK` 时 `USE_MOCK` 为 true；但仓库已提供 `app/.env`（`VITE_USE_MOCK=false`、`VITE_API_BASE=http://localhost:8000/api/v1`），因此**默认连接真实后端**。

**服务入口**（以 agent 为例，`services/agent.ts`）：
```typescript
import { USE_MOCK } from './config';
import { mockAgentService } from './mock/agent';
import { apiAgentService } from './api/agent';
// 后端尚未实现该模块接口，固定使用 Mock；后端就绪后恢复三元切换
export const agentService = mockAgentService;
```
> 目前 Agent/模型/Prompt/知识库/工具/对话/统计/Dashboard 的服务入口均固定导出 Mock 服务；系统管理内无后端接口的 API密钥/审计/告警/系统配置页面同样固定使用 Mock，因此真实模式下也不会请求不存在的接口。

**目录对应关系**：
```
services/
├── config.ts              # USE_MOCK / API_BASE
├── types/                 # TypeScript 接口定义（前后端数据契约）
│   ├── common.ts          # ApiResponse, ApiErrorResponse, PaginatedResponse, PaginationParams...
│   ├── agent.ts / model.ts / prompt.ts / knowledge.ts / tool.ts
│   ├── conversation.ts / analytics.ts / dashboard.ts / system.ts
├── mock/                  # Mock 实现（带模拟延迟）
│   ├── data/              # 静态 Mock 数据（10 个数据文件）
│   └── [module].ts        # agent/analytics/auth/conversation/dashboard/knowledge/model/prompt/system/tool
├── api/                   # 真实 API 实现（已全部实现，非骨架）
│   ├── client.ts          # HTTP 客户端（fetch 封装）
│   └── [module].ts        # 各模块 API Service
└── [module].ts            # 各模块服务入口（自动选择 mock 或 api）
```

**切换方式**（建议通过 `app/.env` 配置，避免各 shell 的临时变量语法差异）：
```bash
# 默认：连接真实后端（app/.env 已提供）
# VITE_USE_MOCK=false
# VITE_API_BASE=http://localhost:8000/api/v1

# 需要离线演示时切回 Mock：把 VITE_USE_MOCK 改为 true 或删除该行
```

### 5.3 API 客户端

`services/api/client.ts` 封装了基于 fetch 的 HTTP 客户端：
- 支持 GET（带 query params）、POST、PUT、DELETE；POST 自动识别 `FormData`（文件上传）
- **已实现 token 注入**：从 `localStorage.access_token` 读取并添加 `Authorization: Bearer <token>`
- 401 时清除 token 并跳转 `/login`
- 自动解包 `data` 字段；业务 `code` 非 200/0 时抛错（兼容 `code: 0` 与 `code: 200` 两种约定）

### 5.4 布局

`DashboardLayout.tsx` 提供：
- 左侧固定侧边栏：工作台、Agent管理、模型管理、Prompt管理、知识库、工具管理、对话日志、数据统计、系统管理（可展开，含用户/角色/**权限**/API密钥/审计/告警/系统配置）
- 顶部面包屑导航
- 右上角用户头像下拉菜单（个人信息、设置、退出）
- 内容区通过 `<Outlet />` 渲染子路由

### 5.5 UI 组件

Shadcn UI（基于 Radix），已安装 19 个：
`alert-dialog, avatar, badge, button, card, dropdown-menu, input, label, scroll-area, select, separator, sheet, sidebar, skeleton, switch, table, tabs, textarea, tooltip`

自定义组件（`components/`）：`AuthGuard.tsx`、`Pagination.tsx`（支持每页条数切换）。

### 5.6 列表分页（用户 / 角色 / 权限）

三个系统管理列表页统一采用**服务端分页**，不再一次性拉取全量：

| 页面 | 接口 | 搜索字段 |
|------|------|----------|
| `/system/users` | `GET /users/search` | 用户名、邮箱 |
| `/system/roles` | `GET /roles/search` | 角色名称、编码 |
| `/system/permissions` | `GET /permissions/search` | 权限名称、编码 |

统一行为：
- 请求参数 `{ page, page_size, keyword }`；每页条数默认 10，可切换 5 / 10 / 20 / 50
- 搜索或切换每页条数时，页码重置为 1
- 删除后若当前页超界（如删掉末页最后一条），自动回退到最后一个有效页
- `Pagination.tsx` 展示总条数、当前页/总页数、上一页/下一页与省略页码；`total === 0` 时不渲染
- Mock 模式对应 `getUsers / getRolesPaged / getPermissionsPaged`，返回 `{ data, total, page, pageSize }`；真实接口返回 `{ items, total, page, page_size }`
- 统计卡片：总数取后端 `total`；用户「本页活跃/本页停用」与权限「模块（本页）」仅统计当前页数据

---

## 六、前端 TypeScript 类型定义速查

### 通用类型（`types/common.ts`）
```typescript
interface ApiResponse<T> { code: 0; message: 'success'; data: T }
interface PaginatedResponse<T> {
  code: 0; message: 'success';
  data: { items: T[]; total: number; page: number; pageSize: number; totalPages: number }
}
interface PaginationParams { page?: number; pageSize?: number }
interface SortParams { sortBy?: string; sortOrder?: 'asc' | 'desc' }
interface SearchParams { keyword?: string }
```
> 真实后端分页返回的是 `PageResult`：`{ items, total, page, page_size }`，字段是下划线 `page_size`；`services/api/system.ts` 中另定义了对应的 `PageResult<T>`。

### Agent（`types/agent.ts`）
- `Agent`：id, name, description, type(conversation|tool|analysis|creative|workflow), status(active|inactive|error|draft), modelId, config(AgentConfig), successRate, callCount7d, version...
- `AgentConfig`：model + prompt + RAG + tools + advanced
- `AgentVersion`：版本管理

### Model（`types/model.ts`）
- `Model`：id, name, modelId, providerId, capabilities, contextLength, status, inputPrice, outputPrice...
- `ModelProvider`：type(openai|anthropic|aliyun|azure|local|custom), status, endpoint...

### Prompt（`types/prompt.ts`）
- `Prompt`：id, name, content, variables(PromptVariable[]), version, status(draft|published)...

### Knowledge（`types/knowledge.ts`）
- `KnowledgeBase`：id, name, status(ready|indexing|error|empty), documentCount, segmentCount, embeddingModel...
- `Document`：fileType(pdf|docx|md|txt|html|csv), status(pending|processing|completed|failed)...
- `Segment`：content, wordCount, tokenCount, keywords, hitCount...

### Tool（`types/tool.ts`）
- `Tool`：type(builtin|http_api|custom_function), status(enabled|disabled|error)...
- `ToolDetail`：config(HttpApiConfig|CustomFunctionConfig), functionDefinition...

### Conversation（`types/conversation.ts`）
- `Conversation`：agentId, turnCount, totalTokens, totalCost, satisfaction...
- `ConversationTurn`：role(user|assistant), content, trace(TurnTrace)...
- `TurnTrace`：steps(TraceStep[])，链路追踪

### System（`types/system.ts`）
- `User`, `Role`, `Permission`, `ApiKey`, `AuditLog`, `AlertRule`, `ActiveAlert`, `SystemSettings`

---

## 七、环境配置

### 后端环境变量（根目录 `.env`，模板见 `.env.example`）
```env
APP_NAME=辰光Agent
APP_ENV=development          # 默认值 development
APP_DEBUG=true

DB_HOST=192.168.10.102
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456           # 无默认值，缺失时启动报错
DB_NAME=chenguang

REDIS_HOST=192.168.10.102
REDIS_PORT=6379
REDIS_PASSWORD=123456        # 无默认值，缺失时启动报错
REDIS_DB=0

MINIO_ROOT_USER=minioadmin   # 仅供 docker compose 使用
MINIO_ROOT_PASSWORD=minioadmin123

LOG_LEVEL=DEBUG
LOG_DIR=logs
```
> `.env.example` 中 APP_NAME 为 `MyApp`、DB_HOST 为 `127.0.0.1`、密码为 `change-me`，复制后按需修改。

### 前端环境变量（`app/.env`，模板见 `app/.env.example`）
```env
VITE_USE_MOCK=false
VITE_API_BASE=http://localhost:8000/api/v1
```

### Docker 环境变量（`docker/.env`，与 compose 同目录）
README 要求远程部署时把 `.env` 复制到 `docker/` 下，`docker compose` 通过 `--env-file docker/.env` 显式指定。

---

## 八、启动方式

### 依赖环境（uv）
```bash
uv venv
uv sync            # Windows 激活：.venv\Scripts\Activate.ps1
```

### 基础设施
```bash
# 必须在仓库根目录执行；--project-directory . 保证数据卷落到 <项目根>/docker/...
docker compose --project-directory . -f docker/docker-compose.yaml --env-file docker/.env up -d
```

### 后端
```bash
cp .env.example .env      # 首次初始化，填入真实密码
alembic upgrade head      # 数据库迁移
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd app
npm install
npm run dev
```

### 测试
```bash
pytest                    # test/ 下共 10 个用例文件（auth/captcha/health/jwt/password/permission/role/user 等）
```

---

## 九、API 接口规范

### 后端已实现的接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/captcha` | 获取图形验证码（返回 `{key, images}`） |
| POST | `/api/v1/captcha/verify` | 校验验证码 |
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/users` | 创建用户 |
| GET | `/api/v1/users/me` | 获取当前登录用户 |
| GET | `/api/v1/users/search` | 分页搜索用户（PageParams + PageResult） |
| GET | `/api/v1/users/{id}` | 获取用户详情（**不含角色**，返回 UserRead） |
| GET | `/api/v1/users` | 用户列表（offset/limit，未分页） |
| PUT | `/api/v1/users/{id}/roles` | 给用户分配角色 |
| GET | `/api/v1/users/{id}/roles` | 查看用户的角色列表（UserWithRolesRead） |
| DELETE | `/api/v1/users/{id}` | 删除用户 |
| POST | `/api/v1/roles` | 创建角色 |
| GET | `/api/v1/roles` | 角色列表（未分页） |
| GET | `/api/v1/roles/search` | 分页搜索角色 |
| GET | `/api/v1/roles/{id}` | 角色详情（含权限） |
| PUT | `/api/v1/roles/{id}` | 更新角色 |
| DELETE | `/api/v1/roles/{id}` | 删除角色 |
| PUT | `/api/v1/roles/{id}/permissions` | 给角色分配权限 |
| GET | `/api/v1/permissions` | 权限列表（未分页） |
| GET | `/api/v1/permissions/search` | 分页搜索权限 |
| GET | `/api/v1/permissions/{id}` | 权限详情 |
| POST | `/api/v1/permissions` | 创建权限 |
| PUT | `/api/v1/permissions/{id}` | 更新权限 |
| DELETE | `/api/v1/permissions/{id}` | 删除权限 |
| GET | `/health` | 健康检查 |

### 前端期望的接口（Mock 层已定义，后端待实现）

详见 `app/docs/10-API接口规范.md`，涵盖 Agent、模型、Prompt、知识库、工具、对话、统计等全部模块的 RESTful API。`docs/swagger-openapi.json` 为后端导出的 OpenAPI 描述，可作为对接依据。

---

## 十、开发注意事项

### 后端
1. 所有 ORM 模型继承 `BaseModel`，自带 `id`, `created_at`, `updated_at`
2. 所有 Repository 继承 `BaseRepository[T]`，自带基础 CRUD 与 `get_page()`
3. 统一响应格式 `ResponseSchema(code=200, message="success", data=...)`
4. 业务异常用 `raise BizException(code=xxx, message="xxx")`，全局处理器返回 **HTTP 200 + 非 200 code**；未捕获异常返回 HTTP 500
5. 数据库会话通过 `Depends(get_db)` 注入，正常结束自动 commit，异常自动 rollback
6. JWT 密钥硬编码在 `jwt_utils.py`（生产环境需移至环境变量）
7. 新增模块遵循 `api → service → repository → model/schema` 分层
8. 路由注册在 `src/main.py` 的 `create_app()` 中
9. 新增 model 后必须在 `alembic/env.py` 中 import，否则 autogenerate 发现不了新表

### 前端
1. 新增页面：`pages/` 下创建组件 → `App.tsx` 加路由 → `DashboardLayout.tsx` 加菜单项
2. 新增数据服务：`types/` 定义类型 → `mock/` 与 `api/` 分别实现 → `services/` 根目录创建切换入口
3. 登录已对接 `authService`（Mock/真实 API 双轨），token 存于 `localStorage.access_token`
4. API 客户端已注入 Authorization header，对接后端只需配置 `VITE_API_BASE`
5. UI 组件在 `components/ui/`，可用 `npx shadcn@latest add [component]` 添加
6. 前端文档在 `app/docs/`，每个模块有详细功能设计说明

### 数据库迁移
```bash
alembic revision --autogenerate -m "描述本次变更"
alembic upgrade head
alembic downgrade -1
```

---

## 十一、当前开发状态

| 部分 | 状态 | 说明 |
|------|------|------|
| 后端 RBAC | ✅ 已完成 | User/Role/Permission 完整 CRUD（含用户删除）+ 关联 + 分页搜索 |
| 后端认证 | ✅ 已完成 | 登录 + JWT + 验证码 |
| 后端 Agent/Model/Prompt/知识库/工具/对话/统计 | ❌ 待实现 | 前端 Mock 层已定义接口契约 |
| 前端全部页面 | ✅ 已完成 | 使用 Mock 数据，UI 完整 |
| 系统管理分页 | ✅ 已完成 | 用户/角色/权限列表均为服务端分页，支持关键词搜索、每页条数切换、删除后页码回退 |
| 前端 Mock 数据层 | ✅ 已完成 | 所有模块 Mock Service + 静态数据 |
| 前端 API 数据层 | ✅ 已实现 | 各模块 api service 均已编写，等待后端接口 |
| 前后端对接 | ⚠️ 部分完成 | 登录、验证码、系统管理（用户/角色/权限）、个人资料已对接；其余模块待后端实现 |
| 自动化测试 | ✅ 已有 | `test/` 下 10 个 pytest 用例，覆盖 RBAC 与认证 |

---

## 十二、已知问题 / 待修正

以下为文档核对时发现的真实代码不一致，修改代码时需留意：

1. ~~**验证码字段名不一致**~~ **已修复（2026-10-30）**：前端改为读取 `images`。
2. ~~**前端默认 `API_BASE` 缺版本段**~~ **已修复**：默认值与 `app/.env` 均为 `http://localhost:8000/api/v1`。
3. ~~**后端缺少删除用户接口**~~ **已修复**：新增 `DELETE /api/v1/users/{id}`，前端删除按钮可直接使用。
4. ~~**`GET /users/{id}` 返回不含角色**~~ **已修复**：分配角色弹窗改用 `GET /users/{id}/roles`（返回只含一个元素的列表）。
5. **列表接口存在两套**：`GET ""` 返回全量 list（offset/limit 参数），`GET /search` 才是标准分页；新增列表接口应统一走 `/search` 的 `PageParams + PageResult` 模式。
6. **JWT 密钥硬编码**于 `src/utils/jwt_utils.py`。
7. `pyproject.toml` 中的脚本入口 `chenguang-agent-platform = "src.main:main"` 对应的 `main()` 已被注释，该入口当前不可用。
8. `Role.description` / `Permission.description` 标注为 `Mapped[str]` 但 `nullable=True`，类型与可空性不符。
9. ~~**前端类型检查仍有历史错误**~~ **已修复（2026-10-30）**：统一了 `types/system.ts`、`types/conversation.ts`、`types/analytics.ts` 与实际 Mock 数据/页面字段，`tsc -b` 0 错误、`npm run build` 通过。剩余 `npm run lint` 的 48 个错误/24 个警告属规则类问题（`no-explicit-any`、`react-hooks`），不影响构建。

---

## 十三、变更记录

### 2026-10-30 接口对接补全

| 类型 | 内容 |
|------|------|
| 前端修复 | 验证码字段 `image` → `images`，真实模式验证码图片可正常显示 |
| 前端修复 | `API_BASE` 默认值改为 `http://localhost:8000/api/v1`；新增 `app/.env`、`app/.env.example`，默认连接真实后端 |
| 前端新增 | `apiSystemService.getUserRoles()` 对接 `GET /users/{id}/roles`，修复分配角色弹窗因 `GET /users/{id}` 不含角色导致的崩溃 |
| 前端修复 | 角色、权限全量列表去掉多余尾斜杠（改为 `/roles`、`/permissions`） |
| 前端新增 | 个人资料页对接 `GET /users/me`，展示真实用户名/邮箱/启用状态，其余展示字段保留占位 |
| 前端调整 | 未实现模块（Agent/模型/Prompt/知识库/工具/对话/统计/Dashboard）服务入口固定 Mock；API密钥/审计/告警/系统配置页面固定 Mock，避免真实模式下调用不存在的接口 |
| 前端修复 | `mock/system.ts` 分页返回类型与实际扁平结构对齐，用户/角色/权限页类型检查通过 |
| 后端新增 | `DELETE /api/v1/users/{user_id}`（`UserService.delete_user`），返回 `ResponseSchema[None]` |
| 后端新增 | 注册 `CORSMiddleware`，用正则放行本机任意端口（`localhost` / `127.0.0.1`，`allow_credentials=False`），修复浏览器跨域导致验证码图片与登录请求失败的问题（`test/test_cors.py` 覆盖） |
| 文档 | `docs/swagger-openapi.json` 增加删除用户接口；本文档同步更新 |
| 前端修复 | 清理历史类型错误：`types/system.ts`（User/Role/ApiKey/AuditLog/SystemSettings 与 Mock 数据对齐）、`types/conversation.ts`（userName/tokenUsage/cost/duration、Turn/Step 字段）、`types/analytics.ts`（补齐 UsageStats/CostStats/EvaluationStats）、`api/client.ts` 支持 blob 下载 |
| 前端修复 | 审计页按 `action` 前后缀解析模块/操作，字段改为 `details`/`ip`；系统配置页改用嵌套 `basic/model/notification` 结构；Dashboard 移除未使用的趋势请求与重复声明 |
| 配置 | `eslint.config.js` 允许 `_` 开头的未使用占位参数；`tsc -b` 0 错误、`npm run build` 通过 |

### 2026-10-30 列表分页完善

| 类型 | 内容 |
|------|------|
| 前端增强 | `Pagination.tsx` 新增「每页 N 条」选择器（5/10/20/50，可选属性 `onPageSizeChange`），`total === 0` 时隐藏，其余页面保持向后兼容 |
| 前端调整 | 用户 / 角色 / 权限三个列表页接入服务端分页：每页条数默认 10 且可切换，搜索或切换条数时回到第 1 页 |
| 前端修复 | 删除记录导致当前页超界时，自动回退到最后一个有效页 |
| 前端调整 | 用户页统计卡改为「总用户数 / 本页活跃 / 本页停用」；权限页模块统计标注「（本页）」，避免与总数混淆 |
| 验证 | `tsc -b` 0 错误；`npm run build` 通过 |
