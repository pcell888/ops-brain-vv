# wlwq 企业服务 API 对接文档

## 概述

wlwq 为模拟业务系统 FastAPI 应用，供 MCP（如 crm-server、notify-server、task-server、metrics-server）调用，数据来自 MySQL 库 `wlwq-enterprise-service`。

- **服务名**: wlwq-enterprise-service  
- **默认 Base URL**: `http://localhost:8200`（可配置租户注册表 `tenant_registry` 中的 `base_url`）  
- **统一响应**: `{"code": 0, "data": ..., "msg": "success"}`，非 0 为异常

---

## 1. 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

**响应示例**: `{"status": "ok", "service": "wlwq-enterprise-service"}`

---

## 2. 店铺与行业 (store)

供 MCP crm-server `get_store_profile` 等调用。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/store/{store_id}` | 店铺画像 |
| GET | `/store-class/{class_id}` | 行业分类 |

**GET /store/{store_id}**  
响应 `data`: storeName, storeType, classId, industryCode, province, city, county, customerCount, monthlyGmv, employeeCount, createdDays, adminAccountIds 等。

**GET /store-class/{class_id}**  
响应 `data`: classCode, className。

---

## 3. AI 诊断执行任务 (ai-diagnosis)

前缀: `/ai-diagnosis/exec-task`。对接 task-server 创建执行任务及 5.2.3 推送落地。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ai-diagnosis/exec-task/batch-create` | 批量创建执行任务 |
| PUT | `/ai-diagnosis/exec-task/{task_id}/status` | 更新任务状态 |

**POST batch-create**  
Body: `storeId`, `planId`, `tasks[]`。  
响应 `data`: `tasks`（含生成的 task_id）, `count`。

**PUT {task_id}/status**  
Body: `status`, 可选 `progress`, `remark`。

---

## 4. 消息提醒与记录 (message)

供 MCP notify-server 调用。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/message-remind/batch-create` | 批量创建消息提醒 |
| POST | `/message-remind/create` | 单条创建消息提醒 |
| POST | `/message-record/create` | 创建消息记录 |
| POST | `/message-remind/targeted` | 按人群定向推送（5.2.3） |

**POST /message-remind/targeted**  
Body: `storeId`, `targetSegment`（枚举: churn_risk \| no_repurchase_90d \| coupon_expiring_soon \| low_conversion）, `title`, `content`, `type`。  
响应 `data`: `sent_count`。

---

## 5. 客户记录 (client-record)

前缀: `/client-record`。对接 MCP metrics/crm 的 client-record 能力。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/client-record/statistics` | 客户数等统计 |
| GET | `/client-record/list` | 客户记录列表（分页） |
| GET | `/client-record/{client_record_id}` | 单条客户记录 |

**GET statistics**  
Query: `storeId`, `startDate`, `endDate`（均可选）。  
响应 `data`: `total`。

**GET list**  
Query: `storeId`, `startDate`, `endDate`, `clientRecordId`, `filterType`, `page`(默认 1), `pageSize`(默认 20)。  
响应 `data`: `list`, `total`。

---

## 6. 销售合同 (sales-contract)

前缀: `/sales-contract`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sales-contract/statistics` | 签约数等 |
| GET | `/sales-contract/list` | 合同列表 |

**GET statistics**  
Query: `storeId`, `startDate`, `endDate`。  
响应 `data`: `signedCount`。

**GET list**  
Query: `clientRecordId`, `page`, `pageSize`。  
响应 `data`: `list`, `total`。

---

## 7. 审批/跟进 (examine-initiate)

前缀: `/examine-initiate`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/examine-initiate/follow-stats` | 跟进统计 |
| GET | `/examine-initiate/turnaround-stats` | 审批时效 |
| POST | `/examine-initiate/create` | 创建审批/跟进单 |

**GET follow-stats**  
Query: `storeId`, `startDate`, `endDate`。  
响应 `data`: `followTotal`, `avgResponseHours`。

**GET turnaround-stats**  
Query: 同上。  
响应 `data`: `onTimeRate`。

**POST create**  
Body: `storeId`, `title`, `content`。  
响应 `data`: `id`。

---

## 8. 优惠券与秒杀 (coupon)

供 MCP task-server create_coupon_campaign / create_seckill_activity 调用。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/coupon/create` | 创建优惠券 |
| POST | `/coupon/distribute` | 定向发放优惠券 |
| POST | `/seckill-apply/create` | 创建秒杀活动 |

**POST /coupon/create**  
Body: `storeId`, `couponName`, `couponType`, `fullPrice`, `reducePrice`, `startTime`, `endTime`。  
响应 `data`: `couponId`。

**POST /coupon/distribute**  
Body: `targetCustomers`（如 "all"）等。  
响应 `data`: `count`, `targetCustomers`。

**POST /seckill-apply/create**  
Body: `storeId`, `title`, `startTime`, `endTime`。  
响应 `data`: `id`。

---

## 9. 部门与用户 (sys)

供 MCP crm-server get_dept_structure 等调用。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/sys-dept/tree` | 部门树 |
| GET | `/sys-user/list` | 用户列表 |

**GET /sys-dept/tree**  
Query: `storeId`（可选）。  
响应 `data`: `list`，项含 `deptId`, `deptName`, `parentId`。

**GET /sys-user/list**  
Query: `deptId`（可选）。  
响应 `data`: `list`，项含 `userId`, `userName`, `deptId`。

---

## 10. 统计类 (mock-stats)

无对应表时返回模拟数据，供 MCP 指标/报表使用。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/service-order/completion-stats` | 服务单完成率 |
| GET | `/store-order/shipping-stats` | 发货时效 |
| GET | `/account-coupon/statistics` | 优惠券发放/使用 |
| GET | `/manage-data/exposure-stats` | 曝光用户数 |
| GET | `/store-order/conversion-stats` | 订单转化/新客 |
| GET | `/store-activities/roi` | 活动 ROI |
| GET | `/store-refund-order/statistics` | 退款统计 |
| GET | `/store-order-evaluate/statistics` | 评价统计 |
| GET | `/store-order/repurchase-stats` | 复购/流失/ LTV |
| GET | `/stock/statistics` | 库存（缺货/滞销/周转） |
| GET | `/store-goods/statistics` | 商品 SKU 数 |

以上统计接口统一 Query（可选）: `storeId`, `startDate`, `endDate`。  
响应 `data` 字段见各路由实现（如 completionRate、avgShippingHours、totalIssued、totalUsed、browseUsers、orderUsers、totalOrders、completedOrders、newCustomers、totalSpend、refundOrders、totalReviews、positiveReviews、totalBuyers、repeatBuyers、activeCustomers、churnedCustomers、avgLifetimeValue、stockoutSku、overstockSku、avgTurnoverDays、totalSku、activeSku 等）。

---

## 环境与配置

- **MySQL**: 环境变量 `WLWQ_MYSQL_HOST`、`WLWQ_MYSQL_PORT`、`WLWQ_MYSQL_USER`、`WLWQ_MYSQL_PASSWORD`、`WLWQ_MYSQL_DATABASE`（默认库名 `wlwq-enterprise-service`）。
- **租户**: 对接方通过租户 ID 解析 Base URL（如 `wlwq_local` → `http://localhost:8200`），见 `tenant_registry` 或项目内 `scripts/init_tenant_registry.py`、`src/core/db_init.py`。
- **本地调试**: 可执行 `wlwq-cli.py --base-url http://127.0.0.1:8200` 做健康与关键 API 检查。

---

## OpenAPI

服务启动后可通过 `http://<base_url>/docs` 查看 Swagger UI，`/openapi.json` 获取 OpenAPI 规范。
