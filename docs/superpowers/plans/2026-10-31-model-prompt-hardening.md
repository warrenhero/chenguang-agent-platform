# Model / Prompt 模块加固实施计划

## 背景

`src/modules/model/` 与 `src/modules/prompt/` 为新增模块（当前未提交），代码审查发现 2 个阻塞问题与 9 个重要问题。本计划只修复 Critical + Important；Minor 项记录在 ledger 中留待最终审查分诊。

## 已确认的用户决策

- 修复范围：仅 Critical + Important（11 项）。
- 回滚契约：后端改为 `{ "version": "v1.2" }`，按 `prompt_id + version` 查找版本；前端与 Mock 不动。
- 删除仍有模型的供应商：保持级联删除，不新增拦截。
- 分支：`feature/model-prompt-hardening`（已创建，现有未提交改动已带过来）。

## Global Constraints

- 所有新代码、注释遵守仓库现有风格；提交信息使用中文（路径、函数名、模块名保留英文原名），不加 Co-Authored-By。
- 每个任务必须先写测试再实现（TDD），并运行相关测试。
- 不得修改 `.env`、密钥、CI 配置；不得改动与任务无关的代码。
- 只提交本任务涉及的文件，禁止 `git add -A` 把无关文件带入提交。
- 权限码来源唯一：[src/core/bootstrap.py](../../../src/core/bootstrap.py) 的 `DEFAULT_PERMISSIONS`。
- 错误语义与既有 provider 模块保持一致：资源不存在 → `BizException(code=404)`；参数/业务冲突 → `BizException(code=400)`。
- 测试环境：pytest + 独立 `*_test` 库 + 事务回滚；`client` fixture 默认携带超级管理员 token，`anon_client` 为匿名。
- 测试覆盖必须包含：匿名 401、权限码存在、正常 CRUD、404、422、分页/筛选、发布/回滚/删除等关键不变量。

## 任务

### Task 1: 为 model / prompt 全部接口补齐 RBAC 鉴权与审计字段

**目标**：13 个管理接口必须要求登录并校验权限码；创建/发布 Prompt 时写入操作者用户名（`LLMModel` 无 created_by 列，模型侧不做审计）。

**改动文件**：
- `src/modules/model/api.py`
- `src/modules/prompt/api.py`
- `src/core/bootstrap.py`
- `src/modules/model/service.py`（create 传入 current_user）
- `src/modules/prompt/service.py`（create/publish 传入 current_user）
- 新增 `test/test_model_api.py`、`test/test_prompt_api.py`（本任务先写匿名 401 与权限种子用例，后续任务继续扩充）

**权限码**：
- `model:read` / `model:create` / `model:update` / `model:delete`
- `prompt:read` / `prompt:create` / `prompt:update` / `prompt:delete`（publish 与 rollback 使用 `prompt:update`）

**要求**：
1. 每个路由按 provider 模块的写法挂 `dependencies=[Depends(require_permission("<code>"))]`：GET 用 read，POST 用 create（publish/rollback 用 update），PUT 用 update，DELETE 用 delete。
2. `DEFAULT_PERMISSIONS` 追加 8 个权限码，名称与描述用中文，风格同现有条目。
3. API 通过 `Depends(get_current_user)` 取得当前用户，把 `username` 传给 service：
   - `create_prompt(data, current_user)`
   - `publish(prompt_id, data, current_user)`
   - 签名类型为 `current_user: str | None = None`。
   - 模型侧不传、不新增 `created_by` 列（表结构无该列，属超出本次范围）。
4. 测试：
   - 13 个接口在 `anon_client` 下全部返回 401（参照 `test_provider_api.py:60`）。
   - `apply_rbac_seed` 后 `DEFAULT_PERMISSIONS` 包含 8 个新码。
   - 非超级管理员且无权限的用户访问 `/api/v1/models` 返回 403（可参照 `test_rbac_guard.py` 的建用户/建角色方式）。
   - 用超级管理员创建 Prompt 后，`created_by` 等于其用户名；发布后 `published_by` 等于其用户名。

**验证**：`python -m pytest test/test_model_api.py test/test_prompt_api.py -q` 通过，且既有 `test/test_provider_api.py`、`test/test_rbac_guard.py` 不回归。

---

### Task 2: 修复 Prompt 删除级联与关系加载

**目标**：删除已有版本的 Prompt 不再 500；Prompt 列表不再预加载全部版本全文。

**改动文件**：
- `src/modules/prompt/model.py`
- `test/test_prompt_api.py`

**要求**：
1. `Prompt.versions` 关系改为：
   `relationship("PromptVersion", back_populates="prompt", order_by="PromptVersion.id.desc()", cascade="all, delete-orphan", passive_deletes=True, lazy="select")`
   —— 数据库层 `ON DELETE CASCADE` 与 ORM 级联一致，且不再在列表查询时加载版本。
2. `PromptVersion.prompt` 关系保持现有定义。
3. 测试：
   - 创建 → 发布 → 删除，返回 200，且 `prompt_versions` 中该 prompt 的记录被删除。
   - 删除后 `GET /api/v1/prompts/{id}` 返回 404。
   - 列表接口在存在多个版本时正常返回（不触发 MissingGreenlet）。

**验证**：`python -m pytest test/test_prompt_api.py -q` 通过。

---

### Task 3: 版本不变量与回滚契约

**目标**：版本号不重复；回滚请求体改为 `{"version": "v1.2"}`；并发发布不产生重复版本。

**改动文件**：
- `src/modules/prompt/service.py`
- `src/modules/prompt/repository.py`
- `src/modules/prompt/schema.py`
- 新增迁移 `alembic/versions/<rev>_add_prompt_version_unique.py`
- `alembic/env.py` 不需要改（模型已注册）
- `test/test_prompt_api.py`

**要求**：
1. `RollbackRequest` 改为 `version: str`；`rollback()` 通过新仓储方法 `get_by_version(prompt_id, version)` 查找目标版本，找不到时 `BizException(code=404, message="版本不存在")`。
2. `_next_version` 不再基于 `prompt.version`，改为基于该 Prompt 已有版本的最大 minor：
   - 新增 `PromptVersionRepository.get_max_version(prompt_id) -> str | None`，用 `max` 语义查询（可先取全部版本的 version 再在 Python 中解析，数据量受单 Prompt 版本数限制；实现需保证每次发布只加一条查询）。
   - 无版本时返回 `v1.0`（首次发布即 v1.0，与前端示例一致）。
   - 解析失败时回退 `v1.0`。
3. 迁移新增 `UniqueConstraint("prompt_id", "version", name="uq_prompt_versions_prompt_version")`，`downgrade` 删除该约束。迁移基于当前最新 head 生成，`alembic heads` 必须仍只有一个 head。
4. 并发/竞态兜底：`publish()` 中创建版本若触发 `IntegrityError`，回滚当前事务并抛 `BizException(code=409, message="版本冲突，请重试")`。注意：`BizException(code=409)` 目前映射为 400，Task 4 会处理映射，本任务只保证异常被转换为业务异常而非 500。
5. 测试：
   - 首次发布返回 `version == "v1.0"`。
   - 连续发布得到 `v1.1`、`v1.2`。
   - 发布 v1.0、v1.1 → 回滚到 v1.0 → 再发布，得到 `v1.2`（不重复）。
   - 回滚请求体 `{"version": "v1.0"}` 成功并返回内容为 v1.0 的快照；`{"version": "v9.9"}` 返回 404；传 `{"version_id": 1}` 返回 422。
   - 版本列表中 `version` 唯一。

**验证**：`python -m pytest test/test_prompt_api.py -q`；`alembic heads` 输出单个 head。

---

### Task 4: 统一错误码与 HTTP 状态语义

**目标**：model/prompt 的"不存在"返回 HTTP 404，"重复/非法引用"返回 HTTP 400，与 provider 一致。

**改动文件**：
- `src/modules/model/service.py`
- `src/modules/prompt/service.py`
- `test/test_model_api.py`
- `test/test_prompt_api.py`

**要求**：
1. 删除私有错误码 41001/41002/41003/42001/42002，改为：
   - 模型不存在、Prompt 不存在、版本不存在 → `code=404`。
   - 模型标识符已存在、供应商不存在、版本冲突外的业务冲突 → `code=400`。
2. 在 `src/core/exceptions.py` 的 `_HTTP_STATUS` 中增加 `409: 409`，使 Task 3 的版本冲突返回 HTTP 409；其余映射不变。
3. 测试：断言 `resp.status_code` 与 body 的 `code` 同时正确：
   - `GET /api/v1/models/999999` → 404。
   - `GET /api/v1/prompts/999999` → 404。
   - 重复 `model_id` 创建 → 400。
   - 不存在的 `provider_id` 创建模型 → 400。
   - 不存在的版本回滚 → 404。
   - `GET /api/v1/models` 的 409 映射存在：断言 `_HTTP_STATUS[409] == 409`。

**验证**：`python -m pytest test/test_model_api.py test/test_prompt_api.py test/test_provider_api.py -q`。

---

### Task 5: 模型列表统一分页语义

**目标**：`GET /api/v1/models?provider_id=` 与普通列表使用同一套分页/关键词语义。

**改动文件**：
- `src/modules/model/repository.py`
- `src/modules/model/service.py`
- `test/test_model_api.py`

**要求**：
1. `ModelRepository.search_page(offset, limit, keyword, provider_id=None)` 增加可选 `provider_id` 过滤；`BaseRepository.get_page` 不支持额外条件，因此在 `ModelRepository` 内自行拼装查询（keyword 条件与 provider 条件同时生效，total 用同一 WHERE 计数）。
2. `ModelService.list_models` 取消 `get_by_provider` 分支，统一调用 `search_page`，并始终回填 `params.page` 与 `params.page_size`。
3. `get_by_provider` 若无其他调用则删除（避免死代码）。
4. 测试：
   - 建两个供应商各若干模型，`provider_id` 过滤只返回对应模型，且 `total` 正确。
   - `provider_id + keyword` 同时生效。
   - 无结果时 `page_size` 仍等于请求值，`page` 等于请求值。
   - `page_size` 超过 100 返回 422。

**验证**：`python -m pytest test/test_model_api.py -q`。

---

### Task 6: 补齐 Pydantic 请求校验

**目标**：非法输入返回 422，而不是落到数据库后 500。

**改动文件**：
- `src/modules/model/schema.py`
- `src/modules/prompt/schema.py`
- `test/test_model_api.py`
- `test/test_prompt_api.py`

**要求**：
1. `ModelCreate` / `ModelUpdate`：
   - `name`: `Field(min_length=1, max_length=100)`
   - `model_id`: `Field(min_length=1, max_length=100)`
   - `context_length`: `Field(ge=1)`
   - `input_price` / `output_price`: `Field(ge=0)`
   - `currency`: `Field(min_length=1, max_length=10)`
   - `status`: `Literal["available", "unavailable", "rate_limited"]`（仅 ModelUpdate）
   - `capabilities`: 每个元素 `max_length=50`（用 `list[Annotated[str, Field(max_length=50)]]` 或等价的校验器），保证拼接后不超过 500
   - `description`: `Field(max_length=2000)`
2. `PromptCreate` / `PromptUpdate`：
   - `name`: `Field(min_length=1, max_length=200)`
   - `description`: `Field(max_length=500)`
   - `category`: `Field(min_length=1, max_length=50)`
   - `content`: `Field(min_length=1)`
   - `PublishRequest.changelog`: `Field(max_length=500)`
3. `PromptVariableSchema`：`name`/`type`/`description` 加合理长度上限（`name` 1-100，`type` 1-50，`description` max 500）。
4. 测试：超长 `name`、负价格、非法 `status`、超长 `changelog` 均返回 422；合法边界值通过。

**验证**：`python -m pytest test/test_model_api.py test/test_prompt_api.py -q`。

---

### Task 7: Provider 的 model_count 落地真实统计

**目标**：供应商列表/详情返回真实模型数量。

**改动文件**：
- `src/modules/provider/repository.py`
- `test/test_provider_api.py`

**要求**：
1. `count_models` 改为 `select(func.count()).select_from(LLMModel).where(LLMModel.provider_id == provider_id)`。
2. 在方法内部局部导入 `LLMModel` 以避免循环导入（`model.model` 已导入 `provider.model`）。
3. 把方法 docstring 中"返回 0"的过时说明删掉。
4. 测试：创建供应商 → 创建 2 个模型 → `GET /api/v1/providers` 与 `GET /api/v1/providers/{id}` 的 `model_count == 2`；删除模型后为 1。
5. 不改变删除供应商的级联行为（用户已确认保留）。

**验证**：`python -m pytest test/test_provider_api.py -q`。

---

### Task 8: 补充 model / prompt 集成测试至完整覆盖

**目标**：把前 7 个任务分散写的用例整理成完整的接口级覆盖，确保审查指出的逃逸路径都被测试命中。

**改动文件**：
- `test/test_model_api.py`
- `test/test_prompt_api.py`

**要求**（仅补缺口，不重复已有用例）：
- models：创建成功字段回显、详情、更新（含默认模型互斥：设 B 为默认后 A 的 `is_default` 变 False）、删除、分页、关键词搜索、`provider_name` 回显。
- prompts：创建/详情/更新/删除、分页、关键词、tags 与 variables 往返、发布快照内容正确、版本列表倒序、`is_current` 唯一、回滚后 `is_current` 归属正确。
- 所有用例使用 `client`（超级管理员）fixture，禁止 mock 掉数据库。
- 测试不得依赖用例执行顺序；名称与数据用 `uuid` 去重。

**验证**：`python -m pytest test/test_model_api.py test/test_prompt_api.py -q`，全部通过；`python -m pytest -q` 全量通过。
