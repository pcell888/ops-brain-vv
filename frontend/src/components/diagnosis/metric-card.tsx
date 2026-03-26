

import { Card, Tag, Tooltip, Progress } from 'antd';
import { InfoCircleOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';
import clsx from 'clsx';
import { useState } from 'react';
import icon1 from '../../assets/icon/icon-1.png';
import icon2 from '../../assets/icon/icon-2.png';
import icon3 from '../../assets/icon/icon-3.png';
import icon4 from '../../assets/icon/icon-4.png';

// 指标明细类型
export interface MetricDetail {
  name: string;
  display_name: string;
  value: number;
  unit: string;
  score: number;
  benchmark_avg: number;
  benchmark_excellent: number;
}

interface MetricCardProps {
  title: string;
  value: string;
  status: 'excellent' | 'good' | 'warning' | 'danger';
  dimension: string;
  anomalyCount?: number;
  hasSevereAnomaly?: boolean;
  metricsDetail?: MetricDetail[];
  onDetailClick?: () => void;
  onMetricClick?: (metricName: string) => void;
}

const statusConfig = {
  excellent: {
    label: '表现优秀',
    color: 'green',
    bgColor: 'rgba(0,199,119,1)',
    bgGlow: 'hover:shadow-[0_0_30px_rgba(0,199,119,0.15)]',
  },
  good: {
    label: '表现良好',
    color: 'green',
    bgColor: 'rgba(0,199,119,1)',
    bgGlow: 'hover:shadow-[0_0_30px_rgba(0,199,119,0.15)]',
  },
  warning: {
    label: '需要关注',
    color: 'orange',
    bgColor: 'rgba(255,141,40,1)',
    bgGlow: 'hover:shadow-[0_0_30px_rgba(255,141,40,0.15)]',
  },
  danger: {
    label: '亟需改善',
    color: 'red',
    bgColor: 'rgba(255,56,60,1)',
    bgGlow: 'shadow-[0_0_20px_rgba(255,56,60,0.1)]',
  },
};

const dimensionConfig: Record<string, { icon: any; bg: string; text: string; gradient: string }> = {
  crm: {
    icon: icon1,
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    gradient: 'from-blue-500/20 to-blue-600/5',
  },
  marketing: {
    icon: icon2,
    bg: 'bg-purple-500/10',
    text: 'text-purple-400',
    gradient: 'from-purple-500/20 to-purple-600/5',
  },
  retention: {
    icon: icon3,
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    gradient: 'from-emerald-500/20 to-emerald-600/5',
  },
  efficiency: {
    icon: icon4,
    bg: 'bg-cyan-500/10',
    text: 'text-cyan-400',
    gradient: 'from-cyan-500/20 to-cyan-600/5',
  },
};

// 获取指标显示名称（使用后端返回的 display_name，无需前端硬编码）
function getMetricDisplayName(metric: MetricDetail): string {
  return metric.display_name || metric.name;
}

// 与 calculator INDICATOR_META.direction 一致，用于「相对均值好坏」着色
const METRIC_DIRECTION: Record<string, 'higher_is_better' | 'lower_is_better'> = {
  lead_conversion_rate: 'higher_is_better',
  response_time_avg: 'lower_is_better',
  follow_up_count: 'higher_is_better',
  coupon_redemption_rate: 'higher_is_better',
  browse_to_order_rate: 'higher_is_better',
  order_conversion_rate: 'higher_is_better',
  seckill_conversion_rate: 'higher_is_better',
  repurchase_rate: 'higher_is_better',
  refund_rate: 'lower_is_better',
  churn_rate: 'lower_is_better',
  positive_review_rate: 'higher_is_better',
  avg_customer_lifetime_value: 'higher_is_better',
  service_completion_rate: 'higher_is_better',
  avg_shipping_hours: 'lower_is_better',
};

/** 当前值相对行业均值是否处于「不利」一侧（低于均值且越高越好，或高于均值且越低越好） */
function isWorseThanBenchmark(metric: MetricDetail): boolean {
  const dir = METRIC_DIRECTION[metric.name];
  if (!dir) return false;
  const avg = Number(metric.benchmark_avg);
  const v = Number(metric.value);
  if (Number.isNaN(avg) || Number.isNaN(v)) return false;
  if (dir === 'higher_is_better') return v < avg;
  return v > avg;
}

// 根据得分获取颜色（纯分数档）
function getScoreColor(score: number): string {
  if (score >= 80) return 'text-[rgba(0,199,119,1)]';
  if (score >= 60) return 'text-[rgba(10,67,255,1)]';
  if (score >= 40) return 'text-[rgba(255,141,40,1)]';
  return 'text-[rgba(255,56,60,1)]';
}

function getProgressColor(score: number): string {
  if (score >= 80) return 'rgba(0,199,119,1)';
  if (score >= 60) return 'rgba(10,67,255,1)';
  if (score >= 40) return 'rgba(255,141,40,1)';
  return 'rgba(255,56,60,1)';
}

/** 数值与进度条颜色：差于行业均值时避免 40–60 分仍显「中性黄」，与业务含义一致 */
function getMetricValueColor(metric: MetricDetail): string {
  const score = metric.score;
  const worse = isWorseThanBenchmark(metric);
  if (worse) {
    if (score >= 80) return 'text-[rgba(0,199,119,1)]';
    if (score >= 60) return 'text-[rgba(255,141,40,1)]';
    if (score >= 40) return 'text-[rgba(255,141,40,1)]';
    return 'text-[rgba(255,56,60,1)]';
  }
  return getScoreColor(score);
}

function getMetricProgressColor(metric: MetricDetail): string {
  const score = metric.score;
  const worse = isWorseThanBenchmark(metric);
  if (worse) {
    if (score >= 80) return 'rgba(0,199,119,1)';
    if (score >= 60) return 'rgba(255,141,40,1)';
    if (score >= 40) return 'rgba(255,141,40,1)';
    return 'rgba(255,56,60,1)';
  }
  return getProgressColor(score);
}

export function MetricCard({
  title,
  value,
  status,
  dimension,
  anomalyCount = 0,
  hasSevereAnomaly = false,
  metricsDetail,
  onDetailClick,
  onMetricClick,
}: MetricCardProps) {
  const config = statusConfig[status] || statusConfig.good;
  const dimConfig = dimensionConfig[dimension] || dimensionConfig.crm;
  const [showDetail, setShowDetail] = useState(false);

  return (
    <Card
      className={clsx(
        'hover:translate-y-[-4px] transition-all duration-300 cursor-pointer overflow-hidden',
        'border-0',          // 全边框清除
        'bg-white !important',
        config.bgGlow
      )}
      style={{
        backgroundColor: '#fff !important',
        borderLeft: `4px solid ${config.bgColor}`,
      }}
      styles={{
        body: {
          padding: '20px',
          backgroundColor: '#ffffff !important'
        },
      }}
    >

      <div className="relative">
        <div className="flex justify-between items-start mb-4">
          <img width="32px" src={dimConfig.icon} alt="icon" />
          <div className="flex items-center gap-2">
            {/* 指标详情按钮 */}
            {metricsDetail && metricsDetail.length > 0 && (
              <Tooltip title={showDetail ? '收起指标详情' : '查看指标详情'}>
                <div
                  className={clsx(
                    'w-6 h-6 rounded-md flex items-center justify-center cursor-pointer transition-all',
                    showDetail
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-gray-500/10 text-gray-400 hover:bg-gray-500/20 hover:text-gray-300'
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowDetail(!showDetail);
                  }}
                >
                  <InfoCircleOutlined className="text-xs" />
                </div>
              </Tooltip>
            )}
            <Tag
              className="!m-0 !px-3 !py-0.5 !text-xs !font-medium"
              style={{
                backgroundColor: config.bgColor,
                color: 'white',
                borderColor: config.bgColor
              }}
            >
              {config.label}
            </Tag>
          </div>
        </div>

        <div className="text-gray-400 text-sm mb-1 font-medium">{title}</div>
        <div
          className={clsx(
            'text-4xl font-bold mb-3 tracking-tight',
            value.includes('分') && 'text-[#333]'
          )}
        >
          {value}
        </div>

        {/* 异常摘要（替代原来的行业均值对比） */}
        <div className="flex items-center gap-2 text-sm">
          {anomalyCount > 0 ? (
            <span className={clsx(
              'flex items-center gap-1.5 font-medium',
              hasSevereAnomaly ? 'text-rose-400' : 'text-amber-400'
            )}>
              <WarningOutlined />
              {anomalyCount}项异常需关注{hasSevereAnomaly ? '（含严重）' : ''}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 font-medium text-emerald-400">
              <CheckCircleOutlined />
              所有指标正常
            </span>
          )}
        </div>

        {/* 指标明细展开面板 */}
        {showDetail && metricsDetail && metricsDetail.length > 0 && (
          <div className="mt-4 pt-3 border-t border-white/10 space-y-3 animate-fadeIn">
            <div className="text-xs text-gray-500 font-medium mb-2">各项指标得分</div>
            {metricsDetail.map((metric, idx) => (
              <div
                key={idx}
                className={clsx(
                  "space-y-1 p-2 rounded-lg transition-all",
                  onMetricClick && "cursor-pointer hover:bg-white/5"
                )}
                onClick={(e) => {
                  e.stopPropagation();
                  onMetricClick?.(metric.name);
                }}
              >
                <div className="flex justify-between items-center text-xs">
                  <span className={clsx(
                    "text-gray-400",
                    onMetricClick && "hover:text-blue-400 transition-colors"
                  )}>
                    {getMetricDisplayName(metric)}
                    {onMetricClick && <span className="ml-1 text-gray-600">→</span>}
                  </span>
                  <span className={clsx('font-medium', getMetricValueColor(metric))}>
                    {metric.value}{metric.unit}
                    <span className="text-gray-500 ml-1">({Number.isInteger(metric.score) ? metric.score : metric.score.toFixed(1)}分)</span>
                  </span>
                </div>
                <Progress
                  percent={Math.min(100, metric.score)}
                  size="small"
                  showInfo={false}
                  strokeColor={getMetricProgressColor(metric)}
                  trailColor="rgba(255,255,255,0.05)"
                />
                <div className="flex justify-between text-[10px] text-gray-600">
                  <span>均值: {metric.benchmark_avg}{metric.unit}</span>
                  <span>优秀: {metric.benchmark_excellent}{metric.unit}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {(!metricsDetail || metricsDetail.length === 0) && onDetailClick && (
          <div
            className="mt-4 pt-3 border-t border-white/5 text-xs text-blue-400 flex items-center gap-1.5 cursor-pointer hover:text-blue-300 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              onDetailClick();
            }}
          >
            <span>📋</span>
            <span>查看明细数据</span>
          </div>
        )}
      </div>
    </Card>
  );
}
