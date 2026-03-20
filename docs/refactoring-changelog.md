# 前端 & 后端改造变动记录

## 一、侧边栏 (`frontend/src/components/layout/sidebar.tsx`)

### 之前
- 包含菜单组：CRM 实时看板、诊断报告、优化方案（推荐方案 + 方案库）、执行监控、效果分析、系统设置
- 导入了 `TeamOutlined`、`LineChartOutlined` 图标

### 之后
- **移除** CRM 实时看板菜单组
- **移除** 效果分析（Tracking）菜单组
- **移除** 优化方案下的「方案库」子菜单
- 「推荐方案」重命名为「方案管理」
- 「执行监控」重命名为「任务执行」
- 移除 `TeamOutlined`、`LineChartOutlined` 导入

---

## 二、路由 (`frontend/src/App.tsx`)

### 之前
- 包含懒加载页面：`SolutionLibraryPage`、`SolutionTemplatePage`、`TrackingPage`、`TrackingDetailPage`、`TrackingReportPage`、`TrackingCasesPage`、`TrackingCaseDetailPage`、`CRMRealtimeDashboard`
- 对应 `<Route>` 定义

### 之后
- **移除** 上述所有懒加载导入和 `<Route>` 定义
- 保留：Dashboard、DiagnosisReports、DiagnosisDetail、AnomalyDetail、DrillDown、Solutions、SolutionDiagnosis、Execution、ExecutionDetail、Settings

---

## 三、设置页 (`frontend/src/pages/settings/index.tsx`)

### 之前
- 7 个 Tab：通用设置、维度管理、基准配置、通知设置、集成设置、安全设置、团队管理
- 加载维度数据、上下文表单引用等复杂状态

### 之后
- **仅保留** 通用设置（General）Tab
- 移除所有其他 Tab 的懒加载导入
- 简化 `loadEnterpriseDetail` 只获取 `industry` 和 `name`
- `handleSave` 只调用 `enterpriseApi.updateConfig`
- 页面描述更新为「配置企业信息和诊断参数」

---

## 四、通用设置 Tab (`frontend/src/pages/settings/tabs/general-tab.tsx`)

### 之前
- 企业信息：可编辑表单（行业、规模、团队人数、预算等级）
- 包含数据质量评估功能（评估按钮、评分展示、质量报告）
- 导入 `ContextFormValues`、`INDUSTRY_OPTIONS`、`scoreColor`/`scoreLabel` 函数

### 之后
- 企业信息：**只读展示**（企业ID、企业名称、行业），使用 `Descriptions` 组件
- **移除** 预算等级、企业规模字段
- **移除** 数据质量评估整个区块
- 保留诊断配置（分析周期、自动诊断频率）和方案配置（排序策略、最大方案数）

---

## 五、方案列表页 (`frontend/src/pages/solutions/index.tsx`)

### 之前
- 支持异步方案生成（`useGenerateSolutions`、`useGenerationTask`）
- 支持方案对比（多选 + 对比弹窗）
- 支持方案拒绝（`useRejectSolution` + 拒绝弹窗）
- 支持从此页创建执行计划（`useCreateExecutionPlan`）
- 表格列包含：对比复选框、预估成本、成功率
- 包含方案详情弹窗、方案对比弹窗、拒绝弹窗

### 之后
- 方案已在诊断完成后预生成，**移除** 异步生成逻辑
- **移除** 方案对比功能（按钮、多选、弹窗）
- **移除** 方案拒绝功能
- **移除** 从此页创建执行计划
- 简化统计卡片：总方案数、已采纳、最高评分、异常数
- 简化表格列：排名、方案名称、针对异常、推荐评分、预计周期、状态、操作
- 采纳按钮仅更新状态并刷新列表

---

## 六、方案详情页 (`frontend/src/pages/solutions/[diagnosisId]/index.tsx`)

### 之前
- 单独获取方案详情（`useSolutionDetail`）
- 支持采纳、拒绝、直接执行（创建执行计划）
- 展示完整方案内容：executive_summary、problem_statement、solution_overview、implementation_roadmap、risk_assessment、success_criteria
- 展示详细执行步骤（tasks）列表
- 方案对比表包含预估成本、时长、成功率列

### 之后
- **移除** `useSolutionDetail`、`useRejectSolution`、`useCreateExecutionPlan`
- **移除** 拒绝按钮和直接执行按钮
- 简化主内容：仅展示推荐评分、实施周期、预估成功率、方案概述
- **移除** 详细文本字段和执行步骤区块
- 简化方案对比表列
- 保留「针对异常」卡片

---

## 七、执行列表页 (`frontend/src/pages/execution/index.tsx`)

### 之前
- 使用多个 hooks：`useExecutionPlanSummary`、`usePlanTasks`、`useTaskDetail`、`useGanttData`、`useCompleteTask`、`useFailTask`、`useRetryTask`、`useStartTracking`
- 包含甘特图组件 `GanttChart`
- 复杂的任务统计和详细信息展示

### 之后
- **移除** 甘特图相关 hooks 和组件
- **移除** 效果追踪入口
- 简化为执行计划列表 + 状态卡片
- 保留基本操作：启动、暂停、恢复

---

## 八、执行详情页 (`frontend/src/pages/execution/[planId]/index.tsx`)

### 之前
- 支持表格/甘特图视图切换（`Segmented` 组件）
- 使用 `useGanttData` 获取甘特图数据
- 复杂的任务流程图展示

### 之后
- **移除** 视图切换，默认任务列表视图
- **移除** 甘特图数据获取和展示
- 简化任务表格：名称、类型、状态、进度、时间
- 任务操作简化为手动完成和重试

---

## 九、钻取限制

### 之前
- 所有指标均可点击钻取

### 之后
- **仅异常指标** 提供钻取入口（在仪表盘和诊断详情页的入口处控制）
- 钻取页面本身结构不变

---

## 十、后端新增兼容接口

### 10.1 方案采纳 (`src/api/routes/compat_solutions.py`)

**新增** `PUT /solutions/{solutionId}/adopt`
- 遍历诊断线程查找包含该 plan_id 的 thread
- 调用内部 `adopt_plan` 完成采纳

### 10.2 方案详情 (`src/api/routes/compat_solutions.py`)

**新增** `GET /solutions/detail/{solutionId}`
- 从 LangGraph state 中提取方案详情
- 转换为前端 `SolutionDetail` 结构（含 related_anomalies、tasks）

### 10.3 指标钻取 (`src/api/routes/compat_diagnosis.py`)

**新增** `GET /diagnosis/drill-down/{metricName}`
- 参数：enterprise_id、dimension、days、page、page_size
- 使用 `INDICATOR_META` 验证指标有效性和可钻取性
- 通过指标→表映射（`_INDICATOR_TABLE_MAP`）查询 wlwq 业务库
- 使用 `DRILL_ITEM_FIELDS` 和 `DRILL_FIELD_LABELS` 控制返回字段和标签
- 返回分页数据 + 字段标签

### 10.4 执行管理 (`src/api/routes/compat_execution.py`) — 新文件

**新增接口：**
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/execution/plans` | 执行计划列表（按 plan_id 分组聚合） |
| GET | `/execution/plans/{planId}` | 执行计划摘要 |
| GET | `/execution/plans/{planId}/tasks` | 计划任务列表 |
| POST | `/execution/plans/{planId}/start` | 启动计划 |
| POST | `/execution/plans/{planId}/pause` | 暂停计划 |
| POST | `/execution/plans/{planId}/resume` | 恢复计划 |
| POST | `/execution/tasks/{taskId}/complete` | 完成任务 |
| POST | `/execution/tasks/{taskId}/fail` | 标记任务失败 |
| POST | `/execution/tasks/{taskId}/retry` | 重试任务 |

### 10.5 效果追踪 (`src/api/routes/compat_tracking.py`) — 新文件

**新增接口：**
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tracking/start` | 启动效果追踪 |
| GET | `/tracking/list` | 追踪列表 |
| GET | `/tracking/{trackingId}` | 追踪摘要 |
| POST | `/tracking/{trackingId}/snapshot` | 采集快照 |
| GET | `/tracking/{trackingId}/analyze` | 效果分析 |
| POST | `/tracking/{trackingId}/complete` | 完成追踪（生成复盘报告） |
| POST | `/tracking/{trackingId}/cancel` | 取消追踪 |
| GET | `/tracking/{trackingId}/trends` | 指标趋势 |
| GET | `/tracking/{trackingId}/report` | 复盘报告 |
| GET | `/tracking/{trackingId}/snapshots` | 快照列表 |
| GET | `/tracking/cases/search` | 案例搜索 |
| GET | `/tracking/cases/similar` | 相似案例 |
| GET | `/tracking/cases/{caseId}` | 案例详情 |
| GET | `/tracking/{trackingId}/dashboard/*` | 看板数据（漏斗/团队/排名/汇总） |
| GET | `/tracking/snapshots/{snapshotId}/dashboard` | 快照看板 |

### 10.6 路由注册 (`src/api/main.py`)

**新增** `compat_execution` 和 `compat_tracking` 路由器导入和注册

---

## 十一、效果追踪模块恢复

### 之前（误删）
- 侧边栏移除了「效果分析」菜单组
- 路由移除了 Tracking 相关的 5 个页面路由
- 后端无追踪兼容接口

### 之后（已恢复）
- 侧边栏恢复「效果分析 → 效果追踪」菜单项
- 路由恢复 5 个页面：TrackingPage、TrackingDetailPage、TrackingReportPage、TrackingCasesPage、TrackingCaseDetailPage
- 后端新增 `compat_tracking.py` 兼容层（18 个接口），基于 `ai_effect_tracking`、`ai_effect_snapshot`、`ai_review_report`、`ai_solution_knowledge` 表
