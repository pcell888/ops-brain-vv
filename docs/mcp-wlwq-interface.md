# 诊断系统 ↔ wlwq 外部接口交互文档

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────┐
│  诊断系统 (ops-brain)                                    │
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────┐ ┌─────┐ │
│  │  crm    │ │ metrics │ │benchmark │ │ task │ │notif│ │
│  │ server  │ │ server  │ │ server   │ │server│ │y srv│ │
│  └────┬────┘ └────┬────┘ └────┬─────┘ └──┬───┘ └──┬──┘ │
│       └──────┬────┴─────┬─────┘          │        │    │
│         BizAPIClient (统一 HTTP 封装)     │        │    │
│              │                           │        │    │
│         TenantRouter (租户路由 + 鉴权)    │        │    │
└──────────────┼───────────────────────────┼────────┼────┘
               │                           │        │
               ▼                           ▼        ▼
┌─────────────────────────────────────────────────────────┐
│  wlwq 业务系统 (各租户独立部署)                            │
│  base_url = tenant_registry.api_base_url                │
└─────────────────────────────────────────────────────────┘
```

### 通信模式

- 诊断系统通过 `BizAPIClient` 统一发起 HTTP 请求
- `TenantRouter` 根据 `tenant_id` 解析目标企业的 `api_base_url` 和鉴权信息
- 租户路由优先查 Redis 缓存，未命中查 PostgreSQL `tenant_registry` 表
- 单次请求超时 **15s**，超时后抛异常

### 鉴权方式

| auth_type | 请求头 | 说明 |
|-----------|--------|------|
| `token`   | `Authorization: Bearer {credential}` | JWT / API Token |
| `hmac`    | `X-Service-Signature: {credential}` | HMAC 签名 |

凭证在 `tenant_registry` 表中加密存储（Fernet），运行时解密注入。

---

## 2. 公共约定

### 请求格式

- **GET** 请求：参数通过 query string 传递
- **POST / PUT** 请求：参数通过 JSON body 传递
- Content-Type: `application/json`

### 响应格式

wlwq 端点应返回以下标准格式：

```json
{
  "code": 0,
  "msg": "success",
  "data": { ... }
}
```

`code` 为 `0` / `200` / `"0"` / `"200"` 视为成功，`BizAPIClient` 自动提取 `data` 字段返回。

### 公共查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `storeId` | string | 店铺 ID |
| `startDate` | string | 起始日期，格式 `YYYY-MM-DD` |
| `endDate` | string | 结束日期，格式 `YYYY-MM-DD` |
| `page` | int | 页码，从 1 开始 |
| `pageSize` | int | 每页条数，默认 20 |

### 分页响应结构

```json
{
  "total": 100,
  "list": [ ... ]
}
```

---

## 3. 端点明细

### 3.1 crm-server — 客户数据与企业画像

#### GET `/store/{id}`

获取店铺基础信息。

**响应 data：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `storeName` | string | 店铺名称 |
| `storeType` | string | 店铺类型 |
| `classId` | string | 行业分类 ID |
| `industryCode` | string | 行业编码 |
| `province` | string | 省 |
| `city` | string | 市 |
| `county` | string | 区 |
| `customerCount` | int | 客户总数 |
| `monthlyGmv` | float | 月 GMV |
| `employeeCount` | int | 员工数 |
| `createdDays` | int | 开店天数 |
| `adminAccountIds` | string[] | 管理员账号 ID 列表 |

#### GET `/store-class/{id}`

获取行业分类详情。

| 字段 | 类型 | 说明 |
|------|------|------|
| `classCode` | string | 行业编码 |
| `className` | string | 行业名称 |

#### GET `/client-record/list`

获取客户列表（支持筛选）。

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `storeId` | string | 店铺 ID |
| `filterType` | string | `all` / `high_value` / `churn_risk` / `new` / `low_conversion` / `no_repurchase` |
| `page` | int | 页码 |
| `pageSize` | int | 每页条数 |

**响应 data：**

```json
{
  "total": 3280,
  "list": [
    {
      "id": "c1",
      "name": "张三",
      "phone": "138****1234",
      "tags": ["high_value"],
      "lastOrderDays": 5
    }
  ]
}
```

#### GET `/client-record/{id}`

获取单个客户详情。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 客户 ID |
| `name` | string | 客户名称 |
| `phone` | string | 手机号（脱敏） |
| `totalOrders` | int | 总订单数 |
| `totalAmount` | float | 总消费金额 |

#### GET `/sales-contract/list`

获取销售合同列表。

**查询参数：** `clientRecordId`（可选，按客户筛选）

```json
{
  "total": 2,
  "list": [
    { "id": "sc1", "amount": 5000, "status": "signed" }
  ]
}
```

#### GET `/store-order/analytics`

获取订单分析数据。

**查询参数：** `storeId`, `startDate`, `endDate`, `groupBy`(`day`/`week`/`month`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalGmv` | float | 总 GMV |
| `avgOrderAmount` | float | 平均客单价 |
| `orderCount` | int | 订单总数 |

#### GET `/sys-dept/tree`

获取部门树。

**查询参数：** `storeId`

```json
{
  "list": [
    { "deptId": "d1", "deptName": "销售部", "parentId": null }
  ]
}
```

#### GET `/sys-user/list`

获取部门下用户列表。

**查询参数：** `deptId`

```json
{
  "list": [
    { "userId": 1, "userName": "销售主管", "deptId": "d1" }
  ]
}
```

---

### 3.2 metrics-server — 运营指标采集

所有指标采集端点均需 `storeId`, `startDate`, `endDate` 参数。

#### GET `/client-record/statistics` — CRM 维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 客户总数 |
| `newClients` | int | 新增客户数 |

#### GET `/sales-contract/statistics` — CRM 维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `signedCount` | int | 签约数 |
| `totalAmount` | float | 签约总额 |

#### GET `/examine-initiate/follow-stats` — CRM 维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `followTotal` | int | 跟进总次数 |
| `avgResponseHours` | float | 平均响应时间（小时） |

#### GET `/account-coupon/statistics` — 营销维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalIssued` | int | 优惠券发放总数 |
| `totalUsed` | int | 已使用数 |

#### GET `/store-order/conversion-stats` — 营销维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `orderUsers` | int | 下单用户数 |
| `totalOrders` | int | 订单总数 |
| `completedOrders` | int | 完成订单数 |
| `newCustomers` | int | 新客户数 |

#### GET `/store-activities/roi` — 营销维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalSpend` | float | 营销总花费 |

#### GET `/manage-data/exposure-stats` — 营销维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `browseUsers` | int | 浏览用户数 |

#### GET `/store-order/repurchase-stats` — 留存维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalBuyers` | int | 购买总人数 |
| `repeatBuyers` | int | 复购人数 |
| `activeCustomers` | int | 活跃客户数 |
| `churnedCustomers` | int | 流失客户数 |
| `avgLifetimeValue` | float | 平均客户生命周期价值 |

#### GET `/store-refund-order/statistics` — 留存维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalCompletedOrders` | int | 已完成订单数 |
| `refundOrders` | int | 退款订单数 |

#### GET `/store-order-evaluate/statistics` — 留存维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalReviews` | int | 评价总数 |
| `positiveReviews` | int | 好评数 |

#### GET `/examine-initiate/turnaround-stats` — 效率维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `onTimeRate` | float | 按时完成率（%） |

#### GET `/service-order/completion-stats` — 效率维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalServiceOrders` | int | 服务工单总数 |
| `completedOrders` | int | 已完成工单数 |

#### GET `/store-order/shipping-stats` — 效率维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `avgShippingHours` | float | 平均发货时长（小时） |

#### GET `/stock/statistics` — 库存维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `stockoutSku` | int | 缺货 SKU 数 |
| `overstockSku` | int | 积压 SKU 数 |
| `avgTurnoverDays` | float | 平均周转天数 |

#### GET `/store-goods/statistics` — 库存维度

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalSku` | int | SKU 总数 |
| `activeSku` | int | 在售 SKU 数 |

---

### 3.3 benchmark-server — 行业基准（平台中台）

> 注：以下端点调用平台中台 API（非租户 API），使用 `__platform__` 租户标识。

#### GET `/industry-trend-statistics/benchmark`

**查询参数：** `industryCode`, `period`

**响应 data：**

```json
{
  "benchmarks": {
    "lead_conversion_rate": {
      "avg_value": 5.2,
      "median_value": 4.8,
      "excellent_value": 8.5
    }
  }
}
```

支持的指标码：`lead_conversion_rate`, `response_time_avg`, `follow_up_count`, `coupon_redemption_rate`, `browse_to_order_rate`, `order_conversion_rate`, `customer_acquisition_cost`, `repurchase_rate`, `refund_rate`, `churn_rate`, `positive_review_rate`, `avg_customer_lifetime_value`, `service_completion_rate`, `avg_shipping_hours`, `task_on_time_rate`, `stock_turnover_days`, `stockout_rate`, `overstock_rate`

#### GET `/store-class/list`

获取行业列表。

```json
[
  { "classCode": "retail_general", "className": "综合零售" },
  { "classCode": "food_bev", "className": "餐饮" },
  { "classCode": "beauty", "className": "美业" }
]
```

#### GET `/industry-trend-statistics/trend`

**查询参数：** `industryCode`, `indicatorCode`, `periods`（最近 N 个月）

```json
{
  "trends": [
    { "period": "2026-01", "value": 5.0 },
    { "period": "2026-02", "value": 5.3 }
  ]
}
```

---

### 3.4 task-server — 任务创建与推送

#### POST `/ai-diagnosis/exec-task/batch-create`

批量创建执行任务。

**请求体：**

```json
{
  "storeId": "s001",
  "planId": "plan-001",
  "tasks": [
    {
      "task_name": "优化客户跟进流程",
      "description": "...",
      "assignee_user_id": 1,
      "assignee_dept_id": "d1",
      "deadline": "2026-04-01",
      "priority": "high",
      "related_resources": []
    }
  ]
}
```

**响应 data：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `tasks` / `list` | array | 已创建任务列表 |
| `count` | int | 创建数量 |

#### PUT `/ai-diagnosis/exec-task/{id}/status`

更新任务执行状态。

**请求体：**

```json
{
  "status": "in_progress",
  "progress": 0.5,
  "remark": "进展说明"
}
```

`status` 枚举：`pending` | `in_progress` | `completed` | `paused` | `cancelled`

#### POST `/examine-initiate/create`

发起 OA 审批流程。

**请求体：**

```json
{
  "storeId": "s001",
  "title": "AI诊断方案审批",
  "content": "...",
  "approverUserId": 1,
  "bizType": "ai_diagnosis",
  "bizId": "plan-001"
}
```

**响应 data：** `{ "id": "approval-001" }`

#### POST `/coupon/create`

创建优惠券。

**请求体：**

```json
{
  "storeId": "s001",
  "couponName": "满100减20",
  "couponType": 1,
  "fullPrice": 100,
  "reducePrice": 20,
  "startTime": "2026-03-16",
  "endTime": "2026-04-16"
}
```

**响应 data：** `{ "couponId": "coupon-001" }`

#### POST `/coupon/distribute`

派发优惠券。

**请求体：**

```json
{
  "storeId": "s001",
  "couponId": "coupon-001",
  "targetCustomers": "all"
}
```

**响应 data：** `{ "count": 500 }`

#### POST `/seckill-apply/create`

创建秒杀活动。

**请求体：** 活动配置 JSON（`storeId` + 自定义字段）

**响应 data：** `{ "id": "seckill-001" }`

---

### 3.5 notify-server — 消息通知推送

#### POST `/message-remind/batch-create`

批量创建消息提醒。

**请求体：**

```json
{
  "messages": [
    {
      "accountId": "admin-001",
      "title": "AI诊断报告已生成",
      "content": "共发现 3 项异常指标...",
      "type": "ai_diagnosis_report",
      "jumpUrl": "/report/xxx",
      "bizId": "task-001"
    }
  ]
}
```

消息 `type` 枚举：

| type | 说明 |
|------|------|
| `ai_diagnosis_report` | 诊断报告通知 |
| `ai_weekly_digest` | 周度诊断报告 |
| `ai_plan_adoption` | 方案待采纳通知 |
| `ai_review_report` | 复盘报告通知 |
| `ai_task_assignment` | 任务分配通知 |
| `ai_task_overdue` | 任务超期提醒 |
| `ai_task_approaching_deadline` | 任务即将到期 |
| `ai_task_blocked` | 任务受阻提醒 |
| `ai_targeted` | 定向客户推送 |

#### POST `/message-remind/create`

创建单条消息提醒（字段同上，去掉外层 `messages` 包裹）。

#### POST `/message-record/create`

消息记录留存（用于消息历史查询）。

**请求体：**

```json
{
  "storeId": "s001",
  "type": "ai_diagnosis_report",
  "title": "...",
  "content": "...",
  "bizId": "xxx",
  "userId": 1
}
```

#### POST `/message-remind/targeted`

按人群定向推送消息。

**请求体：**

```json
{
  "storeId": "s001",
  "targetSegment": "churn_risk",
  "title": "专属福利",
  "content": "...",
  "type": "ai_targeted"
}
```

`targetSegment` 枚举：`churn_risk` | `no_repurchase_90d` | `coupon_expiring_soon` | `low_conversion`

**响应 data：** `{ "sent_count": 120 }`

---

## 4. wlwq 需实现端点汇总

| 领域 | 端点 |
|------|------|
| **店铺/CRM** | `/store/{id}`, `/store-class/{id}`, `/client-record/list`, `/client-record/{id}`, `/client-record/statistics`, `/sales-contract/list`, `/sales-contract/statistics` |
| **订单** | `/store-order/analytics`, `/store-order/conversion-stats`, `/store-order/repurchase-stats`, `/store-order/shipping-stats` |
| **营销** | `/account-coupon/statistics`, `/store-activities/roi`, `/manage-data/exposure-stats`, `/coupon/create`, `/coupon/distribute`, `/seckill-apply/create` |
| **跟进/审批** | `/examine-initiate/follow-stats`, `/examine-initiate/turnaround-stats`, `/examine-initiate/create` |
| **售后/评价** | `/store-refund-order/statistics`, `/store-order-evaluate/statistics` |
| **服务/库存** | `/service-order/completion-stats`, `/stock/statistics`, `/store-goods/statistics` |
| **组织** | `/sys-dept/tree`, `/sys-user/list` |
| **消息** | `/message-remind/create`, `/message-remind/batch-create`, `/message-remind/targeted`, `/message-record/create` |
| **AI 任务** | `/ai-diagnosis/exec-task/batch-create`, `/ai-diagnosis/exec-task/{id}/status` |
| **平台中台** | `/industry-trend-statistics/benchmark`, `/industry-trend-statistics/trend`, `/store-class/list` |

**共计约 30 个端点。**

---

## 5. 指标计算公式

诊断系统基于 wlwq 返回的原始数据在本地计算指标值：

| 指标 | 公式 | 方向 |
|------|------|------|
| 线索转化率 | `signedCount / total × 100` | ↑ |
| 平均响应时间 | `avgResponseHours`（直接取） | ↓ |
| 跟进次数 | `followTotal`（直接取） | ↑ |
| 优惠券核销率 | `totalUsed / totalIssued × 100` | ↑ |
| 浏览-下单转化率 | `orderUsers / browseUsers × 100` | ↑ |
| 订单转化率 | `completedOrders / totalOrders × 100` | ↑ |
| 获客成本 | `totalSpend / newCustomers` | ↓ |
| 复购率 | `repeatBuyers / totalBuyers × 100` | ↑ |
| 退款率 | `refundOrders / totalCompletedOrders × 100` | ↓ |
| 流失率 | `churnedCustomers / activeCustomers × 100` | ↓ |
| 好评率 | `positiveReviews / totalReviews × 100` | ↑ |
| 客户 LTV | `avgLifetimeValue`（直接取） | ↑ |
| 服务完成率 | `completedOrders / totalServiceOrders × 100` | ↑ |
| 平均发货时长 | `avgShippingHours`（直接取） | ↓ |
| 任务按时率 | `onTimeRate`（直接取） | ↑ |
| 库存周转天数 | `avgTurnoverDays`（直接取） | ↓ |
| 缺货率 | `stockoutSku / totalSku × 100` | ↓ |
| 积压率 | `overstockSku / totalSku × 100` | ↓ |
