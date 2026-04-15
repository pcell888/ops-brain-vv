# 兼容层瘦化重构指南

本文档提供了一套标准化的重构流程，用于将"厚"兼容层重构为"薄"适配器。

## 📋 重构检查清单

### 准备阶段

- [ ] 阅读现有兼容层代码，理解业务逻辑
- [ ] 识别可以提取到 Service 层的函数
- [ ] 检查是否有标准路由也实现了类似逻辑
- [ ] 确认数据库查询和业务逻辑的边界

### 实施阶段

- [ ] 创建 Service 层文件 (`src/services/xxx_service.py`)
- [ ] 提取业务逻辑函数到 Service 层
- [ ] 提取辅助函数到 Service 层
- [ ] 重写兼容层为薄适配器
- [ ] 更新标准路由使用 Service 层（如果存在）
- [ ] 统计代码行数变化

### 验证阶段

- [ ] 检查代码语法正确性
- [ ] 运行现有测试套件
- [ ] 手动测试关键接口
- [ ] 代码审查

### 文档阶段

- [ ] 创建模块重构总结文档
- [ ] 更新总体重构报告
- [ ] 记录遇到的问题和解决方案

## 🔧 重构步骤详解

### 步骤 1：分析现有代码

#### 1.1 统计代码行数

```bash
# PowerShell
Get-Content src/api/routes/compat_xxx.py | Measure-Object -Line

# Bash
wc -l src/api/routes/compat_xxx.py
```

#### 1.2 识别业务逻辑

查找以下模式：
- 数据库查询（`async with get_conn()`）
- 数据转换（`_xxx_to_dict()`）
- 状态计算（`_calculate_xxx()`）
- 聚合逻辑（`GROUP BY`, `COUNT`, `SUM` 等）

#### 1.3 识别辅助函数

查找以 `_` 开头的私有函数：
- 数据提取函数（`_extract_xxx()`）
- 格式转换函数（`_format_xxx()`）
- 验证函数（`_validate_xxx()`）

### 步骤 2：创建 Service 层

#### 2.1 创建文件

```python
# src/services/xxx_service.py
"""XXX 业务逻辑服务层。

封装 XXX 相关的核心业务逻辑，供 API 路由层调用。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── 辅助函数 ──────────────────────────────────────────────────

def _helper_function():
    """辅助函数说明。"""
    pass


# ── 核心业务逻辑 ──────────────────────────────────────────────

async def get_xxx_list():
    """获取 XXX 列表。
    
    Args:
        param1: 参数说明
        
    Returns:
        (items, total) - 列表和总数
    """
    pass
```

#### 2.2 提取业务逻辑

**原则：**
- 所有数据库查询放在 Service 层
- 所有业务计算放在 Service 层
- 所有数据转换放在 Service 层
- 错误处理返回 `None` 或 `False`，由路由层转换为 HTTP 错误

**示例：**

```python
# 重构前（兼容层）
@router.get("/list")
async def list_items(enterprise_id: str):
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM table WHERE tenant_id = %s", (enterprise_id,))
            rows = await cur.fetchall()
    
    items = []
    for row in rows:
        # 复杂的数据转换逻辑
        items.append({...})
    
    return {"items": items}

# 重构后（Service 层）
async def get_items_list(tenant_id: str) -> tuple[list[dict], int]:
    """获取项目列表。"""
    async with get_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM table WHERE tenant_id = %s", (tenant_id,))
            rows = await cur.fetchall()
    
    items = []
    for row in rows:
        items.append(_row_to_dict(row))
    
    return items, len(items)

# 重构后（兼容层）
@router.get("/list")
async def list_items(enterprise_id: str):
    tenant_id = enterprise_id  # 参数映射
    items, total = await xxx_service.get_items_list(tenant_id)
    return {"items": items}
```

#### 2.3 函数命名规范

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| 列表查询 | `get_xxx_list()` | `get_diagnosis_list_items()` |
| 单项查询 | `get_xxx_detail()` | `get_task_detail()` |
| 创建 | `create_xxx()` | `create_task()` |
| 更新 | `update_xxx()` | `update_task_status()` |
| 删除 | `delete_xxx()` | `delete_task()` |
| 计算 | `calculate_xxx()` | `calculate_plan_progress()` |
| 转换 | `transform_xxx()` | `transform_report_to_frontend_format()` |
| 辅助函数 | `_helper_xxx()` | `_extract_total_score()` |

### 步骤 3：重写兼容层

#### 3.1 薄适配器模式

兼容层只做三件事：
1. **参数映射** - 旧参数名 → 新参数名
2. **调用 Service 层** - 委托业务逻辑
3. **格式转换** - 内部格式 → 前端格式（如果需要）

#### 3.2 标准模板

```python
"""前端兼容层 — /xxx 系列接口。

薄适配器：仅负责参数映射和响应格式转换，业务逻辑委托给 Service 层。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from src.services import xxx_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/xxx", tags=["XXX(兼容层)"])


@router.get("/list", summary="XXX列表(兼容)")
async def compat_xxx_list(
    enterprise_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """兼容前端 GET /xxx/list。
    
    参数映射：enterprise_id -> tenant_id
    调用 Service 层获取数据。
    """
    # 1. 参数映射
    tenant_id = enterprise_id
    
    # 2. 调用 Service 层
    items, total = await xxx_service.get_xxx_list(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    
    # 3. 返回（格式已兼容）
    return {"items": items, "total": total}


@router.get("/{id}", summary="XXX详情(兼容)")
async def compat_xxx_detail(id: str):
    """兼容前端 GET /xxx/{id}。"""
    # 调用 Service 层
    item = await xxx_service.get_xxx_detail(id)
    
    # 处理 404
    if item is None:
        raise HTTPException(status_code=404, detail="XXX不存在")
    
    return item
```

#### 3.3 错误处理模式

```python
# Service 层返回 None
async def get_xxx_detail(id: str) -> dict | None:
    # ... 查询逻辑
    if not row:
        return None
    return row

# 路由层转换为 HTTP 错误
@router.get("/{id}")
async def get_detail(id: str):
    item = await xxx_service.get_xxx_detail(id)
    if item is None:
        raise HTTPException(status_code=404, detail="不存在")
    return item
```

### 步骤 4：更新标准路由（可选）

如果存在标准路由，也更新为调用 Service 层：

```python
# src/api/routes/xxx.py

from src.services import xxx_service

@router.get("/history")
async def get_xxx_history(tenant_id: str, page: int, page_size: int):
    """标准 API：获取历史记录。"""
    skip = (page - 1) * page_size
    items, total = await xxx_service.get_xxx_list(
        tenant_id=tenant_id,
        skip=skip,
        limit=page_size,
    )
    return {"items": items, "total": total, "page": page}
```

### 步骤 5：验证和测试

#### 5.1 代码行数对比

```bash
# 重构前
Get-Content src/api/routes/compat_xxx.py | Measure-Object -Line

# 重构后
Get-Content src/api/routes/compat_xxx.py | Measure-Object -Line
Get-Content src/services/xxx_service.py | Measure-Object -Line
```

#### 5.2 运行测试

```bash
# 运行特定模块测试
pytest tests/test_xxx.py -v

# 运行所有测试
pytest tests/ -v
```

#### 5.3 手动测试

使用 API 客户端（如 Postman、curl）测试关键接口：
- 列表接口
- 详情接口
- 创建/更新/删除接口

## 📊 重构指标

### 目标指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 兼容层代码减少 | ≥ 70% | 兼容层应该非常薄 |
| Service 层代码 | 适中 | 包含所有业务逻辑 |
| 总代码变化 | -10% ~ +30% | 可能增加，但提高了复用性 |

### 已完成模块指标

| 模块 | 兼容层减少 | Service 层 | 总代码变化 |
|------|-----------|-----------|-----------|
| Diagnosis | -75% | 623 行 | -24% |
| Execution | -75% | 440 行 | +33% |

## 🎯 最佳实践

### DO ✅

1. **提取所有业务逻辑到 Service 层**
   - 数据库查询
   - 数据转换
   - 状态计算
   - 聚合逻辑

2. **保持兼容层简洁**
   - 只做参数映射
   - 只做格式转换
   - 只做错误处理

3. **使用清晰的函数命名**
   - `get_xxx_list()` - 列表查询
   - `get_xxx_detail()` - 详情查询
   - `update_xxx()` - 更新操作

4. **添加完整的文档字符串**
   - 函数说明
   - 参数说明
   - 返回值说明

5. **统一错误处理**
   - Service 层返回 `None` 或 `False`
   - 路由层转换为 HTTP 错误

### DON'T ❌

1. **不要在兼容层写业务逻辑**
   - ❌ 数据库查询
   - ❌ 复杂的数据转换
   - ❌ 状态计算

2. **不要在 Service 层处理 HTTP**
   - ❌ 抛出 HTTPException
   - ❌ 处理 HTTP 状态码
   - ❌ 解析 HTTP 请求

3. **不要重复代码**
   - ❌ 兼容层和标准路由重复实现
   - ❌ 多个函数重复相同逻辑

4. **不要过度优化**
   - ❌ 过早的性能优化
   - ❌ 过度抽象

## 🐛 常见问题

### Q1: Service 层应该返回什么格式？

**A:** 返回内部格式（字典或 Pydantic 模型）。格式转换在需要时由兼容层处理。

```python
# Service 层 - 返回内部格式
async def get_report_data(id: str) -> dict | None:
    return {
        "tenant_id": "...",
        "health_score": 75.5,
        "anomalies": [...]
    }

# 兼容层 - 转换为前端格式（如果需要）
@router.get("/report/{id}")
async def compat_report(id: str):
    report = await service.get_report_data(id)
    return service.transform_to_frontend_format(report)
```

### Q2: 如何处理复杂的参数映射？

**A:** 在兼容层做参数映射，传递给 Service 层时使用标准参数名。

```python
@router.get("/list")
async def compat_list(
    enterprise_id: str,  # 旧参数名
    pageNo: int,         # 旧参数名
    pageSize: int,       # 旧参数名
):
    # 参数映射
    tenant_id = enterprise_id
    skip = (pageNo - 1) * pageSize
    limit = pageSize
    
    # 调用 Service 层（使用标准参数名）
    items, total = await service.get_list(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    
    return {"items": items, "total": total}
```

### Q3: Service 层函数应该多大？

**A:** 遵循单一职责原则。一个函数只做一件事。如果函数超过 50 行，考虑拆分。

```python
# 好 ✅ - 单一职责
async def get_task_list(tenant_id: str) -> list[dict]:
    """获取任务列表。"""
    rows = await _query_tasks(tenant_id)
    return [_task_row_to_dict(row) for row in rows]

async def _query_tasks(tenant_id: str) -> list[dict]:
    """查询任务数据。"""
    async with get_conn() as conn:
        # ... 查询逻辑
        return rows

def _task_row_to_dict(row: dict) -> dict:
    """转换任务行为字典。"""
    return {...}

# 不好 ❌ - 职责过多
async def get_task_list_with_stats_and_aggregation(tenant_id: str):
    """获取任务列表、统计信息、聚合数据...（太多职责）"""
    # 100+ 行代码
    pass
```

### Q4: 如何处理事务？

**A:** 在 Service 层处理事务，使用 `async with get_conn()` 和 `await conn.commit()`。

```python
async def update_task_status(task_id: str, status: str) -> bool:
    """更新任务状态。"""
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ai_exec_task SET status = %s WHERE task_id = %s",
                    (status, task_id),
                )
            await conn.commit()
        return True
    except Exception:
        logger.exception("更新任务状态失败")
        return False
```

## 📖 参考资料

- [Diagnosis 模块重构总结](refactoring-diagnosis-summary.md)
- [Execution 模块重构总结](refactoring-execution-summary.md)
- [架构图和数据流](diagnosis-refactoring-architecture.md)
- [重构完成报告](../REFACTORING_COMPLETE.md)

## 🎓 学习资源

### 设计模式
- **适配器模式** - 兼容层就是适配器
- **服务层模式** - Service 层的设计理念
- **仓储模式** - Repository 层的设计理念

### 代码质量
- **SOLID 原则** - 特别是单一职责原则
- **DRY 原则** - Don't Repeat Yourself
- **KISS 原则** - Keep It Simple, Stupid

---

**文档版本：** 1.0  
**最后更新：** 2026-04-15  
**维护者：** Kiro AI
