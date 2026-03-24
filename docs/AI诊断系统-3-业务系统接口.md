# Ai诊断系统接口文档

## 概述

本文档按 `CRM-AI-指标接口文档.md` 的格式整理，并已按代码中的真实返回对象校对响应字段。

---

## 一、客户数据与企业画像

### 1.1 获取客户列表（支持筛选)

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/list` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<PageInfo<LifecycleUserVO>>` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| storeId | String | 否 | 店铺ID |
| filterType | String | 否 | `all/high_value/churn_risk/new/low_conversion/no_repurchase` |
| pageNo | Integer | 否 | 页码 |
| pageSize | Integer | 否 | 每页条数 |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `PageInfo<LifecycleUserVO>`。

#### 响应字段说明（PageInfo）

| 字段名 | 类型 | 说明 |
|---|---|---|
| list | Array | 数据列表 |
| total | Long | 总记录数 |
| pageNum | Integer | 当前页 |
| pageSize | Integer | 每页条数 |

#### 响应字段说明（LifecycleUserVO）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | String | 客户ID |
| name | String | 客户名称 |
| phone | String | 手机号（脱敏） |
| totalOrders | Integer | 总订单数 |
| totalAmount | BigDecimal | 总消费金额 |
| accountId | String | 用户ID |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "list": [
      {
        "id": "10001",
        "name": "张三",
        "phone": "138****5678",
        "totalOrders": 6,
        "totalAmount": 1234.56,
        "accountId": "10001"
      }
    ],
    "total": 1,
    "pageNum": 1,
    "pageSize": 10
  }
}
```

---

### 1.2 获取单个客户详情

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/detail` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<LifecycleUserVO>` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | String | 是 | 客户ID |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `LifecycleUserVO`。

#### 响应字段说明（LifecycleUserVO）

同 1.1。

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "id": "10001",
    "name": "张三",
    "phone": "138****5678",
    "totalOrders": 6,
    "totalAmount": 1234.56,
    "accountId": "10001"
  }
}
```

---

### 1.3 获取销售合同列表（支持筛选)

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/saleContractList` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<PageInfo<SalesContractVo>>` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| clientRecordId | String | 否 | 客户档案ID（默认 `0`） |
| pageNo | Integer | 否 | 页码 |
| pageSize | Integer | 否 | 每页条数 |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `PageInfo<SalesContractVo>`。

#### 响应字段说明（SalesContractVo）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | String | 合同ID |
| amount | float | 金额 |
| status | String | 审核状态 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "list": [
      {
        "id": "C1001",
        "amount": 88888.0,
        "status": "3"
      }
    ],
    "total": 1,
    "pageNum": 1,
    "pageSize": 10
  }
}
```

---

### 1.4 获取订单分析数据（支持筛选)

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/orderList` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<PageInfo<ServiceOrderVo>>` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| startDate | String | 是 | 开始日期 |
| endDate | String | 是 | 结束日期 |
| storeId | String | 否 | 店铺ID |
| groupBy | String | 否 | `day/week/month` |
| pageNo | Integer | 否 | 页码 |
| pageSize | Integer | 否 | 每页条数 |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `PageInfo<ServiceOrderVo>`。

#### 响应字段说明（ServiceOrderVo）

| 字段名 | 类型 | 说明 |
|---|---|---|
| totalGmv | float | 总GMV |
| orderCount | int | 订单总数 |
| avgOrderAmount | float | 平均客单价 |
| groupDate | String | 分组日期 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "list": [
      {
        "totalGmv": 3456.78,
        "orderCount": 12,
        "avgOrderAmount": 288.07,
        "groupDate": "2026-03-21"
      }
    ],
    "total": 1,
    "pageNum": 1,
    "pageSize": 10
  }
}
```

---

### 1.5 获取部门树

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/v1/crm/deptTree` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<List<TreeSelect>>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| deptId | Long | 否 | 部门ID（可选） |
| deptName | String | 否 | 部门名称（可选） |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `List<TreeSelect>`。

#### 响应字段说明（TreeSelect）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | Long | 节点ID |
| label | String | 节点名称 |
| children | Array<TreeSelect> | 子节点列表 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": [
    {
      "id": 100,
      "label": "总部",
      "children": []
    }
  ]
}
```

### 1.6 获取用户列表

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/v1/crm/userList` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<PageInfo<SysUser>>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| deptId | Long | 否 | 部门ID |
| pageNo | Integer | 否 | 页码 |
| pageSize | Integer | 否 | 每页条数 |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `PageInfo<SysUser>`。

#### 响应字段说明（SysUser 常用字段）

| 字段名 | 类型 | 说明 |
|---|---|---|
| userId | Long | 用户ID |
| userName | String | 登录名 |
| nickName | String | 昵称 |
| deptId | Long | 部门ID |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "list": [
      {
        "userId": 1,
        "userName": "admin",
        "nickName": "管理员",
        "deptId": 100
      }
    ],
    "total": 1,
    "pageNum": 1,
    "pageSize": 10
  }
}
```

### 1.7 获取企业下所有店铺列表（用于全企业诊断时聚合画像，无分页）

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiStore/list` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<PageInfo<Map<String,Object>>>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| storeId | String | 否 | 店铺ID |
| startDate | String | 否 | 开始日期 |
| endDate | String | 否 | 结束日期 |
| pageNo | Integer | 否 | 页码 |
| pageSize | Integer | 否 | 每页条数 |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `PageInfo<Map<String,Object>>`。

#### 响应字段说明（动态字段）

| 字段名 | 类型 | 说明 |
|---|---|---|
| storeId | String | 店铺ID |
| storeName | String | 店铺名称 |
| employeeCount | Integer | 员工数量 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "list": [
      {
        "storeId": "1",
        "storeName": "测试店铺",
        "employeeCount": 36
      }
    ],
    "total": 1,
    "pageNum": 1,
    "pageSize": 10
  }
}
```

### 1.8 获取店铺基础信息

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiStore/detail` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<Map<String,Object>>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| storeId | Long | 是 | 店铺ID |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `Map<String,Object>`。

#### 响应字段说明（动态字段）

| 字段名 | 类型 | 说明 |
|---|---|---|
| storeId | String | 店铺ID |
| storeName | String | 店铺名称 |
| employeeCount | Integer | 员工数量 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "storeId": "1",
    "storeName": "测试店铺",
    "employeeCount": 36
  }
}
```

### 1.9 获取行业分类详情

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiStore/industry` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<Map<String,Object>>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| storeId | Long | 是 | 店铺ID |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `Map<String,Object>`。

#### 响应字段说明

| 字段名 | 类型 | 说明 |
|---|---|---|
| classCode | String | 行业编码 |
| className | String | 行业名称 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "classCode": "",
    "className": ""
  }
}
```

---

## 二、运营指标采集

### 2.1 营销维度（优惠券核销率）

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/couponStatistics` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<CouponStatisticsVo>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| startDate | String | 否 | 开始日期 |
| endDate | String | 否 | 结束日期 |
| storeId | String | 否 | 店铺ID |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `CouponStatisticsVo`。

#### 响应字段说明（CouponStatisticsVo）

| 字段名 | 类型 | 说明 |
|---|---|---|
| issuedCount | Integer | 优惠券发放总数 |
| totalUsed | Integer | 已使用数 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "issuedCount": 200,
    "totalUsed": 75
  }
}
```

### 2.2 营销维度（浏览转化率，订单转化率） 下单用户数、订单总数、完成订单数、新客户数

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/orderStatistics` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<OrderStatisticsVo>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| startDate | String | 否 | 开始日期 |
| endDate | String | 否 | 结束日期 |
| storeId | String | 否 | 店铺ID |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `OrderStatisticsVo`。

#### 响应字段说明（OrderStatisticsVo）

| 字段名 | 类型 | 说明 |
|---|---|---|
| orderUsers | Integer | 下单用户数 |
| totalOrders | Integer | 订单总数 |
| completedOrders | Integer | 完成订单数 |
| newCustomers | Integer | 新客户数 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "orderUsers": 35,
    "totalOrders": 120,
    "completedOrders": 98,
    "newCustomers": 12
  }
}
```

### 2.3 营销维度（秒杀转化率) 秒杀统计 进针对商城

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/seckillStatistics` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<SeckillOrderVo>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| startDate | String | 否 | 最小时间（开始） |
| endDate | String | 否 | 最大时间（结束） |
| storeId | String | 否 | 店铺ID |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `SeckillOrderVo`。

#### 响应字段说明（SeckillOrderVo）

| 字段名 | 类型 | 说明 |
|---|---|---|
| totalSeckillGoods | Integer | 参与秒杀总数 |
| soldGoods | Integer | 已售商品数 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "totalSeckillGoods": 1000,
    "soldGoods": 760
  }
}
```

### 2.4 营销维度（浏览转化率） 数据是假的，拿不到

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/browseUsers` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<Map<String,Integer>>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| startDate | String | 否 | 开始日期 |
| endDate | String | 否 | 结束日期 |
| storeId | String | 否 | 店铺ID |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为对象，当前固定 `browseUsers=0`。

#### 响应字段说明

| 字段名 | 类型 | 说明 |
|---|---|---|
| browseUsers | Integer | 浏览用户数（占位值） |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "browseUsers": 0
  }
}
```

### 2.5 留存维度（复购率，流失率，平均客户生命周期价值） 购买总人数、复购人数、活跃客户数、流失客户数、平均客户生命周期价值

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/userStatus` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<AccountTypeResultVo>` |
| 鉴权 | `web:aiStore:query` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| startDate | String | 否 | 开始日期 |
| endDate | String | 否 | 结束日期 |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `AccountTypeResultVo`。

#### 响应字段说明（AccountTypeResultVo）

| 字段名 | 类型 | 说明 |
|---|---|---|
| totalBuyers | Integer | 购买总人数 |
| repeatBuyers | Integer | 复购人数 |
| activeCustomers | Integer | 活跃客户数 |
| churnedCustomers | Integer | 流失客户数 |
| avgLifetimeValue | float | 平均客户生命周期价值 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "totalBuyers": 180,
    "repeatBuyers": 72,
    "activeCustomers": 96,
    "churnedCustomers": 24,
    "avgLifetimeValue": 326.85
  }
}
```

### 2.6 留存维度（退款率）

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/orderRefundRate` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<OrderRefundRateVo>` |
| 鉴权 | `web:aiStore:query` |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `OrderRefundRateVo`。

| 字段名 | 类型 | 说明 |
|---|---|---|
| totalCompletedOrders | Integer | 已完成订单数 |
| refundOrders | Integer | 退款订单数 |
| refundRate | BigDecimal | 退款率 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "totalCompletedOrders": 98,
    "refundOrders": 6,
    "refundRate": 0.0612
  }
}
```

### 2.7 留存维度（好评率）

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/orderPositiveRate` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<OrderPositiveRateVo>` |
| 鉴权 | `web:aiStore:query` |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `OrderPositiveRateVo`。

| 字段名 | 类型 | 说明 |
|---|---|---|
| totalReviews | Integer | 评价总数 |
| positiveReviews | Integer | 好评数 |
| positiveRate | BigDecimal | 好评率 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "totalReviews": 150,
    "positiveReviews": 132,
    "positiveRate": 0.88
  }
}
```

### 2.8 效率维度（订单完成率）

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/orderCompletionRate` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<OrderCompletionRateVo>` |
| 鉴权 | `web:aiStore:query` |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `OrderCompletionRateVo`。

| 字段名 | 类型 | 说明 |
|---|---|---|
| totalOrders | Integer | 订单总数 |
| completedOrders | Integer | 完成订单数 |
| completionRate | BigDecimal | 完成率 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "totalOrders": 120,
    "completedOrders": 98,
    "completionRate": 0.8167
  }
}
```

### 2.9 效率维度（平均发货时效）

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiClientRecord/orderShippingAging` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<OrderShippingAgingVo>` |
| 鉴权 | `web:aiStore:query` |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `OrderShippingAgingVo`。

| 字段名 | 类型 | 说明 |
|---|---|---|
| avgShippingHours | BigDecimal | 平均发货时长（小时） |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "avgShippingHours": 5.25
  }
}
```

### 2.10 CRM 维度（线索转化率）客户数和新增客户数

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/v1/crm/getCustomerCount` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<ClientStatisticsVo>` |
| 鉴权 | `web:aiStore:query` |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `ClientStatisticsVo`。

| 字段名 | 类型 | 说明 |
|---|---|---|
| total | Integer | 客户总数 |
| newClients | Integer | 新增客户数 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "total": 520,
    "newClients": 36
  }
}
```

### 2.11 CRM 维度（线索转化率） 获取签约数和签约金额

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/v1/crm/getSalesContract` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<SalesContractStatisticsVo>` |
| 鉴权 | `web:aiStore:query` |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为 `SalesContractStatisticsVo`。

| 字段名 | 类型 | 说明 |
|---|---|---|
| signedCount | Integer | 签订合同数量 |
| totalAmount | float | 合同金额 |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "signedCount": 18,
    "totalAmount": 368000.0
  }
}
```

### 2.12 CRM 维度（平均响应时间，跟进次数） 跟进总次数和平均响应时间（小时）

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/v1/crm/followUp` |
| 请求方式 | GET |
| 返回类型 | `AjaxResult<Map<String,Object>>` |
| 鉴权 | `web:aiStore:query` |

#### 响应结构

返回 `AjaxResult`，其中 `data` 为对象（当前固定 `followTotal=0`、`avgResponseHours=0`）。

#### 响应字段说明

| 字段名 | 类型 | 说明 |
|---|---|---|
| followTotal | Integer | 跟进总次数 |
| avgResponseHours | Integer | 平均响应时间（小时） |

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "followTotal": 0,
    "avgResponseHours": 0
  }
}
```

---

## 三、消息通知推送

### 3.1 批量创建消息提醒

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiMessage/createMessage` |
| 请求方式 | POST |
| 返回类型 | `AjaxResult<String>` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| message | Array | 是 | 消息列表 |
| message[].accountId | String | 是 | 用户ID |
| message[].title | String | 是 | 消息标题 |
| message[].content | String | 是 | 消息内容 |
| message[].jumpUrl | String | 否 | 跳转地址 |
| message[].type | String | 否 | 消息类型 |

#### 响应结构

返回 `AjaxResult`，`data` 为提示文本（成功：`消息创建成功`）。

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": "消息创建成功"
}
```

### 3.2 按人群定向推送消息

#### 接口信息

| 项目 | 说明 |
|---|---|
| 接口路径 | `/web/aiMessage/targeted` |
| 请求方式 | POST |
| 返回类型 | `AjaxResult<String>` |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | String | 是 | 消息类型 |
| title | String | 是 | 消息标题 |
| content | String | 否 | 消息内容 |
| jumpUrl | String | 否 | 跳转地址 |
| targetSegment | String | 是 | 人群标签 |

#### 响应结构

返回 `AjaxResult`，`data` 为提示文本（成功：`消息创建成功`）。

#### 示例响应

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": "消息创建成功"
}
```

---

## 相关代码

- `wlwq-admin/src/main/java/com/wlwq/web/controller/enterprise/CDPAiController.java`
- `wlwq-admin/src/main/java/com/wlwq/web/controller/enterprise/StoreAiController.java`
- `wlwq-admin/src/main/java/com/wlwq/web/controller/enterprise/CrmAiController.java`
- `wlwq-admin/src/main/java/com/wlwq/web/controller/enterprise/MessagesAiController.java`
