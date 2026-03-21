# 指标异常判定与仪表盘指标颜色说明

本文汇总 **后端异常如何产生**、**兼容接口如何映射严重度**、**仪表盘维度卡片上「N 项异常 / 含严重」如何统计**，以及 **指标明细行数值与进度条颜色** 的规则。实现位置见各节引用。

---

## 一、异常判定（后端 `calculator.py`）

### 1.1 偏离百分比 `deviation_pct`

对每个指标，按 `INDICATOR_META` 中的 `direction` 计算相对行业均值 `avg_value` 的偏离（百分比）：

| 方向 | 公式 |
|------|------|
| `higher_is_better` | `(当前值 - 均值) / 均值 × 100` |
| `lower_is_better` | `(均值 - 当前值) / 均值 × 100` |

### 1.2 是否记为异常

- 常量：`ANOMALY_THRESHOLD_PCT = 15.0`
- **当 `deviation_pct < -15`** 时，该指标记入本维度的 **异常列表**（`anomalies`），即「相对均值不利」且偏离超过 15%。

### 1.3 后端严重度（`severity`）

在已满足异常条件的前提下，按 `deviation_pct` 再分档：

| 条件 | `severity` |
|------|------------|
| `deviation_pct < -30` | `high` |
| `-30 ≤ deviation_pct < -20` | `medium` |
| `-20 ≤ deviation_pct < -15` | `low` |

> 指标得分（0–100）与异常判定独立：得分由 `60 + deviation_pct × 0.4` 等规则计算，异常仅由 **是否 &lt; -15%** 决定。

---

## 二、严重度映射（`compat_diagnosis._map_severity`）

前端诊断报告接口将后端 `high / medium / low` 映射为：

| 后端 | 前端 `severity` |
|------|------------------|
| `high` | `critical` |
| `medium` | `high` |
| `low` | `medium` |

异常列表项中的 `metric_name` 对应指标代码（如 `repurchase_rate`），`dimension` 为逻辑维度（如 `retention`）。

---

## 三、仪表盘「N 项异常需关注（含严重）」

### 3.1 数据来源

- 使用接口返回的 **`report.anomalies`**。
- 维度卡片会先 **合并别名维度**（如 `crm` / `crm_sharing` 归一成一张卡），再按卡统计。

### 3.2 条数 `N`（`countAnomaliesForMetricCard`）

对**当前维度卡片**：

1. **维度**：异常项的 `dimension` 经 `dimensionMapping` 归一化后，须与卡片归一化维度一致。
2. **指标范围**：若该卡合并后的 `metrics_detail` **非空**，只统计 **`metric_name` 落在该列表内**的异常；若为空，则按该维度下全部异常计数。
3. **`N`** = 满足 1、2 的异常 **条数**（每条异常对应一个指标）。

### 3.3 「含严重」

在计入上述 `N` 条的异常中，若存在任一条 **`severity` 为 `critical` 或 `high`（前端字段）**，则展示「含严重」。

结合第二节映射可知：后端标为 **`high` 或 `medium`** 的异常，在前端会变成 `critical` 或 `high`，都会触发「含严重」；仅后端 **`low`**（映射为前端 `medium`）则不会单独靠严重度触发该文案（但若与更高等级混在同卡仍会显示「含严重」）。

---

## 四、指标明细颜色（`metric-card` 展开行）

适用于 **「各项指标得分」** 中每一行：数值颜色与进度条颜色，**不**改变括号内「xx分」的灰色样式。

### 4.1 指标方向

前端维护 `METRIC_DIRECTION`（与 `INDICATOR_META.direction` 一致），按 **`metric.name`**（指标代码）区分 `higher_is_better` / `lower_is_better`。

### 4.2 是否「差于行业均值」`isWorseThanBenchmark`

用当前 **`metric.value`** 与 **`metric.benchmark_avg`** 比较：

| 方向 | 判定为「不利」（用于着色） |
|------|---------------------------|
| `higher_is_better` | 当前值 **&lt;** 均值 |
| `lower_is_better` | 当前值 **&gt;** 均值 |

### 4.3 颜色规则（基于 `metric.score` 0–100）

**若「不利」**（`isWorseThanBenchmark === true`）：

| 分数区间 | 数值（Tailwind class） | 进度条（hex） |
|----------|------------------------|----------------|
| ≥ 80 | `text-emerald-400` | `#10b981` |
| 60–79 | `text-amber-400` | `#f59e0b` |
| 40–59 | `text-orange-400` | `#f97316` |
| &lt; 40 | `text-rose-400` | `#f43f5e` |

**若「不不利」**（优于或等于均值，或未知指标代码）：按 **纯分数档**：

| 分数区间 | 数值 | 进度条 |
|----------|------|--------|
| ≥ 80 | 绿 `emerald` | 绿 |
| 60–79 | 蓝 `blue` | 蓝 `#3b82f6` |
| 40–59 | 琥珀 `amber` | 琥珀 `#f59e0b` |
| &lt; 40 | 红 `rose` | 红 `#f43f5e` |

设计意图：在 **40–60 分** 且 **已低于/高于均值（不利方向）** 时，用 **橙色** 强调，避免与「中性」琥珀黄混淆。

### 4.4 与卡片无关

维度卡片 **主标题大分**、**左侧图标色** 仍由 `dimensionConfig`（crm / marketing / retention / efficiency）控制，与上述「各项指标得分」行规则**独立**。

---

## 五、代码索引

| 内容 | 位置 |
|------|------|
| 异常阈值、偏离、`severity`、得分公式 | `src/core/calculator.py`（`calculate_dimension_score`） |
| `severity` 映射 | `src/api/routes/compat_diagnosis.py`（`_map_severity`） |
| 卡片异常条数与「含严重」 | `frontend/src/pages/dashboard/index.tsx`（`countAnomaliesForMetricCard`） |
| 维度别名合并 | 同上（`mergeDimensionScores`、`dimensionMapping`） |
| 指标行颜色 | `frontend/src/components/diagnosis/metric-card.tsx`（`METRIC_DIRECTION`、`getMetricValueColor`、`getMetricProgressColor`） |
