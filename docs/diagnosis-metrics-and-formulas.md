# 诊断：维度、指标、公式

## 维度与默认权重

| 维度 | 权重 |
|------|------|
| `crm` | 0.25 |
| `marketing` | 0.30 |
| `retention` | 0.30 |
| `efficiency` | 0.15 |

仅部分维度参与诊断时，上表权重在**参与维度**上按比例归一使 \(\sum w_d = 1\)。无数据的维度得分 **60**，仍乘其 \(w_d\)。

## 指标

方向：`h` 越高越好，`l` 越低越好。

### `crm`

| 代码 | 名称 | 向 | 单位 |
|------|------|-----|------|
| `lead_conversion_rate` | 线索转化率 | h | % |
| `response_time_avg` | 平均响应时间 | l | 小时 |
| `follow_up_count` | 跟进次数 | h | 次 |

### `marketing`

| 代码 | 名称 | 向 | 单位 |
|------|------|-----|------|
| `coupon_redemption_rate` | 优惠券核销率 | h | % |
| `browse_to_order_rate` | 浏览转化率 | h | % |
| `order_conversion_rate` | 订单转化率 | h | % |
| `seckill_conversion_rate` | 秒杀转化率 | h | % |

### `retention`

| 代码 | 名称 | 向 | 单位 |
|------|------|-----|------|
| `repurchase_rate` | 复购率 | h | % |
| `refund_rate` | 退款率 | l | % |
| `churn_rate` | 流失率 | l | % |
| `positive_review_rate` | 好评率 | h | % |
| `avg_customer_lifetime_value` | 平均客户生命周期价值 | h | 元 |

### `efficiency`

| 代码 | 名称 | 向 | 单位 |
|------|------|-----|------|
| `service_completion_rate` | 服务订单完成率 | h | % |
| `avg_shipping_hours` | 平均发货时效 | l | 小时 |

## 符号

| 符号 | 含义 |
|------|------|
| \(v\) | 企业该指标当前值 |
| \(\mu\) | 行业基准均值 `avg_value`（缺失/为 0 时用内置缺省；仍无则该指标得分 60、无 `deviation_pct`、不进异常） |
| \(e\) | 行业优秀值 `excellent_value`（缺省为 \(1.3\mu\)，仅用于异常描述展示） |
| \(n\) | 该维度内实际参与打分的指标个数 |
| \(w_d\) | 维度 \(d\) 的权重（见上） |
| \(\mathrm{clip}(x,a,b)\) | \(\min(\max(x,a),b)\) |

## 偏离与得分

**偏离**（\(\mu \neq 0\)）：

- `higher_is_better`：\(\mathrm{deviation\_pct} = \dfrac{v - \mu}{\mu} \times 100\)
- `lower_is_better`：\(\mathrm{deviation\_pct} = \dfrac{\mu - v}{\mu} \times 100\)

**单指标得分**（0～100）：\(\mathrm{indicator\_score} = \mathrm{clip}(60 + 0.4 \times \mathrm{deviation\_pct},\,0,\,100)\)（四舍五入后截断）

**维度得分**：\(\mathrm{dimension\_score} = \dfrac{1}{n}\sum \mathrm{indicator\_score}\)；无可用指标时取 60

**综合健康度**：\(\mathrm{health\_score} = \sum_d w_d \cdot \mathrm{dimension\_score}_d\)

## 异常与严重度

记阈值 \(T = 15\)（`ANOMALY_THRESHOLD_PCT`）。**异常**：\(\mathrm{deviation\_pct} < -T\)。

| 条件 | `severity` |
|------|------------|
| \(\mathrm{deviation\_pct} < -30\) | `high` |
| \(-30 \le \mathrm{deviation\_pct} < -20\) | `medium` |
| \(-20 \le \mathrm{deviation\_pct} < -15\) | `low` |

## 行业基准维度参考分（报告内 `dimension_benchmarks_scores`）

对某维度下每条基准（\(\mu,e\) 均有效且 \(>0\)）：

- `higher_is_better`：\(\mathrm{score}_i = \mathrm{clip}(\dfrac{\mu}{e}\times 100,\,0,\,100)\)
- `lower_is_better`：\(\mathrm{score}_i = \mathrm{clip}(\dfrac{e}{\mu}\times 100,\,0,\,100)\)

该维度分 \(=\) 各条 \(\mathrm{score}_i\) 的算术平均；无有效条时 60。

## 效果对比（跟踪）

| 符号 | 含义 |
|------|------|
| \(v_b, v_a\) | 同一指标执行前、后值 |

\[
\mathrm{change\_pct} =
\begin{cases}
100 & v_b=0,\ v_a>0 \\
0 & v_b=0,\ v_a\le 0 \\
\dfrac{v_a - v_b}{|v_b|}\times 100 & \text{其余}
\end{cases}
\]

**是否改善**：越高越好则 \(\mathrm{change\_pct}>0\) 为改善；越低越好则 \(\mathrm{change\_pct}<0\) 为改善。

**整体达成率**：\(\dfrac{\text{改善指标条数}}{\text{有前后值的指标条数}}\times 100\)（分母为 0 时为 0）。
