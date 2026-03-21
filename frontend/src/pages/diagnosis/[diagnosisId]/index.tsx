

import { Card, Row, Col, Tag, Spin, Empty, Progress, Descriptions, Collapse, Button } from 'antd';
import { 
  ArrowLeftOutlined,
  CheckCircleOutlined,
  RiseOutlined,
  FallOutlined,
  ThunderboltOutlined,
  FileSearchOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useDiagnosisReport, useDimensionConfig } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { DiagnosisReport, MetricDetail } from '@/lib/types';
import { AnomalyList } from '@/components/diagnosis/anomaly-list';
import { useMemo } from 'react';
import dayjs from 'dayjs';
import clsx from 'clsx';
// 维度图标/颜色 fallback（动态配置优先）
const dimensionIconFallback: Record<string, { icon: string; color: string }> = {
  crm: { icon: '📊', color: 'blue' },
  marketing: { icon: '📈', color: 'purple' },
  retention: { icon: '👥', color: 'green' },
  efficiency: { icon: '⚙️', color: 'cyan' },
};

// 获取分数颜色
function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-400';
  if (score >= 60) return 'text-blue-400';
  if (score >= 40) return 'text-amber-400';
  return 'text-rose-400';
}

// 获取进度条颜色
function getProgressColor(score: number): string {
  if (score >= 80) return '#10b981';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#f59e0b';
  return '#f43f5e';
}

export default function DiagnosisDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  const diagnosisId = params.diagnosisId as string;
  const { data, isLoading } = useDiagnosisReport(diagnosisId);
  const report = data as DiagnosisReport | undefined;

  /** 与仪表盘「异常指标预警」一致：映射为 AnomalyList 所需结构 */
  const anomalyListItems = useMemo(() => {
    if (!report) return [];
    const anomalies = report.anomalies || [];
    const rootCauseAnalyses = report.root_cause_analyses || [];
    const dimensionScores = report.health_score?.dimension_scores || [];
    return anomalies.map((a) => {
      let unit = a.unit;
      if (!unit) {
        const ds = dimensionScores.find((d) => d.dimension === a.dimension);
        const md = ds?.metrics_detail?.find((m: MetricDetail) => m.name === a.metric_name);
        unit = md?.unit || '%';
      }
      const matchingRca = rootCauseAnalyses.find((r) => r.metric_name === a.metric_name);
      let desc: string;
      if (a.root_cause_chain && a.root_cause_chain.length > 0) {
        desc = `根因：${a.root_cause_chain.join(' → ')}`;
      } else if (matchingRca?.explanation) {
        desc = `根因：${matchingRca.explanation}`;
      } else {
        desc = '根因：暂无详细分析';
      }
      return {
        id: a.id,
        name: a.rule_name,
        desc,
        currentValue: `${a.current_value.toFixed(1)}${unit}`,
        benchmark: a.benchmark_value != null ? `${a.benchmark_value.toFixed(1)}${unit}` : '-',
        gap: Math.abs(a.gap_percentage || 0),
        severity: (a.severity === 'critical' || a.severity === 'high' ? 'severe' : 'moderate') as
          | 'severe'
          | 'moderate',
        metricName: a.metric_name,
        dimension: a.dimension,
      };
    });
  }, [report]);

  // 使用动态维度配置（替代硬编码映射）
  const {
    getDimensionDisplayName,
    getMetricDisplayName: getDynMetricDisplayName,
  } = useDimensionConfig(currentEnterprise?.id ?? null);

  // 获取指标显示名称（优先后端 display_name → 动态配置 → 原始名称）
  function getMetricDisplayName(name: string, displayName?: string): string {
    return displayName || getDynMetricDisplayName(name) || name;
  }

  // 获取维度图标
  function getDimIcon(dimension: string): string {
    return dimensionIconFallback[dimension]?.icon || '📋';
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin size="large" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Empty description="诊断报告不存在" />
      </div>
    );
  }

  const totalScore = report.health_score?.total_score || 0;
  const dimensionScores = report.health_score?.dimension_scores || [];
  const anomalies = report.anomalies || [];
  const rootCauseAnalyses = report.root_cause_analyses || [];
  const trend = report.health_score?.trend;

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate(-1)}
          >
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg shadow-cyan-500/20">
                <FileSearchOutlined />
              </span>
              诊断报告详情
            </h1>
          </div>
        </div>
        <div className="text-right text-sm text-gray-500 hidden md:block">
          <div>诊断时间: {dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}</div>
        </div>
      </div>

      {/* 健康度概览卡片 */}
      <Row gutter={16}>
        <Col span={14}>
          <Card className="h-full relative overflow-hidden border-l-4 border-l-rose-500">
            <div className="flex items-center justify-between h-full">
              <div className="flex-1">
                <div className="text-gray-400 text-base mb-4">综合健康度</div>
                <div className="flex items-baseline gap-4">
                  <div className={clsx('text-7xl font-bold', getScoreColor(totalScore))}>
                    {totalScore.toFixed(0)}
                  </div>
                  <div className="text-2xl text-gray-500">分</div>
                  <Tag className="text-base px-3 py-1" color={totalScore >= 80 ? 'success' : totalScore >= 60 ? 'warning' : 'error'}>
                    {totalScore >= 80 ? '健康良好' : totalScore >= 60 ? '需要关注' : '亟需改善'}
                  </Tag>
                </div>
                <div className="mt-6 w-3/4">
                  <Progress 
                    percent={totalScore} 
                    showInfo={false}
                    strokeColor={getProgressColor(totalScore)}
                    trailColor="rgba(255,255,255,0.05)"
                    strokeWidth={12}
                  />
                </div>
              </div>
              
              {/* 仪表盘装饰背景 */}
              <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 pointer-events-none">
                <div className="w-full h-full bg-gradient-to-l from-white to-transparent" />
              </div>
            </div>
          </Card>
        </Col>
        <Col span={10}>
          <Card className="h-full">
            <div className="text-gray-400 text-sm mb-3">诊断概况</div>
            <Descriptions column={2} size="small" className="diagnosis-desc">
              <Descriptions.Item label="诊断维度">
                <span className="text-white text-lg">{dimensionScores.length}</span> <span className="text-gray-500">个</span>
              </Descriptions.Item>
              <Descriptions.Item label="检测指标">
                <span className="text-white text-lg">
                  {dimensionScores.reduce((sum, d) => sum + (d.metrics_detail?.length || 0), 0)}
                </span> <span className="text-gray-500">项</span>
              </Descriptions.Item>
              <Descriptions.Item label="异常指标">
                <Tag color={anomalies.length > 0 ? 'error' : 'success'}>
                  {anomalies.length} 项
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="根因分析">
                <span className="text-white">{rootCauseAnalyses.length} 条</span>
              </Descriptions.Item>
              {/* 趋势对比 */}
              <Descriptions.Item label="健康度趋势" span={2}>
                {trend?.change != null ? (
                  <span className={clsx(
                    'flex items-center gap-1 font-medium',
                    trend.direction === 'stable' ? 'text-gray-400' :
                    trend.direction === 'up' ? 'text-emerald-400' : 'text-rose-400'
                  )}>
                    {trend.direction === 'stable' ? (
                      '与上期持平'
                    ) : (
                      <>
                        {trend.direction === 'up' ? <RiseOutlined /> : <FallOutlined />}
                        较上期{trend.direction === 'up' ? '提升' : '下降'} {Math.abs(trend.change).toFixed(1)} 分
                      </>
                    )}
                  </span>
                ) : (
                  <span className="text-gray-500">暂无趋势数据</span>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* 维度评分详情 */}
      <Card 
        title={
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 text-sm">
              📊
            </span>
            <span>维度评分详情</span>
            <Tag color="blue">{dimensionScores.length}个维度</Tag>
          </div>
        }
      >
        <Collapse 
          ghost
          defaultActiveKey={[]}
          items={dimensionScores.map((dim) => {
            const icon = getDimIcon(dim.dimension);
            const dimName = getDimensionDisplayName(dim.dimension);
            return {
              key: dim.dimension,
              label: (
                <div className="flex items-center justify-between w-full pr-4">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{icon}</span>
                    <span className="font-medium text-white">{dimName}</span>
                    <Tag color={dim.status === 'excellent' ? 'success' : dim.status === 'good' ? 'processing' : dim.status === 'warning' ? 'warning' : 'error'}>
                      {dim.status === 'excellent' ? '优秀' : dim.status === 'good' ? '良好' : dim.status === 'warning' ? '需改善' : '亟需改善'}
                    </Tag>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-gray-500 text-sm">权重: {(dim.weight * 100).toFixed(0)}%</span>
                    <span className={clsx('text-xl font-bold', getScoreColor(dim.score))}>
                      {dim.score.toFixed(0)}分
                    </span>
                  </div>
                </div>
              ),
              children: (
                <div className="pl-8 space-y-3">
                  {dim.metrics_detail && dim.metrics_detail.length > 0 ? (
                    dim.metrics_detail.map((metric, idx) => (
                      <div 
                        key={idx}
                        className="bg-gray-800/30 rounded-lg p-3 cursor-pointer hover:bg-gray-800/50 transition-colors"
                        onClick={() => navigate(
                          `/diagnosis/${diagnosisId}/drill-down/${encodeURIComponent(metric.name)}?dimension=${dim.dimension}`
                        )}
                      >
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-gray-300">
                            {getMetricDisplayName(metric.name, metric.display_name)}
                            <span className="text-gray-600 ml-1">→</span>
                          </span>
                          <div className="flex items-center gap-3">
                            <span className={clsx('font-medium', getScoreColor(metric.score))}>
                              {metric.value}{metric.unit}
                            </span>
                            <span className="text-gray-500">({metric.score.toFixed(0)}分)</span>
                          </div>
                        </div>
                        <Progress 
                          percent={Math.min(100, metric.score)} 
                          size="small" 
                          showInfo={false}
                          strokeColor={getProgressColor(metric.score)}
                          trailColor="rgba(255,255,255,0.05)"
                        />
                        <div className="flex justify-between text-xs text-gray-600 mt-1">
                          <span>行业均值: {metric.benchmark_avg}{metric.unit}</span>
                          <span>优秀值: {metric.benchmark_excellent}{metric.unit}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <Empty description="暂无指标明细" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </div>
              ),
            };
          })}
        />
      </Card>

      {/* 异常指标分析（与仪表盘「异常指标预警」列表一致） */}
      {anomalies.length > 0 && (
        <Card
          title={
            <div className="flex items-center gap-3">
              <span className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
                ⚠️
              </span>
              <span className="text-base font-semibold">异常指标分析</span>
              <Tag color="red" className="!m-0 !ml-2 !px-3 !py-0.5 !text-xs !font-semibold">
                {anomalies.length}项需要关注
              </Tag>
            </div>
          }
          extra={
            <Button
              type="primary"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => navigate(`/solutions/${diagnosisId}`)}
            >
              查看优化方案
            </Button>
          }
        >
          <AnomalyList anomalies={anomalyListItems} diagnosisId={diagnosisId} />
        </Card>
      )}

      {/* 无异常时的提示 */}
      {anomalies.length === 0 && (
        <Card>
          <div className="text-center py-8">
            <CheckCircleOutlined className="text-6xl text-emerald-400 mb-4" />
            <div className="text-xl text-white mb-2">恭喜！未发现异常指标</div>
            <div className="text-gray-500">当前企业运营状况良好，请继续保持</div>
          </div>
        </Card>
      )}
    </div>
  );
}
