

import { useParams, useNavigate } from 'react-router-dom';
import { Card, Tag, Spin, Empty, Button, Descriptions, Timeline, Tooltip } from 'antd';
import { 
  ArrowLeftOutlined, 
  LoadingOutlined,
  ExclamationCircleOutlined,
  BulbOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import clsx from 'clsx';
import { useAnomalyDetail, useDimensionConfig } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { getTagLabel } from '@/lib/tag-labels';

// 严重程度配置
const severityConfig: Record<string, { color: string; text: string; bgClass: string }> = {
  critical: { color: 'red', text: '严重', bgClass: 'from-rose-500/20 to-rose-600/10' },
  high: { color: 'orange', text: '高', bgClass: 'from-orange-500/20 to-orange-600/10' },
  medium: { color: 'gold', text: '中等', bgClass: 'from-amber-500/20 to-amber-600/10' },
  low: { color: 'blue', text: '低', bgClass: 'from-blue-500/20 to-blue-600/10' },
};

export default function AnomalyDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  
  const diagnosisId = params.diagnosisId as string;
  const anomalyId = params.anomalyId as string;
  
  const enterpriseId = currentEnterprise?.id || null;
  const { data: anomalyDetail, isLoading } = useAnomalyDetail(diagnosisId, anomalyId);
  const { getDimensionDisplayName, getMetricDisplayName } = useDimensionConfig(enterpriseId);
  
  const anomaly = anomalyDetail?.anomaly;
  const rootCauseAnalysis = anomalyDetail?.root_cause_analysis;

  const unit = anomaly?.unit || '%';
  
  const handleBack = () => {
    navigate(-1);
  };

  const handleViewSolutions = () => {
    navigate(`/solutions/${diagnosisId}`);
  };

  const handleDrillDown = () => {
    if (anomaly?.metric_name && anomaly?.dimension) {
      navigate(`/diagnosis/${diagnosisId}/drill-down/${encodeURIComponent(anomaly.metric_name)}?dimension=${anomaly.dimension}`);
    }
  };
  
  // 加载中
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }
  
  // 异常不存在
  if (!anomaly) {
    return (
      <div className="space-y-6">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={handleBack}
          className="!flex !items-center !gap-2"
        >
          返回
        </Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty description="异常指标不存在或已被删除" />
        </div>
      </div>
    );
  }
  
  const severity = severityConfig[anomaly.severity] || severityConfig.medium;
  const gapPercentage = anomaly.gap_percentage ? Math.abs(anomaly.gap_percentage) : 0;
  
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={handleBack}
            className="!flex !items-center"
          />
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className={clsx(
                'w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-lg',
                anomaly.severity === 'critical' || anomaly.severity === 'high'
                  ? 'bg-gradient-to-br from-rose-500 to-rose-600 shadow-rose-500/20'
                  : 'bg-gradient-to-br from-amber-500 to-amber-600 shadow-amber-500/20'
              )}>
                <ExclamationCircleOutlined />
              </span>
              异常指标明细
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              查看异常指标的详细信息和根因分析
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button 
            icon={<BulbOutlined />}
            onClick={handleViewSolutions}
          >
            查看方案
          </Button>
          {anomaly?.metric_name && anomaly?.dimension && (
            <Button 
              icon={<LineChartOutlined />}
              onClick={handleDrillDown}
            >
              数据钻取
            </Button>
          )}
        </div>
      </div>

      {/* 异常概览卡片 */}
      <Card className={clsx(
        'border-l-4',
        anomaly.severity === 'critical' || anomaly.severity === 'high'
          ? 'border-l-rose-500'
          : 'border-l-amber-500'
      )}>
        <div className={clsx(
          'absolute inset-0 bg-gradient-to-r opacity-30 pointer-events-none',
          severity.bgClass
        )} />
        
        <div className="relative flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-xl font-semibold text-white">
                {anomaly.rule_name}
              </h2>
              <Tag color={severity.color} className="!m-0">
                {severity.text}
              </Tag>
              <Tag color="default" className="!m-0">
                {getDimensionDisplayName(anomaly.dimension)}
              </Tag>
            </div>
            <p className="text-gray-400 text-sm mb-4">
              指标: {getMetricDisplayName(anomaly.metric_name)}
            </p>
            
            {/* 数值对比 */}
            <div className="flex items-center gap-8">
              <div>
                <div className="text-gray-500 text-xs mb-1">当前值</div>
                <div className={clsx(
                  'text-3xl font-bold',
                  anomaly.severity === 'critical' || anomaly.severity === 'high'
                    ? 'text-rose-400'
                    : 'text-amber-400'
                )}>
                  {anomaly.current_value.toFixed(1)}{unit}
                </div>
              </div>
              <div className="text-gray-600 text-2xl">→</div>
              <div>
                <div className="text-gray-500 text-xs mb-1">行业基准</div>
                <div className="text-3xl font-bold text-emerald-400">
                  {anomaly.benchmark_value?.toFixed(1) || '-'}{unit}
                </div>
              </div>
              <div className="ml-4 px-4 py-2 bg-gray-800/50 rounded-lg">
                <div className="text-gray-500 text-xs mb-1">差距</div>
                <div className={clsx(
                  'text-xl font-bold',
                  anomaly.severity === 'critical' || anomaly.severity === 'high'
                    ? 'text-rose-400'
                    : 'text-amber-400'
                )}>
                  ↓ {gapPercentage.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        {/* 根因分析 */}
        <Card 
          title={
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 text-sm">
                🔍
              </span>
              <span>根因分析链</span>
            </div>
          }
        >
          {anomaly.root_cause_chain && anomaly.root_cause_chain.length > 0 ? (
            <Timeline
              items={anomaly.root_cause_chain.map((cause: string, index: number) => ({
                color: index === anomaly.root_cause_chain.length - 1 ? 'red' : 'blue',
                children: (
                  <div className={clsx(
                    'p-3 rounded-lg',
                    index === anomaly.root_cause_chain.length - 1 
                      ? 'bg-rose-500/10 border border-rose-500/20' 
                      : 'bg-gray-800/50'
                  )}>
                    <span className={clsx(
                      'text-sm',
                      index === anomaly.root_cause_chain.length - 1 ? 'text-rose-300' : 'text-gray-300'
                    )}>
                      {cause}
                    </span>
                    {index === anomaly.root_cause_chain.length - 1 && (
                      <Tag color="red" className="!ml-2 !text-xs">根因</Tag>
                    )}
                  </div>
                ),
              }))}
            />
          ) : (
            <Empty description="暂无根因分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
          
          {/* 详细解释 */}
          {rootCauseAnalysis?.explanation && (
            <div className="mt-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
              <div className="text-gray-500 text-xs mb-2 flex items-center gap-1">
                <BulbOutlined /> AI 分析说明
              </div>
              <p className="text-gray-300 text-sm leading-relaxed">
                {rootCauseAnalysis.explanation}
              </p>
            </div>
          )}
        </Card>

        {/* 改进建议 */}
        <Card 
          title={
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 text-sm">
                💡
              </span>
              <span>改进建议</span>
            </div>
          }
        >
          {rootCauseAnalysis?.recommendations && rootCauseAnalysis.recommendations.length > 0 ? (
            <div className="space-y-3">
              {rootCauseAnalysis.recommendations.map((rec: string, index: number) => (
                <div 
                  key={index}
                  className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-800/70 transition-colors"
                >
                  <span className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-xs font-medium flex-shrink-0">
                    {index + 1}
                  </span>
                  <span className="text-gray-300 text-sm">{rec}</span>
                </div>
              ))}
            </div>
          ) : (
            <Empty description="暂无改进建议" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
          
          {/* 解决方案标签 */}
          {anomaly.solution_tags && anomaly.solution_tags.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-700/50">
              <div className="text-gray-500 text-xs mb-2">相关方案标签</div>
              <div className="flex flex-wrap gap-2">
                {anomaly.solution_tags.map((tag: string, index: number) => (
                  <Tag key={index} color="processing">
                    {getTagLabel(tag)}
                  </Tag>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* 详细信息 */}
      <Card 
        title={
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 text-sm">
              📋
            </span>
            <span>详细信息</span>
          </div>
        }
      >
        <Descriptions 
          column={3} 
          bordered 
          size="small"
          labelStyle={{ color: '#9ca3af', backgroundColor: 'transparent' }}
          contentStyle={{ color: '#fff', backgroundColor: 'transparent' }}
        >
          <Descriptions.Item label="异常ID">{anomaly.id}</Descriptions.Item>
          <Descriptions.Item label="规则ID">{anomaly.rule_id}</Descriptions.Item>
          <Descriptions.Item label="所属维度">
            {getDimensionDisplayName(anomaly.dimension)}
          </Descriptions.Item>
          <Descriptions.Item label="指标名称">{getMetricDisplayName(anomaly.metric_name)}</Descriptions.Item>
          <Descriptions.Item label="当前值">{anomaly.current_value.toFixed(2)}{unit}</Descriptions.Item>
          <Descriptions.Item label="基准值">
            {anomaly.benchmark_value?.toFixed(2) || '-'}{unit}
          </Descriptions.Item>
          <Descriptions.Item label="差距百分比">
            <span className={anomaly.gap_percentage && anomaly.gap_percentage < 0 ? 'text-rose-400' : 'text-emerald-400'}>
              {anomaly.gap_percentage?.toFixed(2) || '-'}%
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="严重程度">
            <Tag color={severity.color}>{severity.text}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="诊断ID">{diagnosisId}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}

