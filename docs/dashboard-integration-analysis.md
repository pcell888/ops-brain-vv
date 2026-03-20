# 仪表盘页面对接分析报告

> 前端 `frontend/src/pages/dashboard/index.tsx` → 后端 `src/api/`  
> 分析日期: 2026-03-20

---

## 一、仪表盘页面调用的全部 API 汇总

仪表盘页面共调用 **10 个 API**（含 WebSocket），按功能分组如下：

| # | 前端调用 | 方法 | 触发时机 | 用途 |
|---|---------|------|---------|------|
| 1 | `/enterprises/{id}` | GET | 页面加载 | 获取企业详情（industry、config） |
| 2 | `/diagnosis/list?enterprise_id&skip=0&limit=1` | GET | 页面加载 | 获取最新一条诊断记录 |
| 3 | `/diagnosis/report/{diagnosisId}` | GET | 最新诊断 completed 时 | 获取诊断报告 |
| 4 | `/diagnosis/benchmarks/dimension-scores?industry=` | GET | 有报告但无 benchmark 数据时 | 雷达图行业基准 |
| 5 | `/diagnosis/start` | POST | 点击「立即诊断」 | 启动诊断 |
| 6 | `/diagnosis/{diagnosisId}/cancel` | POST | 点击「取消诊断」 | 取消诊断 |
| 7 | `/custom-dimensions/all-dimensions?enterprise_id=` | GET | 页面加载 | 获取维度配置（名称映射） |
| 8 | `/solutions/list/{diagnosisId}` | GET | 有报告时 | 获取方案列表 |
| 9 | `/solutions/generate` | POST | 点击「生成方案」 | 生成优化方案 |
| 10 | `ws://host/api/v1/ws/tasks/{enterpriseId}` | WS | 页面加载 | 实时诊断进度推送 |

---

## 二、逐项对接状态分析

### ✅ 可对接（需适配）

#### 1. 诊断历史列表 — 需路径+参数映射

| | 前端 | 后端 |
|---|------|------|
| 路径 | `GET /diagnosis/list` | `GET /diagnosis/history` |
| 参数 | `enterprise_id, skip, limit` | `tenant_id, store_id, page, page_size` |
| 返回 | `{ items: DiagnosisListItem[], total }` | `{ items: [{thread_id, tenant_id, store_id, trigger_type, created_at}], total, page, page_size }` |

**差距分析：**
- 路径不同：`/list` vs `/history`
- 参数名不同：`enterprise_id` → `tenant_id`；`skip/limit` → `page/page_size`（分页语义不同，skip 是偏移量，page 是页码）
- **返回字段严重不足**：后端只返回 `thread_id, tenant_id, store_id, trigger_type, created_at`，前端需要 `diagnosis_id, status, progress, message, error_message, health_score, anomaly_count, trigger_type, created_at`
- 前端用 `latestDiagnosisStatus` 判断是否有正在运行的诊断，后端列表不返回 `status/progress/message`

**前端改动：**
- `api.ts` 中 `diagnosisApi.list` 路径改为 `/diagnosis/history`
- 参数映射：`enterprise_id` → `tenant_id`，`skip` → `page`（需转换），`limit` → `page_size`

**后端改动（必须）：**
- 列表接口需返回 `status, progress, message, health_score, anomaly_count` 字段（从 report JSON 中提取或单独存储）
- 或新增兼容路由 `/diagnosis/list`

---

#### 2. 诊断报告 — 需路径映射 + 返回结构适配

| | 前端 | 后端 |
|---|------|------|
| 路径 | `GET /diagnosis/report/{diagnosisId}` | `GET /diagnosis/{thread_id}/report` |
| 返回 | `DiagnosisReport` 类型（见下） | 从 PG 或 LangGraph state 读取的原始 report dict |

**前端期望的 DiagnosisReport 结构：**
```typescript
{
  diagnosis_id: string;
  enterprise_id: string;
  status: string;
  health_score: {
    total_score: number;
    status: string;
    dimension_scores: [{
      dimension: string;
      score: number;
      weight: number;
      weighted_score: number;
      status: string;
      metrics_detail?: [{ name, display_name, value, unit, score, benchmark_avg, benchmark_excellent }];
    }];
    trend: { previous_score?, change?, direction? };
  };
  anomalies: [{
    id: string;
    rule_id: string;
    rule_name: string;
    metric_name: string;
    dimension: string;
    current_value: number;
    benchmark_value?: number;
    gap_percentage?: number;
    severity: 'low'|'medium'|'high'|'critical';
    root_cause_chain: string[];
    solution_tags: string[];
    unit?: string;
  }];
  root_cause_analyses: [...];
  created_at: string;
  completed_at?: string;
  benchmark_dimension_scores?: [{ dimension, score }];  // 可选
}
```

**后端实际 DiagnosisReport (models.py)：**
```python
{
  tenant_id, store_id, generated_at,
  health_score: float,                    # ← 前端期望是对象！
  dimension_scores: {dim: {score, weight}},  # ← 前端期望是数组！
  dimension_indicator_scores: {...},
  dimension_benchmarks: {...},
  anomalies: [{indicator_code, indicator_name, dimension, current_value, benchmark_avg, benchmark_excellent, deviation_pct, severity, description, root_cause}],
  root_causes: [...],
  summary: str,
}
```

**差距分析：**
- 路径不同：`/report/{id}` vs `/{id}/report`
- `health_score`：前端期望嵌套对象 `{total_score, dimension_scores[], trend}`，后端是 `float`
- `dimension_scores`：前端期望数组 `[{dimension, score, weight, status, metrics_detail}]`，后端是 dict `{dim: {score, weight}}`
- `anomalies` 字段名不同：前端用 `id/rule_name/metric_name/benchmark_value/gap_percentage/root_cause_chain/solution_tags`，后端用 `indicator_code/indicator_name/benchmark_avg/deviation_pct/description/root_cause`
- 前端需要 `trend`（上次对比），后端无此字段
- 前端需要 `benchmark_dimension_scores`，后端无此字段

**前端改动：**
- `api.ts` 路径改为 `/{id}/report`
- 需要写一个**响应适配层**，将后端返回的扁平结构转换为前端 `DiagnosisReport` 类型

**后端改动（推荐）：**
- 在 `diagnose` 节点输出时，按前端期望的结构组装 report（或在 API 层做转换）
- 增加 `trend` 计算（对比上一次报告）

---

#### 3. 启动诊断 — 需请求体字段映射

| | 前端 | 后端 |
|---|------|------|
| 路径 | `POST /diagnosis/start` | `POST /diagnosis/start` ✅ |
| 请求体 | `{ enterprise_id, trigger_type?, dimensions?, async_mode? }` | `{ tenant_id, store_id, trigger_type, triggered_by, selected_dimensions, selected_indicators }` |
| 返回 | 期望 `{ status, message?, diagnosis_id? }` | `{ thread_id, ws_url }` |

**差距分析：**
- 路径一致 ✅
- 字段不同：`enterprise_id` → `tenant_id`（缺 `store_id`）；`dimensions` → `selected_dimensions`；前端有 `async_mode` 后端无
- 返回不同：前端期望 `status/message`，后端返回 `thread_id/ws_url`

**前端改动：**
- 请求体字段映射
- 处理返回值差异（`thread_id` 作为 `diagnosis_id` 使用）

---

#### 4. 取消诊断 — 路径一致 ✅

| | 前端 | 后端 |
|---|------|------|
| 路径 | `POST /diagnosis/{diagnosisId}/cancel` | `POST /diagnosis/{thread_id}/cancel` ✅ |

完全兼容，无需改动。

---

#### 5. 方案列表 — 需路径映射 + 返回结构适配

| | 前端 | 后端 |
|---|------|------|
| 路径 | `GET /solutions/list/{diagnosisId}` | `GET /solutions/{thread_id}` |
| 返回 | `SolutionGenerateResponse` | `{ thread_id, status, adopted_plan_ids, plan_count, plans[], recommendation }` |

**差距分析：**
- 路径不同：`/list/{id}` vs `/{id}`
- 返回结构完全不同：
  - 前端期望 `solutions: SolutionSummary[]`（含 rank, solution_id, name, score, estimated_cost 等）
  - 后端返回 `plans[]`（含 plan_id, plan_name, priority_level, metrics, execution 等）
- 前端期望 `ai_recommendation`，后端返回 `recommendation`（结构不同）

**前端改动：**
- 路径改为 `/{id}`
- 需要适配层将后端 `plans` 转换为前端 `SolutionSummary` 格式

---

### ❌ 后端完全缺失

#### 6. 企业详情 — 后端无 `/enterprises` 模块

前端调用 `GET /enterprises/{id}` 获取企业详情（industry、config.analysis_period_days、config.auto_diagnosis_frequency、config.solution_sort_strategy）。

后端仅有 `/tenant-config/{tenant_id}`，返回格式为：
```json
{
  "tenant_id": "xxx",
  "config": {
    "diagnosis_trigger_mode": { "value": "manual", ... },
    "analysis_period_days": { "value": 90, ... },
    "stores": []
  }
}
```

**缺失字段：** `industry`、`name`、`scale`、`auto_diagnosis_frequency`、`solution_sort_strategy`

**解决方案：**
- 方案 A（推荐）：后端新增 `/enterprises/{id}` 兼容接口，从 `tenant_registry` 表读取并组装
- 方案 B：前端改用 `/tenant-config/{id}` 并适配返回结构

---

#### 7. 行业基准维度得分 — 后端无此接口

前端调用 `GET /diagnosis/benchmarks/dimension-scores?industry=` 获取雷达图行业基准数据。

**解决方案：**
- 后端新增此接口，从 benchmark 配置中按维度聚合计算得分
- 或在诊断报告中直接包含 `benchmark_dimension_scores` 字段

---

#### 8. 自定义维度配置 — 后端无 `/custom-dimensions` 模块

前端调用 `GET /custom-dimensions/all-dimensions?enterprise_id=` 获取所有维度配置。

仪表盘用此数据做：
- 维度显示名称映射（`dimensionNameMap`）
- 维度→首个指标映射（`dimensionFirstMetricMap`，用于钻取跳转）
- 指标显示名称映射（`metricNameMap`）
- 判断哪些维度已启用（`enabledDimensionNames`）

**解决方案：**
- 后端新增 `/custom-dimensions/all-dimensions` 接口
- 返回格式需匹配 `AllDimensionsResponse`：`{ system_dimensions, custom_dimensions, all_dimensions }`
- 每个维度需包含 `id, name, display_name, weight, is_system, enabled, metrics_config, rules_config`

---

#### 9. 方案生成 — 后端无异步任务模式

前端调用：
1. `POST /solutions/generate` → 返回 `{ task_id, status }`
2. `GET /solutions/generate/status/{taskId}` → 轮询任务状态
3. `GET /solutions/generate/active/{diagnosisId}` → 检测活跃任务

后端方案生成是在 LangGraph `generate_solutions` 节点中同步完成的，无独立的异步任务 API。

**解决方案：**
- 仪表盘页面的方案生成可暂时简化：直接跳转到方案页面，不在仪表盘做异步生成
- 或后端新增异步方案生成任务 API

---

#### 10. WebSocket — 协议不兼容

| | 前端 | 后端 |
|---|------|------|
| URL | `ws://host/api/v1/ws/tasks/{enterpriseId}` | `ws://host/api/v1/ws/diagnosis/{thread_id}` |
| 消息格式 | `TaskStatusMessage { type:'task_status', task_type, task_id, enterprise_id, status, progress, message, data }` | `WSProgressMessage { type:'progress'|'node_start'|'completed'|..., node, message, percent, ... }` |

**差距分析：**
- URL 维度不同：前端按**企业**订阅所有任务，后端按**单次诊断 thread_id** 订阅
- 消息格式完全不同

**解决方案：**
- 方案 A（推荐）：后端新增 `/ws/tasks/{enterpriseId}` 端点，内部聚合该企业所有运行中的诊断任务，转换消息格式为前端期望的 `TaskStatusMessage`
- 方案 B：前端改为按 `thread_id` 连接，但需要先知道 thread_id（启动诊断后获取）

---

## 三、对接优先级与工作量评估

### P0 — 必须完成（仪表盘基本可用）

| 项目 | 改动方 | 工作量 | 说明 |
|------|--------|--------|------|
| 诊断历史列表适配 | 前端+后端 | 中 | 后端需补充 status/progress/health_score 字段 |
| 诊断报告结构适配 | 前端 or 后端 | 大 | 核心数据结构差异大，建议后端输出时按前端格式组装 |
| 启动诊断字段映射 | 前端 | 小 | enterprise_id→tenant_id，处理返回值 |
| 企业详情接口 | 后端 | 中 | 新增 `/enterprises/{id}` 或前端改用 tenant-config |
| 维度配置接口 | 后端 | 中 | 新增 `/custom-dimensions/all-dimensions` |

### P1 — 增强功能

| 项目 | 改动方 | 工作量 | 说明 |
|------|--------|--------|------|
| WebSocket 适配 | 后端 | 大 | 新增企业级 WS 端点 + 消息格式转换 |
| 行业基准维度得分 | 后端 | 小 | 新增接口或在报告中附带 |
| 方案列表适配 | 前端 | 中 | 路径+返回结构映射 |

### P2 — 可延后

| 项目 | 改动方 | 工作量 | 说明 |
|------|--------|--------|------|
| 异步方案生成 | 后端 | 大 | 新增任务队列机制 |
| 趋势对比 | 后端 | 中 | 需对比历史报告计算 trend |

---

## 四、推荐对接策略

### 策略：后端增加适配层（推荐）

在后端新增一个 `compat` 路由模块，提供前端期望的接口路径和数据格式，内部调用现有逻辑：

1. **`GET /diagnosis/list`** → 内部调用 `list_reports()` + 从报告 JSON 提取 status/health_score/anomaly_count
2. **`GET /diagnosis/report/{id}`** → 内部调用 `get_report()` + 转换为前端 DiagnosisReport 结构
3. **`GET /enterprises/{id}`** → 从 tenant_registry 读取 + 合并 config
4. **`GET /custom-dimensions/all-dimensions`** → 返回系统内置维度配置（硬编码或从配置文件读取）
5. **`GET /diagnosis/benchmarks/dimension-scores`** → 从 benchmark 配置计算
6. **`GET /solutions/list/{id}`** → 内部调用现有 `GET /solutions/{id}` + 转换格式
7. **`WS /ws/tasks/{enterpriseId}`** → 新增企业级 WebSocket 聚合端点

### 前端最小改动清单

如果后端提供了上述适配层，前端仅需：

1. `api.ts` — `diagnosisApi.start` 的请求体字段映射（`enterprise_id` → `tenant_id`，补充 `store_id`）
2. `api.ts` — 处理 `/diagnosis/start` 返回值（`thread_id` → `diagnosis_id`）
3. `websocket.ts` — 如后端新增了 `/ws/tasks/{enterpriseId}`，无需改动；否则需改为 `/ws/diagnosis/{thread_id}`

---

## 五、数据流图

```
仪表盘页面加载
  │
  ├─ GET /enterprises/{id}          → 企业详情（industry, config）     ❌ 后端缺失
  ├─ GET /custom-dimensions/all     → 维度配置（名称映射）             ❌ 后端缺失
  ├─ GET /diagnosis/list?limit=1    → 最新诊断状态                    ⚠️ 需适配
  │   └─ if completed:
  │       ├─ GET /diagnosis/report/{id}  → 诊断报告                  ⚠️ 需适配
  │       ├─ GET /diagnosis/benchmarks/dimension-scores → 雷达基准   ❌ 后端缺失
  │       └─ GET /solutions/list/{id}    → 方案列表                  ⚠️ 需适配
  │
  ├─ WS /ws/tasks/{enterpriseId}    → 实时进度                       ❌ 协议不兼容
  │
  └─ 用户操作:
      ├─ POST /diagnosis/start      → 启动诊断                       ⚠️ 字段映射
      ├─ POST /diagnosis/{id}/cancel → 取消诊断                      ✅ 兼容
      └─ POST /solutions/generate   → 生成方案                       ❌ 后端缺失

图例: ✅ 兼容  ⚠️ 需适配  ❌ 缺失
```
