# 诊断系统 ↔ wlwq 外部接口交互文档

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────┐
│  诊断系统 (ops-brain)                                    │
│                                                         │
│  ┌──────────────────────── biz-server ────────────────┐ │
│  │ crm │ metrics │ task │ notify （同一 stdio 进程）    │ │
│  └──────────────────────────┬─────────────────────────┘ │
│  ┌──────────── benchmark-server ────────────┐            │
│  └────────────────────┬────────────────────┘            │
│         BizAPIClient (统一 HTTP 封装)                     │
│         TenantRouter (租户路由 + 鉴权)                    │
└──────────────────────┼──────────────────────────────────┘
                        │
                        ▼
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
| `storeId` | string | 店铺 ID。**各统计/列表类接口原则上均携带本参数**；**可为空字符串**表示全企业汇总（不按店铺过滤）。勿将租户 ID 与店铺 ID 混用。 |
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

> **诊断范围说明**
>
> 诊断可针对 **单店铺** 或 **全企业**。区别如下：
>
> | 维度 | 店铺级诊断 | 全企业诊断（`storeId` 为空字符串） |
> |------|-----------|---------------------------|
> | 画像来源 | `GET /store/{id}` | `GET /store/list` 聚合所有店铺 |
> | 指标采集 | 各统计端点传 `storeId=<店铺ID>` | 各统计端点**仍传** `storeId`，取值为**空字符串**，后端按全企业汇总 |
> | 部门/人员 | 对应店铺的部门树 | 所有店铺的部门树合并 |
> | 任务推送 | 推送到该店铺 | 按异常指标归属店铺拆分推送 |

#### GET `/store/list`

获取企业下所有店铺列表（用于全企业诊断时聚合画像）。

**查询参数：** 无（租户由鉴权信息确定）

**响应 data：**

```json
{
  "list": [
    {
      "storeId": "s001",
      "storeName": "杭州旗舰店",
      "storeType": "retail",
      "businessMode": "mall",
      "industryCode": "retail_general",
      "province": "浙江省",
      "city": "杭州市",
      "customerCount": 3280,
      "monthlyGmv": 425000,
      "employeeCount": 18,
      "adminAccountIds": ["admin-001"]
    }
  ]
}
```

#### GET `/store/{id}`

获取店铺基础信息。

**响应 data：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `storeName` | string | 店铺名称 |
| `storeType` | string | 店铺类型 |
| `businessMode` | string | 经营模式：`mall`（商城）/ `service`（服务）/ `hybrid`（混合） |
| `classId` | string | 行业分类 ID |
| `industryCode` | string | 行业编码 |
| `province` | string | 省 |
| `city` | string | 市 |
| `county` | string | 区 |
| `customerCount` | int | 客户总数 |
| `monthlyGmv` | float | 月 GMV（商品交易总额） |
| `employeeCount` | int | 员工数 |
| `createdDays` | int | 开店天数 |
| `adminAccountIds` | string[] | 管理员账号 ID 列表 |

#### GET `/store-class/{id}`

获取行业分类详情。

**响应 data：**

```json
{
  "classCode": "retail_general",
  "className": "综合零售"
}
```

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
| `filterType` | string | 客户筛选类型：`all` 全部；`high_value` 高价值；`churn_risk` 流失风险；`new` 新客；`low_conversion` 低转化；`no_repurchase` 未复购 |
| `page` | int | 页码 |
| `pageSize` | int | 每页条数 |

**`filterType` 判定规则（以服务端实现为准）：**

| 取值 | 判定逻辑 |
|------|----------|
| `all` | 不做筛选，返回该店铺下全部客户 |
| `high_value` | 消费金额或频次高于设定阈值（如 RFM 中 R/F/M 综合或单维度达标） |
| `churn_risk` | 超过设定天数未下单（如 lastOrderDays > N），或活跃度明显下降 |
| `new` | 首单/注册时间在近 N 天内 |
| `low_conversion` | 有浏览/加购等行为但未下单或下单率低于阈值 |
| `no_repurchase` | 仅有 1 次订单，且超过设定天数未再次购买 |

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

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `clientRecordId` | string | 客户 ID（可选，按客户筛选） |

**响应 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 合同 ID |
| `amount` | float | 金额 |
| `status` | string | 状态，见下表 |

**`status` 取值：**

| 取值 | 说明 |
|------|------|
| `draft` | 草稿 |
| `pending` | 待签 |
| `signed` | 已签 |
| `executed` | 已执行 |
| `cancelled` | 已取消 |
| `expired` | 已过期 |


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

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `storeId` | string | 店铺 ID |
| `startDate` | string | 开始日期 |
| `endDate` | string | 结束日期 |
| `groupBy` | string | `day` / `week` / `month` |

**响应 data：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalGmv` | float | 总 GMV |
| `avgOrderAmount` | float | 平均客单价 |
| `orderCount` | int | 订单总数 |

#### GET `/sys-dept/tree`

获取部门树。

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `storeId` | string | 店铺 ID |

```json
{
  "list": [
    { "deptId": "d1", "deptName": "销售部", "parentId": null }
  ]
}
```

#### GET `/sys-user/list`

获取部门下用户列表。

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `deptId` | string | 部门 ID |

```json
{
  "list": [
    { "userId": 1, "userName": "销售主管", "deptId": "d1" }
  ]
}
```

---

### 3.2 metrics-server — 运营指标采集

以下**公共查询参数**适用于本节所有指标采集端点：

| 参数 | 类型 | 必传 | 说明 |
|------|------|------|------|
| `storeId` | string | 是（可为空） | 店铺 ID；**传空字符串时返回全企业汇总**（SQL 不加 `store_id` 过滤条件）。调用侧应始终带该参数。 |
| `startDate` | string | 是 | 开始日期 |
| `endDate` | string | 是 | 结束日期 |

#### GET `/client-record/statistics` — CRM 维度（线索转化率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 客户总数 |
| `newClients` | int | 新增客户数 |

#### GET `/sales-contract/statistics` — CRM 维度（线索转化率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `signedCount` | int | 签约数 |
| `totalAmount` | float | 签约总额 |

#### GET `/examine-initiate/follow-stats` — CRM 维度（平均响应时间，跟进次数）

| 字段 | 类型 | 说明 |
|------|------|------|
| `followTotal` | int | 跟进总次数 |
| `avgResponseHours` | float | 平均响应时间（小时） |

**计算方式：**

- `followTotal`：统计 `examine_initiate` 表在时间范围内（及可选 storeId）的记录条数。
- `avgResponseHours`：`examine_initiate.response_hours` 在时间范围内的平均值。

#### GET `/account-coupon/statistics` — 营销维度（优惠券核销率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalIssued` | int | 优惠券发放总数 |
| `totalUsed` | int | 已使用数 |

#### GET `/store-order/conversion-stats` — 营销维度（浏览转化率，订单转化率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `orderUsers` | int | 下单用户数 |
| `totalOrders` | int | 订单总数 |
| `completedOrders` | int | 完成订单数 |
| `newCustomers` | int | 新客户数 |

#### GET `/seckill-apply/conversion-stats` — 营销维度（秒杀转化率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalSeckillGoods` | int | 参与秒杀商品总量 |
| `soldGoods` | int | 已售出商品数 |

**计算方式：** 基于 `seckill_goods_time` 表，按时间范围和可选 storeId 过滤。

| 字段 | 计算方式 |
|------|----------|
| `totalSeckillGoods` | `SUM(goods_num)` |
| `soldGoods` | `SUM(goods_num - surplus_goods_num)` |

#### GET `/manage-data/exposure-stats` — 营销维度（浏览转化率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `browseUsers` | int | 曝光量（基于 `manage_data` 表 `date_type=1` 记录条数） |

#### GET `/store-order/repurchase-stats` — 留存维度（复购率，流失率，平均客户生命周期价值）

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalBuyers` | int | 购买总人数 |
| `repeatBuyers` | int | 复购人数 |
| `activeCustomers` | int | 活跃客户数 |
| `churnedCustomers` | int | 流失客户数 |
| `avgLifetimeValue` | float | 平均客户生命周期价值 |

**计算方式：** 基于 `store_order` 表，可按时间范围与可选 `storeId` 过滤。

| 字段 | 计算方式 |
|------|----------|
| `totalBuyers` | `COUNT(DISTINCT account_id)` |
| `repeatBuyers` | 先按 `account_id` 分组得每人订单数 `order_count`，再 `SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)` |
| `activeCustomers` | 当前实现与 `totalBuyers` 一致 |
| `churnedCustomers` | 估算值，如 `max(0, totalBuyers * 0.17)` |
| `avgLifetimeValue` | 按 `account_id` 汇总每客户订单总金额后求平均，即 所有客户累计订单金额之和 / totalBuyers（需订单金额字段） |

#### GET `/store-refund-order/statistics` — 留存维度（退款率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalCompletedOrders` | int | 已完成订单数 |
| `refundOrders` | int | 退款订单数 |

#### GET `/store-order-evaluate/statistics` — 留存维度（好评率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalReviews` | int | 评价总数 |
| `positiveReviews` | int | 好评数 |

#### GET `/store-order/conversion-stats` — 效率维度（商品订单完成率）

> 与营销维度共用同一端点，效率维度关注 `completedOrders / totalOrders`。

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalOrders` | int | 订单总数 |
| `completedOrders` | int | 完成订单数 |

#### GET `/service-order/completion-stats` — 效率维度（服务订单完成率）

| 字段 | 类型 | 说明 |
|------|------|------|
| `totalServiceOrders` | int | 服务工单总数 |
| `completedOrders` | int | 已完成工单数 |

#### GET `/store-order/shipping-stats` — 效率维度（平均发货时效）

| 字段 | 类型 | 说明 |
|------|------|------|
| `avgShippingHours` | float | 平均发货时长（小时） |

---

### 3.3 benchmark-server — 行业基准（平台中台）

> 注：以下端点调用平台中台 API（非租户 API），使用 `__platform__` 租户标识。

#### GET `/industry-trend-statistics/benchmark`

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `industryCode` | string | 行业编码 |
| `period` | string | 统计周期 |

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

支持的指标码：`lead_conversion_rate`, `response_time_avg`, `follow_up_count`, `coupon_redemption_rate`, `browse_to_order_rate`, `order_conversion_rate`, `seckill_conversion_rate`, `repurchase_rate`, `refund_rate`, `churn_rate`, `positive_review_rate`, `avg_customer_lifetime_value`, `service_completion_rate`, `avg_shipping_hours`

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

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `industryCode` | string | 行业编码 |
| `indicatorCode` | string | 指标编码 |
| `periods` | int | 最近 N 个月 |

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

创建消息提醒（一条或多条；单条时 `messages` 仅含一项）。

**请求体：**

```json
{
  "messages": [
    {
      "accountId": "admin-001",
      "title": "AI诊断报告已生成",
      "content": "共发现 3 项异常指标...",
      "type": "ai_diagnosis_report",
      "jumpUrl": "/diagnosis/report/rpt-abc123"
    },
    {
      "accountId": "admin-001",
      "title": "任务即将到期",
      "content": "任务「线索跟进」将在 1 天内截止。",
      "type": "ai_task_approaching_deadline",
      "bizId": "exec-task-001"
    }
  ]
}
```

**`jumpUrl` 与 `bizId`（均为可选，按场景填其一或都填）**

| 字段 | 含义 | 业务侧建议用法 |
|------|------|------------------|
| `jumpUrl` | **用户点击通知后要打开的前端路由或 H5 路径**（相对路径如 `/report/xxx`，或完整 URL）。 | 落库到「跳转链接」类字段；App/小程序 `onClick` 用该值做路由或 `web-view`。适用于**有固定详情页**的通知（诊断报告、方案会话、复盘页等）。 |
| `bizId` | **关联的后台业务主键**，字符串，由诊断侧生成或沿用已有 id。 | 落库到「关联业务 ID」类字段，用于列表反查、详情接口入参（如执行任务 id、会话 thread id）。适用于**任务类提醒**（分配/超期/即将到期/受阻），即使暂无独立 H5 页也可先只传 `bizId` 再在后端拼跳转。 |

**合并规则（与参考实现一致）：** 若**同时**提供 `jumpUrl` 与 `bizId`，持久化到单一关联字段时 **优先采用 `jumpUrl`**；若业务表**分列**存储跳转链接与业务 id，则应**两列分别写入**，勿只存其一。仅填 `bizId` 时，业务端可自行拼默认详情路径（如 `/tasks/{bizId}`）。

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

#### POST `/message-remind/targeted`

按人群定向推送消息。

**请求体：** 各字段含义见下表；`title` / `content` 为展示在客户端消息列表与详情中的文案。

**`type`：** 与上文「消息 `type` 枚举」一致（`ai_diagnosis_report` … `ai_targeted` 共 9 项）。**本接口为定向运营推送，应使用 `ai_targeted`**；其余类型面向诊断/任务等非「按人群圈选」场景，勿与本接口混用，除非业务统计上需自定义子类型字符串。

**示例 1 — 流失风险（`churn_risk`）**

```json
{
  "storeId": "s001",
  "targetSegment": "churn_risk",
  "title": "好久不见，为您留了一份回归礼",
  "content": "检测到您已有一段时间未在本店消费。我们为您准备了专属优惠券与会员折扣，点击消息即可查看详情，期待您的再次光临。",
  "type": "ai_targeted"
}
```

**示例 2 — 长期未复购（`no_repurchase_90d`）**

```json
{
  "storeId": "s001",
  "targetSegment": "no_repurchase_90d",
  "title": "专属老客：满减券已到账",
  "content": "您已超过 90 天未下单。我们已为您发放一张「满 200 减 30」复购券，仅限本周使用，进店或下单时自动抵扣。",
  "type": "ai_targeted"
}
```

**示例 3 — 持券未用（`coupon_expiring_soon`）**

```json
{
  "storeId": "s001",
  "targetSegment": "coupon_expiring_soon",
  "title": "您有未使用的优惠券",
  "content": "检测到您账户仍有未使用的优惠券，建议尽快使用以免过期。打开卡券中心可查看面额与适用商品。",
  "type": "ai_targeted"
}
```

**示例 4 — 曝光未转化（`low_conversion`）**

```json
{
  "storeId": "s001",
  "targetSegment": "low_conversion",
  "title": "看过还没下单？首单立减",
  "content": "您近期浏览过本店商品但尚未下单。新客专享首单立减活动进行中，限时有效，欢迎下单体验。",
  "type": "ai_targeted"
}
```

**`targetSegment`（人群标签）**

业务侧按标签解析出目标客户 `account_id` 列表后再发消息；参考实现中的圈选逻辑如下表（实际生产可按门店/行业细化）。

| 取值 | 含义（业务语义） | 参考圈选逻辑 |
|------|------------------|----------------|
| `churn_risk` | **流失风险客**：长期未再来店下单的老客 | 曾有已完成订单，但**最近一次完成订单距今超过 60 天** |
| `no_repurchase_90d` | **长期未复购**：需促活/召回 | 曾有已完成订单，但**最近一次完成订单距今超过 90 天** |
| `coupon_expiring_soon` | **持券未用**（可配合「即将过期」营销） | 存在**未使用**优惠券的账号（具体「即将过期」条件由业务规则补充） |
| `low_conversion` | **曝光/进店未转化**：有曝光或进店行为但尚未下单 | 有经营侧曝光/入店数据，且**尚无已完成订单**的账号 |

**响应 data：** `{ "sent_count": 120 }`

---

### 3.6 指标钻取 — 明细数据下钻

诊断系统在发现异常指标后，会对每个异常指标发起**钻取请求**，获取明细列表数据，用于根因分析和报告展示。

#### 钻取机制

钻取**复用已有的统计/列表端点**，通过附加查询参数切换到明细模式：

| 切换方式 | 查询参数 | 说明 |
|---------|---------|------|
| 明细模式 | `detail=true` | 统计端点不再返回聚合数，改为返回明细列表 |
| 筛选模式 | `filterType=xxx` | 列表端点按特定条件筛选 |

#### 公共查询参数

与 3.2 节相同（`storeId`、`startDate`、`endDate`），额外支持分页：

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码，从 1 开始 |
| `pageSize` | int | 每页条数，默认 20 |

#### 明细响应格式

当传入 `detail=true` 或 `filterType` 时，端点应返回分页列表：

```json
{
  "total": 58,
  "list": [
    { "字段1": "值1", "字段2": "值2", ... }
  ]
}
```

#### 各指标钻取端点与预期字段

##### CRM 维度

| 指标 | 钻取端点 | 额外参数 | 说明 |
|------|---------|---------|------|
| `lead_conversion_rate` | `GET /client-record/list` | `filterType=low_conversion` | 低转化线索客户列表 |
| `response_time_avg` | `GET /examine-initiate/follow-stats` | `filterType=slow_response` | 响应慢的协同记录（超过 24 小时未跟进） |
| `follow_up_count` | `GET /examine-initiate/follow-stats` | `detail=true` | 跟进记录明细 |

**`lead_conversion_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `client_record_id` | string | 客户 ID |
| `client_name` | string | 客户名称 |
| `contact_person` | string | 联系人 |
| `contact_number` | string | 联系电话 |
| `create_time` | string | 创建时间 |

**`response_time_avg` / `follow_up_count` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `examine_initiate_id` | string | 审批/跟进 ID |
| `content` | string | 内容 |
| `create_time` | string | 创建时间 |
| `finish_time` | string | 完成时间（仅 response_time_avg） |
| `user_name` | string | 发起人（一般是销售专员、客服或运营人员） |

##### 营销维度

| 指标 | 钻取端点 | 额外参数 | 说明 |
|------|---------|---------|------|
| `coupon_redemption_rate` | `GET /account-coupon/statistics` | `filterType=unused` | 未核销优惠券列表 |
| `browse_to_order_rate` | `GET /manage-data/exposure-stats` | `detail=true` | 浏览-下单漏斗明细 |
| `order_conversion_rate` | `GET /store-order/conversion-stats` | `detail=true` | 订单转化漏斗明细 |
| `seckill_conversion_rate` | `GET /seckill-apply/conversion-stats` | `detail=true` | 秒杀商品销售明细 |

**`coupon_redemption_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_coupon_id` | string | 用户优惠券 ID |
| `coupon_name` | string | 优惠券名称 |
| `phone` | string | 手机号 |
| `use_status` | int | 使用状态 |
| `start_time` | string | 开始时间 |
| `end_time` | string | 结束时间 |
| `create_time` | string | 创建时间 |

**`browse_to_order_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | 用户 ID |
| `browse_time` | string | 浏览时间 |
| `order_count` | int | 订单数 |
| `first_order_time` | string | 首单时间 |

> 有多少浏览了商品的用户最终产生了下单行为

**`order_conversion_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | 用户 ID |
| `order_sn` | string | 订单号 |
| `pay_time` | string | 支付时间 |
| `pay_price` | float | 实付金额 |
| `order_status` | int | 订单状态 |

> 订单转化率 = `completedOrders / totalOrders × 100`，衡量从下单到完成支付的转化效率；明细记录每笔订单的支付与状态信息，用于定位支付流失环节。

**`seckill_conversion_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `seckill_apply_id` | string | 秒杀申请 ID |
| `goods_name` | string | 商品名称 |
| `goods_num` | int | 商品数量 |
| `surplus_goods_num` | int | 剩余数量 |
| `start_time` | string | 开始时间 |
| `end_time` | string | 结束时间 |

##### 客户留存维度

| 指标 | 钻取端点 | 额外参数 | 说明 |
|------|---------|---------|------|
| `repurchase_rate` | `GET /client-record/list` | `filterType=no_repurchase` | 未复购客户列表 |
| `refund_rate` | `GET /store-refund-order/statistics` | `detail=true` | 退款订单列表 |
| `churn_rate` | `GET /client-record/list` | `filterType=churn_risk` | 流失风险客户列表 |
| `positive_review_rate` | `GET /store-order-evaluate/statistics` | `filterType=negative` | 差评订单列表 |
| `avg_customer_lifetime_value` | `GET /store-order/repurchase-stats` | `detail=true` | 客户 LTV 明细 |

**`repurchase_rate` / `churn_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `client_record_id` | string | 客户 ID |
| `client_name` | string | 客户名称 |
| `contact_number` | string | 联系电话 |
| `create_time` | string | 创建时间 |

**`refund_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `store_refund_order_id` | string | 退款单 ID |
| `store_order_id` | string | 订单 ID |
| `order_sn` | string | 订单号 |
| `refund_price` | float | 退款金额 |
| `refund_cause` | string | 退款原因 |
| `refund_apply_time` | string | 申请退款时间 |
| `refund_success_time` | string | 退款成功时间 |

**`positive_review_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `store_order_evaluate_id` | string | 评价 ID |
| `store_order_id` | string | 订单 ID |
| `star` | int | 星级 |
| `level` | int | 评价等级 |
| `content` | string | 评价内容 |
| `create_time` | string | 创建时间 |

**`avg_customer_lifetime_value` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | 用户 ID |
| `order_count` | int | 订单数 |
| `total_amount` | float | 累计金额 |
| `last_order_time` | string | 最近订单时间 |

##### 运营效率维度

| 指标 | 钻取端点 | 额外参数 | 说明 |
|------|---------|---------|------|
| `service_completion_rate` | `GET /service-order/completion-stats` | `detail=true` | 未完成服务订单列表 |
| `avg_shipping_hours` | `GET /store-order/shipping-stats` | `detail=true` | 发货时效明细 |
**`service_completion_rate` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `service_order_id` | string | 服务订单 ID |
| `order_sn` | string | 订单号 |
| `order_status` | int | 订单状态 |
| `create_time` | string | 创建时间 |
| `finish_time` | string | 完成时间 |

**`avg_shipping_hours` 明细 list 项字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `store_order_id` | string | 订单 ID |
| `order_sn` | string | 订单号 |
| `pay_time` | string | 支付时间 |
| `delivery_time` | string | 发货时间 |
| `shipping_hours` | float | 发货时效（小时） |

#### wlwq 端点改造要点

已有统计端点需支持以下扩展：

| 端点 | 新增参数 | 行为变化 |
|------|---------|---------|
| `/examine-initiate/follow-stats` | `detail=true` / `filterType=slow_response` | 返回跟进记录明细列表 |
| `/account-coupon/statistics` | `filterType=unused` | 返回未核销优惠券列表 |
| `/manage-data/exposure-stats` | `detail=true` | 返回浏览用户明细 |
| `/store-order/conversion-stats` | `detail=true` | 返回订单明细列表 |
| `/seckill-apply/conversion-stats` | `detail=true` | 返回秒杀商品明细 |
| `/store-refund-order/statistics` | `detail=true` | 返回退款订单列表 |
| `/store-order-evaluate/statistics` | `filterType=negative` | 返回差评订单列表 |
| `/store-order/repurchase-stats` | `detail=true` | 返回客户 LTV 明细 |
| `/service-order/completion-stats` | `detail=true` | 返回未完成服务订单列表 |
| `/store-order/shipping-stats` | `detail=true` | 返回发货时效明细 |

---

## 4. wlwq 需实现端点汇总

| 领域 | 端点 |
|------|------|
| **店铺/CRM** | `/store/list`, `/store/{id}`, `/store-class/{id}`, `/client-record/list`, `/client-record/{id}`, `/client-record/statistics`, `/sales-contract/list`, `/sales-contract/statistics` |
| **订单** | `/store-order/analytics`, `/store-order/conversion-stats`, `/store-order/repurchase-stats`, `/store-order/shipping-stats` |
| **营销** | `/account-coupon/statistics`, `/seckill-apply/conversion-stats`, `/manage-data/exposure-stats`, `/coupon/create`, `/coupon/distribute`, `/seckill-apply/create` |
| **跟进/审批** | `/examine-initiate/follow-stats`（含 detail/filterType 钻取）, `/examine-initiate/create` |
| **售后/评价** | `/store-refund-order/statistics`, `/store-order-evaluate/statistics` |
| **服务** | `/service-order/completion-stats` |
| **组织** | `/sys-dept/tree`, `/sys-user/list` |
| **消息** | `/message-remind/batch-create`, `/message-remind/targeted` |
| **AI 任务** | `/ai-diagnosis/exec-task/batch-create`, `/ai-diagnosis/exec-task/{id}/status` |
| **平台中台** | `/industry-trend-statistics/benchmark`, `/industry-trend-statistics/trend`, `/store-class/list` |

| **钻取扩展** | 上述 9 个统计端点需支持 `detail=true` / `filterType` 参数返回明细列表（见 3.6 节） |

**共计约 30 个端点，9 个已有端点需钻取扩展。**

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
| 秒杀转化率 | `soldGoods / totalSeckillGoods × 100` | ↑ |
| 复购率 | `repeatBuyers / totalBuyers × 100` | ↑ |
| 退款率 | `refundOrders / totalCompletedOrders × 100` | ↓ |
| 流失率 | `churnedCustomers / activeCustomers × 100` | ↓ |
| 好评率 | `positiveReviews / totalReviews × 100` | ↑ |
| 客户 LTV | `avgLifetimeValue`（直接取） | ↑ |
| 服务完成率 | `completedOrders / totalServiceOrders × 100` | ↑ |
| 平均发货时长 | `avgShippingHours`（直接取） | ↓ |
