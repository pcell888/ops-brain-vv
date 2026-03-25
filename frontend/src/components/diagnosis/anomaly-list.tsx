

import { Button, Tag, Empty } from 'antd';
import { RightOutlined } from '@ant-design/icons';
import clsx from 'clsx';
import { useNavigate } from 'react-router-dom';

export interface AnomalyItem {
  id: string;
  name: string;
  desc: string;
  currentValue: string;
  benchmark: string;
  gap: number;
  severity: 'severe' | 'moderate';
  metricName?: string;
  dimension?: string;
}

interface AnomalyListProps {
  anomalies?: AnomalyItem[];
  diagnosisId?: string | null;
  /** 是否已有方案（兼容旧逻辑） */
  hasSolutions?: boolean;
  /** 已有方案的异常 ID 集合（用于单独判断每个异常是否有方案） */
  anomalyIdsWithSolutions?: Set<string>;
  /** 正在生成方案的异常 ID（null 表示没有正在生成） */
  generatingAnomalyId?: string | null;
  onViewSolution?: (anomalyId: string) => void;
  onViewDetail?: (anomalyId: string) => void;
  onDrillDown?: (metricName: string, dimension: string) => void;
  /** 生成方案回调 */
  onGenerateSolution?: (anomalyId: string) => void;
}

// 默认的静态数据（用于开发时展示）
const defaultAnomalies: AnomalyItem[] = [
  {
    id: '1',
    name: '线索转化率严重低于行业水平',
    desc: '根因：跟进记录同步延迟 → 销售响应不及时 → 客户流失',
    currentValue: '12.3%',
    benchmark: '18.1%',
    gap: 32,
    severity: 'severe',
  },
  {
    id: '2',
    name: '营销触达ROI低于预期',
    desc: '根因：受众定向不精准 → 触达成本高 → 转化率低',
    currentValue: '2.1x',
    benchmark: '2.5x',
    gap: 18,
    severity: 'moderate',
  },
  {
    id: '3',
    name: '任务完成率偏低',
    desc: '根因：任务分配不均衡 → 部分员工超负荷 → 延期增加',
    currentValue: '67.2%',
    benchmark: '79.0%',
    gap: 15,
    severity: 'moderate',
  },
];

export function AnomalyList({
  anomalies,
  diagnosisId,
  hasSolutions = false,
  anomalyIdsWithSolutions,
  generatingAnomalyId = null,
  onViewSolution,
  onViewDetail,
  onDrillDown,
  onGenerateSolution,
}: AnomalyListProps) {
  const navigate = useNavigate();

  // 有 diagnosisId 时只用真实数据，避免用占位 id(1/2/3) 请求详情导致 404；无 diagnosisId 时可用默认数据展示
  const displayAnomalies =
    diagnosisId && (!anomalies || anomalies.length === 0)
      ? []
      : (anomalies && anomalies.length > 0 ? anomalies : defaultAnomalies);

  // 判断某个异常是否已有方案
  const hasAnomalySolution = (anomalyId: string) => {
    // 优先使用精确的异常 ID 判断
    if (anomalyIdsWithSolutions) {
      return anomalyIdsWithSolutions.has(anomalyId);
    }
    // 兼容旧逻辑：使用全局的 hasSolutions
    return hasSolutions;
  };

  // 处理查看/生成方案
  const handleSolutionAction = (anomaly: AnomalyItem) => {
    if (hasAnomalySolution(anomaly.id)) {
      // 方案已存在，跳转到详情页
      if (onViewSolution) {
        onViewSolution(anomaly.id);
      } else if (diagnosisId) {
        // 跳转到方案详情页，带上 anomaly_id 参数以便自动选择匹配的方案
        navigate(`/solutions/${diagnosisId}?anomaly_id=${anomaly.id}`);
      }
    } else {
      // 方案不存在，触发生成
      if (onGenerateSolution) {
        onGenerateSolution(anomaly.id);
      } else if (diagnosisId) {
        // 跳转到方案页面，带上参数提示需要生成
        navigate(`/solutions?diagnosis_id=${diagnosisId}&anomaly_id=${anomaly.id}&action=generate`);
      }
    }
  };

  // 处理查看方案（兼容旧逻辑）
  const handleViewSolution = (anomalyId: string) => {
    if (onViewSolution) {
      onViewSolution(anomalyId);
    } else if (diagnosisId) {
      // 跳转到方案详情页，带上 anomaly_id 参数以便自动选择匹配的方案
      navigate(`/solutions/${diagnosisId}?anomaly_id=${anomalyId}`);
    }
  };

  // 处理查看明细
  const handleViewDetail = (anomalyId: string) => {
    if (onViewDetail) {
      onViewDetail(anomalyId);
    } else if (diagnosisId) {
      // 默认跳转到详情页面
      navigate(`/diagnosis/${diagnosisId}/anomaly/${anomalyId}`);
    }
  };

  // 处理钻取
  const handleDrillDown = (anomaly: AnomalyItem) => {
    if (onDrillDown && anomaly.metricName && anomaly.dimension) {
      onDrillDown(anomaly.metricName, anomaly.dimension);
    } else if (diagnosisId && anomaly.metricName && anomaly.dimension) {
      navigate(`/diagnosis/${diagnosisId}/drill-down/${encodeURIComponent(anomaly.metricName)}?dimension=${anomaly.dimension}`);
    }
  };

  if (displayAnomalies.length === 0) {
    return (
      <Empty
        description="暂无异常指标，运营状况良好！"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <div className="space-y-3">
      {displayAnomalies.map((anomaly, index) => (
        <div
          key={anomaly.id}
          className={clsx(
            'group relative flex items-center gap-5 p-5 rounded-xl border cursor-pointer transition-all duration-300',
            'hover:scale-[1.01]',
            anomaly.severity === 'severe'
              ? 'border-rose-500/20 hover:border-rose-500/40 hover:bg-rose-500/5'
              : 'border-amber-500/20 hover:border-amber-500/40 hover:bg-amber-500/5'
          )}
          style={{ animationDelay: `${index * 100}ms` }}
        >
          {/* 背景渐变 */}
          <div className={clsx(
            'absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300',
            anomaly.severity === 'severe'
              ? 'bg-gradient-to-r from-rose-500/5 to-transparent'
              : 'bg-gradient-to-r from-amber-500/5 to-transparent'
          )} />

          {/* 严重程度指示条 */}
          <div
            className={clsx(
              'relative w-1.5 h-14 rounded-full',
              anomaly.severity === 'severe'
                ? 'bg-gradient-to-b from-rose-400 to-rose-600'
                : 'bg-gradient-to-b from-amber-400 to-amber-600'
            )}
          />

          {/* 信息 */}
          <div className="relative flex-1 min-w-0">
            <div className="font-semibold text-gray-500 text-base mb-1.5 truncate">
              {anomaly.name}
            </div>
            <div className="text-sm text-gray-500 leading-relaxed mb-2">
              {anomaly.desc}
            </div>
          </div>

          {/* 数据 */}
          <div className="relative text-right min-w-[100px]">
            <div
              className={clsx(
                'text-2xl font-bold tracking-tight',
                anomaly.severity === 'severe' ? 'text-rose-400' : 'text-amber-400'
              )}
            >
              {anomaly.currentValue}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              行业均值 {anomaly.benchmark}
            </div>
          </div>

          {/* 差距 */}
          <Tag
            style={{
              backgroundColor: anomaly.severity === 'severe' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: anomaly.severity === 'severe' ? '#ef4444' : '#f59e0b',
              border: 'none'
            }}
            className="relative !m-0 !px-3 !py-1 !text-xs !font-semibold !flex !items-center !gap-1"
          >
            ↓ 差距 {anomaly.gap}%
          </Tag>

          {/* 操作 */}
          <div className="relative flex gap-2">
            <Button
              size="small"
              style={{ color: 'rgba(10, 67, 255, 1)', backgroundColor: 'rgba(10, 67, 255, 0.08)', border: 'none' }}
              onClick={(e) => {
                e.stopPropagation();
                handleViewDetail(anomaly.id);
              }}
            >
              诊断明细
            </Button>
          </div>

          {/* 悬浮箭头指示 */}
          <RightOutlined className="relative text-gray-600 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all duration-300" />
        </div>
      ))}
    </div>
  );
}
