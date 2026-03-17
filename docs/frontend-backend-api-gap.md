# 前端调用诊断服务 (localhost:8000) 接口缺口调查

前端 baseURL: `/api/v1`，后端 FastAPI prefix: `/api/v1`。

## 一、路径/参数不一致（前端已有调用，后端存在但路径或参数不同）

| 前端调用 | 后端现有 | 说明 |
|----------|----------|------|
| `GET /diagnosis/list?enterprise_id,skip,limit` | `GET /diagnosis/history?tenant_id,store_id,page,page_size` | 路径与参数名均不同 |
| `GET /diagnosis/status/{diagnosisId}` | `GET /diagnosis/{thread_id}/state` | 路径不同（status/:id vs :id/state） |
| `GET /diagnosis/report/{diagnosisId}` | `GET /diagnosis/{thread_id}/report` | 路径不同（report/:id vs :id/report） |
| `GET /diagnosis/anomaly/{diagnosisId}/{anomalyId}` | `GET /diagnosis/{thread_id}/anomalies/{indicator_code}` | 路径段顺序与参数名不同 |
| `POST /diagnosis/start` body: `enterprise_id, trigger_type, dimensions?, async_mode?` | body: `tenant_id, store_id, trigger_type, triggered_by, selected_dimensions, selected_indicators` | 请求体字段不一致 |
| `GET /solutions/list/{diagnosisId}` | `GET /solutions/{thread_id}` | 路径不同（list/:id vs :id） |
| `PUT /solutions/{solutionId}/adopt` | `POST /solutions/{thread_id}/adopt` body: `plan_id` | 方法不同且后端按 thread+plan_id 采纳 |
| `GET /tracking/{trackingId}/snapshots` | `GET /track/{thread_id}/snapshots` | 前缀不同：tracking vs track |

## 二、后端完全缺失的接口（前端会 404）

### 1. 企业 /enterprises
- `GET /enterprises` — 企业列表
- `GET /enterprises/{enterpriseId}` — 企业详情
- `PATCH /enterprises/{enterpriseId}/config` — 更新企业配置
- `PATCH /enterprises/{enterpriseId}/context` — 更新企业上下文
- `POST /enterprises/{enterpriseId}/data-quality` — 数据质量评估
- `GET /enterprises/{enterpriseId}/benchmarks` — 企业基准
- `GET /enterprises/industry-benchmarks` — 行业基准列表（支持 ?industry）
- `POST /enterprises/industry-benchmarks` — 创建行业基准
- `GET /enterprises/industry-benchmarks/{id}` — 行业基准详情
- `PUT /enterprises/industry-benchmarks/{id}` — 更新
- `DELETE /enterprises/industry-benchmarks/{id}` — 删除

注：后端仅有 `/tenant-config/{tenant_id}`（GET/PUT）和 `POST /tenant-config/sync`，与前端 enterprises 语义/路径均不同。

### 2. 诊断 /diagnosis
- `GET /diagnosis/benchmarks?industry=` — 行业基准（指标级）
- `GET /diagnosis/benchmarks/dimension-scores?industry=` — 行业基准维度得分（雷达图）
- `GET /diagnosis/drill-down/{metricName}?enterprise_id,dimension,days,page,page_size` — 指标钻取

### 3. 自定义维度 /custom-dimensions
- `POST /custom-dimensions?enterprise_id=` — 创建
- `GET /custom-dimensions?enterprise_id=...` — 列表
- `GET /custom-dimensions/all-dimensions?enterprise_id=` — 所有可用维度
- `GET /custom-dimensions/{dimensionId}` — 详情
- `PUT /custom-dimensions/{dimensionId}` — 更新
- `DELETE /custom-dimensions/{dimensionId}` — 删除
- `POST /custom-dimensions/{dimensionId}/toggle` — 启用/禁用
- `POST /custom-dimensions/{dimensionId}/metrics?enterprise_id=` — 提交指标数据
- `POST /custom-dimensions/generate-rules` — 智能生成规则

### 4. 方案 /solutions
- `POST /solutions/generate` — 生成优化方案
- `GET /solutions/generate/status/{taskId}` — 生成任务状态
- `GET /solutions/generate/active/{diagnosisId}` — 诊断下活跃生成任务
- `GET /solutions/detail/{solutionId}` — 方案详情
- `POST /solutions/compare` — 方案对比（body: solutionIds[]）
- `GET /solutions/templates?category,skip,limit` — 方案模板列表
- `GET /solutions/templates/{templateId}` — 模板详情
- `PUT /solutions/{solutionId}/reject?reason=` — 拒绝方案

### 5. 执行 /execution
- `POST /execution/plans` — 创建执行计划
- `GET /execution/plans?enterprise_id,status,skip,limit` — 计划列表
- `GET /execution/plans/{planId}` — 计划摘要
- `GET /execution/plans/{planId}/gantt` — 甘特图数据
- `POST /execution/plans/{planId}/start` — 启动
- `POST /execution/plans/{planId}/pause` — 暂停
- `POST /execution/plans/{planId}/resume` — 恢复
- `GET /execution/plans/{planId}/tasks?status=` — 计划下任务列表
- `GET /execution/tasks/{taskId}` — 任务详情
- `POST /execution/tasks/{taskId}/complete` — 完成任务
- `POST /execution/tasks/{taskId}/fail` — 任务失败
- `POST /execution/tasks/{taskId}/retry` — 重试

### 6. 追踪 /tracking（前端用 tracking，后端仅有 /track 且仅一条）
- `POST /tracking/start` — 启动效果追踪
- `GET /tracking/list?enterprise_id,status,skip,limit` — 追踪列表
- `GET /tracking/{trackingId}` — 追踪摘要
- `POST /tracking/{trackingId}/snapshot` — 采集快照
- `GET /tracking/{trackingId}/analyze` — 效果分析
- `POST /tracking/{trackingId}/complete` — 完成并生成复盘报告
- `POST /tracking/{trackingId}/cancel` — 取消
- `GET /tracking/{trackingId}/trends` — 指标趋势
- `GET /tracking/{trackingId}/report` — 复盘报告
- `GET /tracking/{trackingId}/snapshots` — 快照列表
- `GET /tracking/cases/search` — 案例搜索
- `GET /tracking/cases/{caseId}` — 案例详情
- `GET /tracking/cases/similar` — 相似案例
- `GET /tracking/{trackingId}/dashboard/funnel` — 转化漏斗
- `GET /tracking/{trackingId}/dashboard/teams` — 团队对比
- `GET /tracking/{trackingId}/dashboard/ranking` — 销售排名
- `GET /tracking/{trackingId}/dashboard/summary` — 看板汇总
- `GET /tracking/snapshots/{snapshotId}/dashboard` — 快照看板

### 7. CRM /crm
- `GET /crm/leads?enterprise_id,status,limit,skip` — 线索列表
- `GET /crm/leads/{leadId}?enterprise_id=` — 线索详情
- `GET /crm/leads/stats?enterprise_id=` — 线索统计
- `POST /crm/leads/{leadId}/assign?enterprise_id=,&sales_user_id=` — 分配线索
- `GET /crm/events?enterprise_id,limit,event_type` — 事件列表

### 8. WebSocket
- 前端：`/api/v1/ws/tasks/{enterpriseId}` — 任务进度
- 前端：`/api/v1/ws/crm/{enterpriseId}` — CRM 实时
- 后端仅有：`/api/v1/ws/diagnosis/{thread_id}` — 诊断进度

---

## 三、建议

1. **仅跑通“诊断”流程**：在后端为前端已有调用增加别名或适配层（如 `/diagnosis/list` → 转发到 `/diagnosis/history` 并做参数映射；`/diagnosis/status/:id`、`/diagnosis/report/:id` 等与现有 `/:id/state`、`/:id/report` 二选一统一或同时支持）。
2. **企业/租户**：要么前端改用 `/tenant-config`，要么后端新增 `/enterprises` 系列接口（或代理到现有 tenant 逻辑）。
3. **方案**：前端期望“按 solutionId 采纳、方案详情、模板、生成任务状态”等，需在后端补充相应路由与实现，或前端先只使用“按 thread 的方案列表 + 按 thread+plan_id 采纳”。
4. **执行 / 追踪 / CRM / 自定义维度**：均为整块缺失，需按产品优先级在后端逐模块实现或前端暂时隐藏/ mock。
5. **WebSocket**：若需要任务维、CRM 维的推送，需新增 `ws/tasks/{enterpriseId}`、`ws/crm/{enterpriseId}`；若仅诊断进度，前端可统一用 `ws/diagnosis/{thread_id}`。
