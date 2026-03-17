

import { Card, Row, Col, Tag, Spin, Empty, Progress, Descriptions, Collapse, Timeline, Button, Statistic, App } from 'antd';
import { 
  ArrowLeftOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  BulbOutlined,
  RiseOutlined,
  FallOutlined,
  ThunderboltOutlined,
  AimOutlined,
  FileSearchOutlined,
  LoadingOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useDiagnosisReport, useDimensionConfig, useSolutionList, useGenerateSolutions, useGenerationTask } from '@/lib/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '@/stores/app-store';
import { DiagnosisReport, DimensionScore, Anomaly, RootCauseAnalysis, MetricDetail, SolutionGenerateResponse } from '@/lib/types';
import { useMemo, useState, useEffect, useRef } from 'react';
import dayjs from 'dayjs';
import clsx from 'clsx';
import { getTagLabel } from '@/lib/tag-labels';

// 维度图标/颜色 fallback（动态配置优先）
const dimensionIconFallback: Record<string, { icon: string; color: string }> = {
  crm: { icon: '📊', color: 'blue' },
  marketing: { icon: '📈', color: 'purple' },
  retention: { icon: '👥', color: 'green' },
  efficiency: { icon: '⚙️', color: 'cyan' },
};

// 严重程度配置
const severityConfig: Record<string, { color: string; text: string; bgClass: string }> = {
  critical: { color: 'red', text: '严重', bgClass: 'bg-red-500/10 border-red-500/30' },
  severe: { color: 'red', text: '严重', bgClass: 'bg-red-500/10 border-red-500/30' },
  high: { color: 'orange', text: '较高', bgClass: 'bg-orange-500/10 border-orange-500/30' },
  moderate: { color: 'gold', text: '中等', bgClass: 'bg-amber-500/10 border-amber-500/30' },
  medium: { color: 'gold', text: '中等', bgClass: 'bg-amber-500/10 border-amber-500/30' },
  low: { color: 'blue', text: '轻微', bgClass: 'bg-blue-500/10 border-blue-500/30' },
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
  const { message } = App.useApp();
  const diagnosisId = params.diagnosisId as string;
  const queryClient = useQueryClient();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;
  
  const { data, isLoading } = useDiagnosisReport(diagnosisId);
  const report = data as DiagnosisReport | undefined;

  // 查询已有方案，判断每个异常是否已有方案
  const { data: solutionData } = useSolutionList(diagnosisId);
  const anomalyIdsWithSolutions = useMemo(() => {
    const ids = new Set<string>();
    (solutionData as SolutionGenerateResponse | undefined)?.solutions?.forEach(s => {
      s.anomaly_ids?.forEach(id => ids.add(id));
    });
    return ids;
  }, [solutionData]);

  // 生成方案
  const [generatingAnomalyId, setGeneratingAnomalyId] = useState<string | null>(null);
  const [overlayVisible, setOverlayVisible] = useState(false);
  const [progressStep, setProgressStep] = useState<number | null>(null);
  const [progressStatus, setProgressStatus] = useState<'generating' | 'success' | 'error'>('generating');
  
  const generateSolutions = useGenerateSolutions((step) => {
    setProgressStep(step);
  });
  
  const { isGenerating: isBackgroundGenerating, progressStep: backgroundProgressStep } = useGenerationTask(diagnosisId);

  const progressSteps = [
    { label: '正在分析异常指标...', icon: <LoadingOutlined spin /> },
    { label: '正在匹配解决方案库...', icon: <LoadingOutlined spin /> },
    { label: '正在生成优化方案...', icon: <LoadingOutlined spin /> },
    { label: '正在评估方案可行性...', icon: <LoadingOutlined spin /> },
  ];

  // 使用实际的进度步骤（优先使用当前任务的进度，否则使用后台任务的进度）
  const currentProgressStep = progressStep !== null ? progressStep : (backgroundProgressStep !== null ? backgroundProgressStep : null);

  // 处理方案按钮点击
  const handleSolutionAction = async (anomalyId: string) => {
    if (anomalyIdsWithSolutions.has(anomalyId)) {
      navigate(`/solutions/${diagnosisId}?anomaly_id=${anomalyId}`);
      return;
    }
    if (!enterpriseId) {
      message.warning('请先选择企业');
      return;
    }
    setGeneratingAnomalyId(anomalyId);
    setProgressStep(0);
    setProgressStatus('generating');
    setOverlayVisible(true);
    try {
      const result = await generateSolutions.mutateAsync({
        enterprise_id: enterpriseId,
        diagnosis_id: diagnosisId,
        anomaly_ids: [anomalyId],
        ranking_strategy: 'balanced',
      });
      
      // 检查是否生成了方案
      const solutionCount = (result as { solution_count?: number })?.solution_count || 0;
      if (solutionCount === 0) {
        setProgressStatus('error');
        message.error('未能生成任何方案。可能原因：异常指标没有匹配的解决方案标签，或没有找到匹配的方案模板。');
        setGeneratingAnomalyId(null);
        setTimeout(() => {
          setOverlayVisible(false);
          setProgressStep(null);
        }, 2000);
        return;
      }
      
      setProgressStatus('success');
      // 等待缓存刷新完成，确保跳转后能拿到最新数据
      await queryClient.refetchQueries({ queryKey: ['solutions', 'list', diagnosisId] });
      const targetUrl = `/solutions/${diagnosisId}?anomaly_id=${anomalyId}`;
      // 显示成功状态 1s 后跳转
      setTimeout(() => {
        setOverlayVisible(false);
        setProgressStep(null);
        setGeneratingAnomalyId(null);
        navigate(targetUrl);
      }, 1000);
    } catch (error: any) {
      setProgressStatus('error');
      setGeneratingAnomalyId(null);
      const errorMessage = error?.message || '方案生成失败';
      message.error(errorMessage);
      setTimeout(() => {
        setOverlayVisible(false);
        setProgressStep(null);
      }, 1500);
    }
  };

  // 使用动态维度配置（替代硬编码映射）
  const {
    getDimensionDisplayName,
    getMetricDisplayName: getDynMetricDisplayName,
  } = useDimensionConfig(enterpriseId);

  // 获取指标显示名称（优先后端 display_name → 动态配置 → 原始名称）
  function getMetricDisplayName(name: string, displayName?: string): string {
    return displayName || getDynMetricDisplayName(name) || name;
  }

  // 获取维度图标
  function getDimIcon(dimension: string): string {
    return dimensionIconFallback[dimension]?.icon || '📋';
  }

  // 获取维度颜色
  function getDimColor(dimension: string): string {
    return dimensionIconFallback[dimension]?.color || 'default';
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
      {/* 生成方案蒙版 */}
      {overlayVisible && (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gray-900/95 border border-gray-700/60 rounded-2xl p-8 w-[420px] shadow-2xl">
            {progressStatus === 'success' ? (
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                  <CheckOutlined className="text-3xl text-emerald-400" />
                </div>
                <div className="text-xl font-semibold text-white mb-2">方案生成完成</div>
                <div className="text-gray-400 text-sm">正在跳转到方案详情...</div>
              </div>
            ) : progressStatus === 'error' ? (
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-rose-500/20 flex items-center justify-center mx-auto mb-4">
                  <ExclamationCircleOutlined className="text-3xl text-rose-400" />
                </div>
                <div className="text-xl font-semibold text-white mb-2">生成失败</div>
                <div className="text-gray-400 text-sm">请稍后重试</div>
              </div>
            ) : (
              <div>
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <BulbOutlined className="text-3xl text-blue-400 animate-pulse" />
                  </div>
                </div>
                <div className="text-center text-xl font-semibold text-white mb-6">AI 正在生成优化方案</div>
                <div className="space-y-3">
                  {progressSteps.map((step, idx) => {
                    const stepValue = currentProgressStep ?? -1;
                    return (
                      <div 
                        key={idx}
                        className={clsx(
                          'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-500',
                          idx < stepValue ? 'bg-emerald-500/10' :
                          idx === stepValue ? 'bg-blue-500/10' :
                          'bg-gray-800/30 opacity-40'
                        )}
                      >
                        <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                          {idx < stepValue ? (
                            <CheckOutlined className="text-emerald-400" />
                          ) : idx === stepValue ? (
                            <LoadingOutlined spin className="text-blue-400" />
                          ) : (
                            <span className="w-2 h-2 rounded-full bg-gray-600" />
                          )}
                        </span>
                        <span className={clsx(
                          'text-sm',
                          idx < stepValue ? 'text-emerald-400' :
                          idx === stepValue ? 'text-blue-300' :
                          'text-gray-500'
                        )}>
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-6">
                  <Progress 
                    percent={currentProgressStep !== null ? Math.min(95, ((currentProgressStep + 1) / progressSteps.length) * 90) : 0}
                    showInfo={false}
                    strokeColor={{ from: '#3b82f6', to: '#06b6d4' }}
                    trailColor="rgba(255,255,255,0.05)"
                    strokeWidth={6}
                  />
                </div>
                <div className="text-center text-gray-500 text-xs mt-3">预计需要 10-30 秒，请稍候...</div>
              </div>
            )}
          </div>
        </div>
      )}

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
        <div className="flex items-center gap-3">
          <div className="text-right text-sm text-gray-500 mr-4 hidden md:block">
            <div>诊断时间: {dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}</div>
          </div>
          <Button 
            type="primary" 
            icon={<ThunderboltOutlined />}
            onClick={() => navigate(`/solutions/${diagnosisId}`)}
          >
            查看优化方案
          </Button>
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
                {trend?.change ? (
                  <span className={clsx(
                    'flex items-center gap-1 font-medium',
                    trend.direction === 'up' ? 'text-emerald-400' : 'text-rose-400'
                  )}>
                    {trend.direction === 'up' ? <RiseOutlined /> : <FallOutlined />}
                    较上期{trend.direction === 'up' ? '提升' : '下降'} {Math.abs(trend.change).toFixed(1)} 分
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

      {/* 异常指标分析 */}
      {anomalies.length > 0 && (
        <Card 
          title={
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400 text-sm">
                <WarningOutlined />
              </span>
              <span>异常指标分析</span>
              <Tag color="error">{anomalies.length}项异常</Tag>
            </div>
          }
        >
          <div className="space-y-4">
            {anomalies.map((anomaly) => {
              const severity = severityConfig[anomaly.severity] || severityConfig.moderate;
              const matchingRca = rootCauseAnalyses.find(r => r.metric_name === anomaly.metric_name);
              // unit: anomaly → metrics_detail → 默认 %
              const _ds = dimensionScores.find(ds => ds.dimension === anomaly.dimension);
              const _md = _ds?.metrics_detail?.find((m: MetricDetail) => m.name === anomaly.metric_name);
              const unit = anomaly.unit || _md?.unit || '%';
              
              return (
                <div 
                  key={anomaly.id}
                  className={clsx(
                    'rounded-xl border p-4',
                    severity.bgClass
                  )}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <ExclamationCircleOutlined className="text-amber-400" />
                        <span className="text-white font-medium text-lg">{anomaly.rule_name}</span>
                        <Tag color={severity.color}>{severity.text}</Tag>
                      </div>
                      <div className="text-gray-500 text-sm">
                        指标: {getMetricDisplayName(anomaly.metric_name)} | 
                        维度: {getDimensionDisplayName(anomaly.dimension)}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        size="small"
                        onClick={() => navigate(
                          `/diagnosis/${diagnosisId}/drill-down/${encodeURIComponent(anomaly.metric_name)}?dimension=${anomaly.dimension}`
                        )}
                      >
                        数据钻取
                      </Button>
                      <Button
                        size="small"
                        type={anomalyIdsWithSolutions.has(anomaly.id) ? 'primary' : 'default'}
                        icon={<BulbOutlined />}
                        loading={(generatingAnomalyId === anomaly.id && generateSolutions.isPending) || isBackgroundGenerating}
                        disabled={isBackgroundGenerating}
                        onClick={() => handleSolutionAction(anomaly.id)}
                      >
                        {isBackgroundGenerating ? '方案生成中...' : anomalyIdsWithSolutions.has(anomaly.id) ? '查看方案' : '生成方案'}
                      </Button>
                    </div>
                  </div>

                  {/* 数值对比 */}
                  <Row gutter={16} className="mb-4">
                    <Col span={8}>
                      <Statistic 
                        title="当前值"
                        value={anomaly.current_value}
                        suffix={unit}
                        valueStyle={{ color: '#f43f5e', fontSize: 24 }}
                        prefix={<FallOutlined />}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic 
                        title="行业基准"
                        value={anomaly.benchmark_value || '-'}
                        suffix={unit}
                        valueStyle={{ color: '#10b981', fontSize: 24 }}
                        prefix={<RiseOutlined />}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic 
                        title="差距"
                        value={anomaly.gap_percentage?.toFixed(1) || '-'}
                        suffix="%"
                        valueStyle={{ 
                          color: (anomaly.gap_percentage || 0) < 0 ? '#f43f5e' : '#10b981', 
                          fontSize: 24 
                        }}
                      />
                    </Col>
                  </Row>

                  {/* 根因链 */}
                  {anomaly.root_cause_chain && anomaly.root_cause_chain.length > 0 && (
                    <div className="mb-4">
                      <div className="text-gray-400 text-sm mb-2 flex items-center gap-1">
                        <BulbOutlined />
                        根因链路
                      </div>
                      <Timeline
                        mode="left"
                        items={anomaly.root_cause_chain.map((cause, idx) => ({
                          color: idx === anomaly.root_cause_chain.length - 1 ? 'red' : 'blue',
                          children: (
                            <span className={idx === anomaly.root_cause_chain.length - 1 ? 'text-rose-400 font-medium' : 'text-gray-300'}>
                              {cause}
                            </span>
                          ),
                        }))}
                      />
                    </div>
                  )}

                  {/* AI 分析解释 */}
                  {matchingRca?.explanation && (
                    <div className="bg-gray-900/50 rounded-lg p-3 mt-3">
                      <div className="text-gray-400 text-sm mb-2 flex items-center gap-1">
                        <BulbOutlined className="text-amber-400" />
                        AI 分析说明
                      </div>
                      <div className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">
                        {matchingRca.explanation.length > 500 
                          ? matchingRca.explanation.substring(0, 500) + '...' 
                          : matchingRca.explanation}
                      </div>
                    </div>
                  )}

                  {/* 推荐措施 */}
                  {matchingRca?.recommendations && matchingRca.recommendations.length > 0 && (
                    <div className="mt-3">
                      <div className="text-gray-400 text-sm mb-2 flex items-center gap-1">
                        <CheckCircleOutlined className="text-emerald-400" />
                        推荐改善措施
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {matchingRca.recommendations.map((rec, idx) => (
                          <div 
                            key={idx}
                            className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2 text-sm text-emerald-400"
                          >
                            {idx + 1}. {rec}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 方案标签 */}
                  {anomaly.solution_tags && anomaly.solution_tags.length > 0 && (
                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                      <span className="text-gray-500 text-xs">相关方案:</span>
                      {anomaly.solution_tags.map((tag) => (
                        <Tag key={tag} color="cyan" className="!text-xs">
                          {getTagLabel(tag)}
                        </Tag>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
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
