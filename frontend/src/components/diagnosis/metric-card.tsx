

import { Card, Tag, Tooltip, Progress } from 'antd';
import { InfoCircleOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';
import clsx from 'clsx';
import { useState } from 'react';

// 指标明细类型
interface MetricDetail {
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
    bgGlow: 'hover:shadow-[0_0_30px_rgba(16,185,129,0.15)]',
  },
  good: {
    label: '表现良好',
    color: 'green',
    bgGlow: 'hover:shadow-[0_0_30px_rgba(16,185,129,0.15)]',
  },
  warning: {
    label: '需要关注',
    color: 'orange',
    bgGlow: 'hover:shadow-[0_0_30px_rgba(245,158,11,0.15)]',
  },
  danger: {
    label: '亟需改善',
    color: 'red',
    bgGlow: 'shadow-[0_0_20px_rgba(244,63,94,0.1)]',
  },
};

const dimensionConfig: Record<string, { icon: string; bg: string; text: string; gradient: string }> = {
  crm: {
    icon: '📊',
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    gradient: 'from-blue-500/20 to-blue-600/5',
  },
  marketing: {
    icon: '📈',
    bg: 'bg-purple-500/10',
    text: 'text-purple-400',
    gradient: 'from-purple-500/20 to-purple-600/5',
  },
  retention: {
    icon: '👥',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    gradient: 'from-emerald-500/20 to-emerald-600/5',
  },
  efficiency: {
    icon: '⚙️',
    bg: 'bg-cyan-500/10',
    text: 'text-cyan-400',
    gradient: 'from-cyan-500/20 to-cyan-600/5',
  },
};

// 获取指标显示名称（使用后端返回的 display_name，无需前端硬编码）
function getMetricDisplayName(metric: MetricDetail): string {
  return metric.display_name || metric.name;
}

// 根据得分获取颜色
function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-400';
  if (score >= 60) return 'text-blue-400';
  if (score >= 40) return 'text-amber-400';
  return 'text-rose-400';
}

// 根据得分获取进度条颜色
function getProgressColor(score: number): string {
  if (score >= 80) return '#10b981';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#f59e0b';
  return '#f43f5e';
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
        'border-l-4 border-t-0 border-r-0 border-b-0',
        status === 'excellent' && 'border-l-emerald-500',
        status === 'good' && 'border-l-emerald-500',
        status === 'warning' && 'border-l-amber-500',
        status === 'danger' && 'border-l-rose-500 soft-pulse',
        config.bgGlow
      )}
      styles={{ body: { padding: '20px' } }}
    >
      {/* 背景渐变装饰 */}
      <div className={clsx(
        'absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-30 -translate-y-1/2 translate-x-1/2',
        `bg-gradient-to-br ${dimConfig.gradient}`
      )} />

      <div className="relative">
        <div className="flex justify-between items-start mb-4">
          <div
            className={clsx(
              'w-11 h-11 rounded-xl flex items-center justify-center text-xl',
              dimConfig.bg,
              'backdrop-blur-sm border border-white/5'
            )}
          >
            {dimConfig.icon}
          </div>
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
              color={config.color} 
              className="!m-0 !px-3 !py-0.5 !text-xs !font-medium"
            >
              {config.label}
            </Tag>
          </div>
        </div>

        <div className="text-gray-400 text-sm mb-1 font-medium">{title}</div>
        <div className={clsx(
          'text-4xl font-bold mb-3 tracking-tight',
          dimConfig.text
        )}>
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
            <div className="text-xs text-gray-500 font-medium mb-2">
              各项指标得分 
              <span className="text-gray-600 ml-1">(点击查看明细)</span>
            </div>
            {metricsDetail.map((metric, idx) => (
              <div 
                key={idx} 
                className={clsx(
                  "space-y-1 p-2 -mx-2 rounded-lg transition-all",
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
                  <span className={clsx('font-medium', getScoreColor(metric.score))}>
                    {metric.value}{metric.unit} 
                    <span className="text-gray-500 ml-1">({Number.isInteger(metric.score) ? metric.score : metric.score.toFixed(1)}分)</span>
                  </span>
                </div>
                <Progress 
                  percent={Math.min(100, metric.score)} 
                  size="small" 
                  showInfo={false}
                  strokeColor={getProgressColor(metric.score)}
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

        <div 
          className="mt-4 pt-3 border-t border-white/5 text-xs text-blue-400 flex items-center gap-1.5 cursor-pointer hover:text-blue-300 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onDetailClick?.();
          }}
        >
          <span>📋</span>
          <span>查看明细数据</span>
        </div>
      </div>
    </Card>
  );
}
