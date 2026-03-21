

import { Card, Row, Col, Button, Tag, Spin, Empty, App, Progress, Tooltip } from 'antd';
import { 
  ThunderboltOutlined, 
  CalendarOutlined,
  LoadingOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useMemo, useRef, useState } from 'react';
import { HealthScoreRing } from '@/components/diagnosis/health-score-ring';
import { RadarChart } from '@/components/diagnosis/radar-chart';
import { MetricCard, type MetricDetail } from '@/components/diagnosis/metric-card';
import { AnomalyList } from '@/components/diagnosis/anomaly-list';
import { 
  useLatestDiagnosisReport, 
  useStartDiagnosis,
  useCancelDiagnosis,
  useWebSocket,
  useDiagnosisTaskStatus,
  useSolutionList,
  useGenerateSolutions,
  useGenerationTask,
  useDimensionConfig,
  type DimensionConfig,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import { enterpriseApi, diagnosisApi } from '@/lib/api';
import dayjs from 'dayjs';
import type { SolutionGenerateResponse } from '@/lib/types';

// 维度映射
const dimensionMapping: Record<string, string> = {
  crm_sharing: 'crm',
  crm: 'crm',
  marketing: 'marketing',
  marketing_effect: 'marketing',
  retention: 'retention',
  customer_retention: 'retention',
  efficiency: 'efficiency',
  operation_efficiency: 'efficiency',
};

function normalizeDashboardDimension(d: string): string {
  return dimensionMapping[d] || d;
}

type DimScoreRow = {
  dimension: string;
  score: number;
  status: string;
  metrics_detail?: MetricDetail[];
};

function scoreToStatusFromScore(score: number): 'excellent' | 'good' | 'warning' | 'danger' {
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  if (score >= 40) return 'warning';
  return 'danger';
}

/** 将 crm / crm_sharing 等别名合并为一张卡，避免同一归一化维度重复显示相同异常数 */
function mergeDimensionScores(rows: DimScoreRow[]): Array<DimScoreRow & { rawDimension: string }> {
  const byNorm = new Map<string, DimScoreRow & { rawDimension: string }>();
  for (const d of rows) {
    const norm = normalizeDashboardDimension(d.dimension);
    const md = d.metrics_detail || [];
    const cur = byNorm.get(norm);
    if (!cur) {
      byNorm.set(norm, {
        ...d,
        dimension: norm,
        rawDimension: d.dimension,
        metrics_detail: [...md],
      });
    } else {
      if (!cur.metrics_detail) cur.metrics_detail = [];
      const seen = new Set(cur.metrics_detail.map((m) => m.name));
      for (const m of md) {
        if (!seen.has(m.name)) {
          cur.metrics_detail.push(m);
          seen.add(m.name);
        }
      }
      const mergedScore = Math.min(cur.score, d.score);
      cur.score = mergedScore;
      cur.status = scoreToStatusFromScore(mergedScore);
    }
  }
  return Array.from(byNorm.values());
}

type AnomalyForCount = { dimension: string; metric_name?: string; severity?: string };

/** 仅统计属于该卡指标范围内的异常（与下方列表一致）；metrics_detail 为空时按维度汇总 */
function countAnomaliesForMetricCard(
  anomalies: AnomalyForCount[] | undefined,
  normDimension: string,
  metricsDetail: Array<{ name: string }> | undefined
): { count: number; hasSevere: boolean } {
  const names = new Set((metricsDetail || []).map((m) => m.name));
  let count = 0;
  let hasSevere = false;
  for (const a of anomalies || []) {
    if (normalizeDashboardDimension(a.dimension) !== normDimension) continue;
    if (names.size > 0 && a.metric_name && !names.has(a.metric_name)) continue;
    count++;
    if (a.severity === 'critical' || a.severity === 'high') hasSevere = true;
  }
  return { count, hasSevere };
}

// 诊断阶段配置 - 根据消息关键词匹配
const diagnosisStagePatterns: Array<{ pattern: RegExp; label: string; icon: string }> = [
  { pattern: /初始化|加载.*配置/, label: '初始化', icon: '⚡' },
  { pattern: /CRM.*数据|CRM.*共享/, label: '采集 CRM 数据', icon: '📊' },
  { pattern: /营销.*数据|营销效果/, label: '采集营销数据', icon: '📣' },
  { pattern: /留存.*数据|客户留存/, label: '采集留存数据', icon: '👥' },
  { pattern: /运营.*数据|运营效率/, label: '采集运营数据', icon: '⚙️' },
  { pattern: /采集自定义维度/, label: '采集自定义维度', icon: '🔧' },
  { pattern: /采集|收集/, label: '数据采集', icon: '📊' },
  { pattern: /CRM.*规则/, label: '评估 CRM 规则', icon: '🔍' },
  { pattern: /营销.*规则/, label: '评估营销规则', icon: '🔍' },
  { pattern: /留存.*规则/, label: '评估留存规则', icon: '🔍' },
  { pattern: /运营.*规则/, label: '评估运营规则', icon: '🔍' },
  { pattern: /评估自定义维度规则/, label: '评估自定义规则', icon: '🔧' },
  { pattern: /异常检测|检测到.*异常/, label: '异常检测', icon: '🔍' },
  { pattern: /维度健康度/, label: '计算维度健康度', icon: '📈' },
  { pattern: /综合健康度|汇总/, label: '汇总健康度', icon: '📈' },
  { pattern: /健康度/, label: '健康度计算', icon: '📈' },
  { pattern: /分析异常.*\//, label: '根因分析中', icon: '🧠' },
  { pattern: /根因分析/, label: '根因分析', icon: '🧠' },
  { pattern: /保存.*指标|保存.*结果/, label: '保存结果', icon: '💾' },
  { pattern: /生成.*报告/, label: '生成报告', icon: '📝' },
  { pattern: /完成/, label: '诊断完成', icon: '✅' },
];

// 根据消息获取阶段信息
function getStageFromMessage(message: string): { label: string; icon: string } {
  for (const stage of diagnosisStagePatterns) {
    if (stage.pattern.test(message)) {
      return { label: stage.label, icon: stage.icon };
    }
  }
  return { label: message, icon: '⏳' };
}

function getAnalysisPeriodLabel(days?: number): string {
  if (days === 30) return '近30天';
  if (days === 60) return '近60天';
  if (days === 90) return '近90天';
  if (days === 180) return '近180天';
  return '近90天'; // 默认与设置一致
}

export default function DashboardPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  const { data: enterpriseDetail } = useQuery({
    queryKey: ['enterprise', enterpriseId],
    queryFn: () => enterpriseApi.get(enterpriseId!),
    enabled: !!enterpriseId,
  });
  const industry = (enterpriseDetail as { industry?: string } | undefined)?.industry || 'general';
  const analysisPeriodDays = (enterpriseDetail as { config?: { analysis_period_days?: number } } | undefined)?.config?.analysis_period_days;
  const analysisPeriodLabel = getAnalysisPeriodLabel(analysisPeriodDays);
  const autoDiagnosisFrequency = (enterpriseDetail as { config?: { auto_diagnosis_frequency?: string } } | undefined)?.config?.auto_diagnosis_frequency || 'weekly';
  
  // 频率标签映射
  const frequencyLabelMap: Record<string, string> = {
    daily: '每日',
    weekly: '每周',
    monthly: '每月',
    manual: '仅手动',
  };
  
  function getFrequencyLabel(frequency: string): string {
    return frequencyLabelMap[frequency] || '未设置';
  }
  
  // 计算下次诊断时间
  function getNextDiagnosisTime(frequency: string): string {
    if (frequency === 'manual') {
      return '仅手动';
    }
    
    const now = dayjs();
    switch (frequency) {
      case 'daily':
        return now.add(1, 'day').hour(2).minute(0).format('MM月DD日 HH:mm');
      case 'weekly':
        return now.add(1, 'week').startOf('week').add(1, 'day').hour(2).minute(0).format('MM月DD日 HH:mm');
      case 'monthly':
        return now.add(1, 'month').date(1).hour(2).minute(0).format('MM月DD日 HH:mm');
      default:
        return '未设置';
    }
  }
  
  const { 
    data: report, 
    isLoading, 
    latestDiagnosisId,
    lastDiagnosisDate,
    // 从列表获取的初始状态（进入页面时）
    latestDiagnosisStatus,
    latestDiagnosisProgress,
    latestDiagnosisMessage,
    refetchList,
  } = useLatestDiagnosisReport(enterpriseId);

  // 仅在有报告且报告无 benchmark 数据时才请求（无报告不展示雷达；有 report 且带 benchmark_dimension_scores 时不再请求）
  const reportBenchmark = (report as { benchmark_dimension_scores?: unknown[] } | undefined)?.benchmark_dimension_scores;
  const { data: benchmarkDimensionScoresData } = useQuery({
    queryKey: ['diagnosis', 'benchmark-dimension-scores', industry],
    queryFn: () => diagnosisApi.getBenchmarkDimensionScores(industry),
    enabled: !!enterpriseId && !!report && !(reportBenchmark?.length),
  });

  const startDiagnosis = useStartDiagnosis();

  // 使用统一的维度配置 hook
  const { 
    dimensionNameMap, 
    dimensionFirstMetricMap,
    metricNameMap,
    getDimensionDisplayName,
    getMetricDisplayName,
    allDimensions,
    isLoading: isDimensionsLoading,
  } = useDimensionConfig(enterpriseId);

  // 获取当前启用的维度名称集合（用于过滤历史报告中已禁用的维度）
  const enabledDimensionNames = useMemo(() => {
    return new Set(allDimensions.filter((d: DimensionConfig) => d.enabled).map((d: DimensionConfig) => d.name));
  }, [allDimensions]);
  
  // 判断是否所有维度都被禁用（维度已加载但无启用的维度）
  const allDimensionsDisabled = !isDimensionsLoading && allDimensions.length > 0 && enabledDimensionNames.size === 0;

  // WebSocket 连接
  useWebSocket(enterpriseId);
  
  const [isCancelling, setCancelling] = useState(false);
  const lastFailedRef = useRef<{ taskId: string; t: number }>({ taskId: '', t: 0 });
  const { tasks } = useDiagnosisTaskStatus(enterpriseId, {
    onCompleted: () => {
      queryClient.invalidateQueries({ queryKey: ['diagnosis', 'list', enterpriseId] });
      queryClient.invalidateQueries({ queryKey: ['diagnosis', 'report'] });
      message.success('诊断完成！数据已更新');
    },
    onFailed: (taskId, error) => {
      if (error === '已取消') return;
      const now = Date.now();
      if (lastFailedRef.current.taskId === taskId && now - lastFailedRef.current.t < 3000) return;
      lastFailedRef.current = { taskId, t: now };
      refetchList().then(() => {
        const data = queryClient.getQueryData<{ items?: Array<{ message?: string }> }>(['diagnosis', 'list', enterpriseId, 0, 1]);
        const latestMessage = data?.items?.[0]?.message ?? '';
        if (latestMessage.includes('已取消')) return;
        message.error(`诊断失败: ${error || '未知错误'}`);
      });
    },
    onCancelled: () => {
      setCancelling(false);
      queryClient.refetchQueries({ queryKey: ['diagnosis', 'list', enterpriseId, 0, 1] });
      message.success('已取消诊断');
    },
  });

  // 获取当前正在执行的诊断任务（优先使用 WebSocket 实时数据，否则使用列表中的初始状态）
  const runningTask = useMemo(() => {
    // 先从 WebSocket 任务中查找（仅当前企业）
    const wsTask = Object.values(tasks).find(
      t => (t.status === 'running' || t.status === 'pending') && t.enterprise_id === enterpriseId
    );
    if (wsTask) return wsTask;
    
    // 如果没有 WebSocket 数据，使用列表中的状态（进入页面时）
    if (latestDiagnosisStatus === 'running' || latestDiagnosisStatus === 'pending') {
      return {
        task_id: latestDiagnosisId || '',
        status: latestDiagnosisStatus,
        progress: latestDiagnosisProgress || 0,
        message: latestDiagnosisMessage || '处理中...',
      };
    }
    
    return null;
  }, [tasks, enterpriseId, latestDiagnosisStatus, latestDiagnosisProgress, latestDiagnosisMessage, latestDiagnosisId]);

  const isDiagnosing = !!runningTask;
  
  // 检查最新诊断是否失败
  const isLatestFailed = latestDiagnosisStatus === 'failed';
  
  // 获取当前诊断阶段信息
  const currentStage = useMemo(() => {
    if (!runningTask?.message) return null;
    return getStageFromMessage(runningTask.message);
  }, [runningTask?.message]);

  const cancelDiagnosis = useCancelDiagnosis(enterpriseId);

  // 处理启动诊断
  const handleStartDiagnosis = async () => {
    if (!enterpriseId) {
      message.warning('请先选择企业');
      return;
    }
    
    if (isDiagnosing) {
      message.info('诊断任务正在执行中，请稍候');
      return;
    }

    if (allDimensionsDisabled) {
      message.warning('当前没有启用的诊断维度，请先在设置中启用至少一个维度');
      return;
    }
    
    try {
      const result = await startDiagnosis.mutateAsync({
        enterprise_id: enterpriseId,
        trigger_type: 'manual',
        async_mode: true,
      });
      if (result.status === 'failed') {
        message.error(result.message || '诊断任务提交失败');
      } else if ((result as { already_running?: boolean }).already_running) {
        message.info('已有诊断任务在执行，已为您显示进度');
        await refetchList();
      } else {
        message.success('诊断任务已提交');
      }
    } catch (error: any) {
      message.error(error?.message || '启动诊断失败');
    }
  };

  const handleCancelDiagnosis = () => {
    if (!runningTask?.task_id) return;
    setCancelling(true);
    cancelDiagnosis.mutate(runningTask.task_id, {
      onSuccess: () => {
        setCancelling(false);
        // 不在此处弹「已取消诊断」，由 WebSocket onCancelled 统一弹一次，避免重复
      },
      onError: (e: any) => {
        const isTimeout = e?.code === 'ECONNABORTED' || /timeout/i.test(e?.message || '');
        if (isTimeout) {
          message.info('正在取消，请稍候…');
          return;
        }
        setCancelling(false);
        message.error(e?.message || '取消失败');
      },
    });
  };

  // 格式化日期
  const formatLastDiagnosisDate = () => {
    if (!lastDiagnosisDate) return '暂无记录';
    return dayjs(lastDiagnosisDate).format('M月D日 HH:mm:ss');
  };

  const mergedDimensionScores = useMemo(() => {
    const list = report?.health_score?.dimension_scores;
    if (!list?.length) return [];
    return mergeDimensionScores(list as DimScoreRow[]);
  }, [report?.health_score?.dimension_scores]);

  // 从报告中提取维度分数用于雷达图（显示上一次诊断的完整结果；已合并别名维度）
  const radarData = mergedDimensionScores.map((d) => ({
    dimension: d.dimension,
    score: d.score,
  }));
  const radarBenchmarkData = useMemo(() => {
    const fromReport = (report as { benchmark_dimension_scores?: { dimension: string; score: number }[] } | undefined)?.benchmark_dimension_scores;
    if (fromReport?.length) return fromReport.map((d) => ({ dimension: d.dimension, score: d.score }));
    return (benchmarkDimensionScoresData?.dimension_scores ?? []).map((d) => ({ dimension: d.dimension, score: d.score }));
  }, [report, benchmarkDimensionScoresData?.dimension_scores]);

  // 从报告中提取指标卡片数据（显示维度得分 + 异常摘要；与合并后的维度一致）
  const metricCards = mergedDimensionScores.map((d) => {
    const dimension = d.dimension;
    const dimAnomalies = countAnomaliesForMetricCard(
      report?.anomalies as AnomalyForCount[] | undefined,
      dimension,
      d.metrics_detail
    );
    return {
      dimension,
      rawDimension: d.rawDimension,
      metricName: getDefaultMetricName(dimension),
      title: getMetricTitle(dimension),
      value: `${Number.isInteger(d.score) ? d.score : d.score.toFixed(1)}分`,
      status: d.status as 'excellent' | 'good' | 'warning' | 'danger',
      metricsDetail: d.metrics_detail,
      anomalyCount: dimAnomalies.count,
      hasSevereAnomaly: dimAnomalies.hasSevere,
    };
  });

  // 获取默认指标名称（当没有异常时）
  function getDefaultMetricName(dimension: string): string {
    // 系统维度的静态映射
    const metricNames: Record<string, string> = {
      crm_sharing: 'crm_sharing_rate',
      crm: 'lead_conversion_rate',
      marketing: 'order_conversion_rate',
      marketing_effect: 'coupon_redemption_rate',
      retention: 'repurchase_rate',
      customer_retention: 'churn_rate',
      efficiency: 'service_order_completion_rate',
      operation_efficiency: 'shipping_timeliness',
    };
    // 优先使用静态映射，否则使用动态获取的第一个指标名称
    return metricNames[dimension] || dimensionFirstMetricMap[dimension] || dimension;
  }

  // 获取指标标题（优先使用动态映射）
  function getMetricTitle(dimension: string): string {
    // 优先使用动态获取的维度名称
    if (dimensionNameMap[dimension]) {
      return dimensionNameMap[dimension];
    }
    // 回退到静态映射
    const titles: Record<string, string> = {
      crm_sharing: '线索转化率',
      crm: 'CRM共享率',
      marketing: '营销触达ROI',
      marketing_effect: '营销效果',
      retention: '客户复购率',
      customer_retention: '客户留存',
      efficiency: '任务完成率',
      operation_efficiency: '运营效率',
    };
    return titles[dimension] || dimension;
  }

  // 获取方案列表（仅在有报告时请求，无报告时不展示异常/方案）
  const { data: solutionData } = useSolutionList(report ? (latestDiagnosisId ?? null) : null);
  const typedSolutionData = solutionData as SolutionGenerateResponse | undefined;
  const hasSolutions = (typedSolutionData?.solutions?.length || 0) > 0;
  
  // 计算已有方案的异常 ID 集合
  const anomalyIdsWithSolutions = useMemo(() => {
    const ids = new Set<string>();
    typedSolutionData?.solutions?.forEach(s => {
      s.anomaly_ids?.forEach(id => ids.add(id));
    });
    return ids;
  }, [typedSolutionData]);
  
  // 生成方案
  const generateSolutions = useGenerateSolutions();
  // 检测活跃的后台生成任务（仅在有报告时请求，无报告时不展示异常/生成状态）
  const { isGenerating: isBackgroundGenerating } = useGenerationTask(report ? (latestDiagnosisId ?? null) : null);
  // 从企业配置读取方案排序策略（设置页维护）
  const rankingStrategy = (enterpriseDetail as { config?: { solution_sort_strategy?: string } } | undefined)?.config?.solution_sort_strategy || 'balanced';
  
  // 处理生成方案
  const handleGenerateSolution = async (anomalyId: string) => {
    if (!enterpriseId || !latestDiagnosisId) {
      message.warning('请先完成诊断');
      return;
    }
    
    try {
      const result = await generateSolutions.mutateAsync({
        enterprise_id: enterpriseId,
        diagnosis_id: latestDiagnosisId,
        anomaly_ids: [anomalyId],
        ranking_strategy: rankingStrategy,
      });
      
      // 检查是否生成了方案
      const solutionCount = (result as { solution_count?: number })?.solution_count || 0;
      if (solutionCount === 0) {
        message.error('未能生成任何方案。可能没有匹配的方案模板，请稍后重试。');
        return;
      }
      
      message.success('方案生成成功，正在跳转到详情页...');
      navigate(`/solutions/${latestDiagnosisId}?anomaly_id=${anomalyId}`);
    } catch (error: any) {
      const errorMessage = error?.message || '方案生成失败';
      message.error(errorMessage);
    }
  };

  // 从报告中提取异常列表
  const anomalies = (report?.anomalies?.map(a => {
    // unit 优先使用 anomaly 自身的，fallback 到 metrics_detail 查找
    let unit = a.unit;
    if (!unit) {
      const ds = report?.health_score?.dimension_scores?.find(
        (d: { dimension: string }) => d.dimension === a.dimension
      );
      const md = ds?.metrics_detail?.find(
        (m: { name: string }) => m.name === a.metric_name
      );
      unit = md?.unit || '%';
    }
    return {
      id: a.id,
      name: a.rule_name,
      desc: `根因：${a.root_cause_chain.join(' → ')}`,
      currentValue: `${a.current_value.toFixed(1)}${unit}`,
      benchmark: a.benchmark_value ? `${a.benchmark_value.toFixed(1)}${unit}` : '-',
      gap: Math.abs(a.gap_percentage || 0),
      severity: (a.severity === 'critical' || a.severity === 'high' ? 'severe' : 'moderate') as 'severe' | 'moderate',
      metricName: a.metric_name,
      dimension: a.dimension,
    };
  }) || []) as Array<{
    id: string;
    name: string;
    desc: string;
    currentValue: string;
    benchmark: string;
    gap: number;
    severity: 'severe' | 'moderate';
    metricName: string;
    dimension: string;
  }>;

  // 获取趋势信息
  const trendInfo = report?.health_score?.trend as { change?: number; direction?: string } | undefined;
  const trendText = trendInfo?.change != null
    ? trendInfo.direction === 'stable'
      ? '📊 与上次持平'
      : `${trendInfo.direction === 'up' ? '📈' : '📉'} ${trendInfo.direction === 'up' ? '良好' : '下降'} · 较上次${trendInfo.direction === 'up' ? '提升' : '下降'}${Math.abs(trendInfo.change).toFixed(1)}分`
    : '📊 暂无趋势数据（需至少两次诊断）';

  // 如果没有选择企业
  if (!enterpriseId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Empty description="请先选择企业" />
      </div>
    );
  }

  // 加载中状态（首次加载且无缓存数据）
  if (isLoading && !report) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }

  // 诊断进度条组件
  const DiagnosisProgressBar = () => {
    if (!isDiagnosing && !isCancelling) return null;
    const cancelLoading = cancelDiagnosis.isPending || isCancelling;
    
    return (
      <div className="bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-blue-500/10 border border-blue-500/30 rounded-xl p-5 mb-6 animate-pulse-slow">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-blue-500/30 animate-bounce">
              {isCancelling ? '⏹' : (currentStage?.icon || '⏳')}
            </div>
            <div>
              <span className="text-blue-300 font-semibold text-base">
                {isCancelling ? '取消中…' : (currentStage?.label || '诊断任务执行中')}
              </span>
              <p className="text-gray-400 text-sm mt-0.5 max-w-md truncate">
                {isCancelling ? '后台正在停止任务，请稍候' : (runningTask?.message || '处理中...')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!isCancelling && (
              <Tag icon={<SyncOutlined spin />} color="processing" className="!px-3 !py-1 !text-sm">
                {runningTask?.progress || 0}%
              </Tag>
            )}
            <Button
              size="small"
              disabled={cancelLoading}
              onClick={handleCancelDiagnosis}
            >
              {cancelLoading ? '取消中…' : '取消诊断'}
            </Button>
          </div>
        </div>
        <Progress 
          percent={runningTask?.progress || 0} 
          status="active"
          strokeColor={{
            '0%': '#3b82f6',
            '50%': '#8b5cf6',
            '100%': '#06b6d4',
          }}
          trailColor="rgba(255,255,255,0.08)"
          showInfo={false}
          size={{ height: 8 }}
        />
        {report && (
          <p className="text-gray-500 text-xs mt-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
            下方显示的是上次诊断结果，新结果将在完成后自动更新
          </p>
        )}
      </div>
    );
  };

  // 诊断失败/取消提示组件
  const DiagnosisFailedAlert = () => {
    if (!isLatestFailed || isDiagnosing) return null;
    
    const isCancelled = (latestDiagnosisMessage || '').includes('已取消');
    const errorMessage = latestDiagnosisMessage || '诊断执行失败，请检查数据源连接';
    
    if (isCancelled) {
      return (
        <div className="bg-gray-500/10 border border-gray-500/30 rounded-xl p-5 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gray-500/50 flex items-center justify-center text-lg">
              ⏹
            </div>
            <div className="flex-1">
              <span className="text-gray-300 font-semibold text-base">诊断已取消</span>
              <p className="text-gray-400 text-sm mt-1">可点击上方「立即诊断」重新开始</p>
            </div>
          </div>
        </div>
      );
    }
    
    return (
      <div className="bg-gradient-to-r from-red-500/10 via-rose-500/10 to-red-500/10 border border-red-500/30 rounded-xl p-5 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center text-lg shadow-lg shadow-red-500/30">
            ❌
          </div>
          <div className="flex-1">
            <span className="text-red-300 font-semibold text-base">上次诊断执行失败</span>
            <p className="text-gray-300 text-sm mt-1 break-words">
              {errorMessage}
            </p>
            <p className="text-gray-400 text-xs mt-1">
              提示：请检查 mock-subsystem 服务是否正常运行，修复后点击上方「立即诊断」重试
            </p>
          </div>
        </div>
      </div>
    );
  };

  // 没有诊断数据
  if (!report) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-blue-500/20">
                📊
              </span>
              运营健康度仪表盘
            </h1>
            <div className="flex items-center gap-4 mt-2">
              <p className="text-gray-400 text-sm">
                基于{analysisPeriodLabel}数据，AI智能分析企业运营状况
              </p>
              {autoDiagnosisFrequency !== 'manual' ? (
                <Tooltip title={`下次自动诊断：${getNextDiagnosisTime(autoDiagnosisFrequency)}`}>
                  <Tag 
                    color="blue" 
                    className="cursor-pointer hover:opacity-80"
                    onClick={() => navigate('/settings?tab=general')}
                  >
                    <SyncOutlined className="mr-1" />
                    自动诊断：{getFrequencyLabel(autoDiagnosisFrequency)}
                  </Tag>
                </Tooltip>
              ) : (
                <Tag color="default">
                  <CalendarOutlined className="mr-1" />
                  仅手动诊断
                </Tag>
              )}
            </div>
          </div>
          <Button 
            type="primary" 
            icon={isDiagnosing ? <SyncOutlined spin /> : <ThunderboltOutlined />}
            loading={startDiagnosis.isPending}
            disabled={isDiagnosing}
            onClick={handleStartDiagnosis}
          >
            {isDiagnosing ? '诊断中...' : '立即诊断'}
          </Button>
        </div>
        
        {/* 诊断进度条 */}
        <DiagnosisProgressBar />
        
        {/* 诊断失败提示 */}
        <DiagnosisFailedAlert />
        
        {!isDiagnosing && !isLatestFailed && (
          <div className="flex items-center justify-center h-[50vh]">
            <Empty 
              description="暂无诊断数据，请点击「立即诊断」开始首次诊断" 
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-blue-500/20">
              📊
            </span>
            运营健康度仪表盘
          </h1>
          <div className="flex items-center gap-4 mt-2">
            <p className="text-gray-400 text-sm">
              基于{analysisPeriodLabel}数据，AI智能分析企业运营状况
            </p>
            {autoDiagnosisFrequency !== 'manual' ? (
              <Tooltip title={`下次自动诊断：${getNextDiagnosisTime(autoDiagnosisFrequency)}`}>
                <Tag 
                  color="blue" 
                  className="cursor-pointer hover:opacity-80"
                  onClick={() => navigate('/settings?tab=general')}
                >
                  <SyncOutlined className="mr-1" />
                  自动诊断：{getFrequencyLabel(autoDiagnosisFrequency)}
                </Tag>
              </Tooltip>
            ) : (
              <Tag color="default">
                <CalendarOutlined className="mr-1" />
                仅手动诊断
              </Tag>
            )}
          </div>
        </div>
        <div className="flex gap-3">
          <Button icon={<CalendarOutlined />} className="!flex !items-center !gap-2">
            上次诊断: {formatLastDiagnosisDate()}
          </Button>
          <Button 
            type="primary" 
            icon={isDiagnosing ? <SyncOutlined spin /> : <ThunderboltOutlined />}
            loading={startDiagnosis.isPending}
            disabled={isDiagnosing}
            onClick={handleStartDiagnosis}
          >
            {isDiagnosing ? '诊断中...' : '立即诊断'}
          </Button>
        </div>
      </div>

      {/* 诊断进度条 */}
      <DiagnosisProgressBar />

      {/* 诊断失败提示 */}
      <DiagnosisFailedAlert />

      {/* 健康度概览 */}
      <Row gutter={24} className={isDiagnosing ? 'opacity-70 transition-opacity' : 'transition-opacity'}>
        <Col span={10}>
          <Card className="h-full">
            <div className="text-center py-2">
              <h3 className="text-base font-semibold mb-6 text-gray-300 flex items-center justify-center gap-2">
                <span className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-500" />
                综合健康度
              </h3>
              <HealthScoreRing score={report.health_score.total_score} />
              <div className="mt-6">
                <Tag color="green" className="!px-4 !py-1.5 !text-sm !font-medium !rounded-lg">
                  {trendText}
                </Tag>
              </div>
              <div className="flex justify-center gap-8 mt-5 text-sm font-medium">
                {report.health_score.dimension_scores
                  .slice(0, 3)
                  .map(d => {
                    const change = d.score - 70; // 简化的变化计算
                    return (
                      <span 
                        key={d.dimension}
                        className={change >= 0 ? 'text-emerald-400 flex items-center gap-1' : 'text-rose-400 flex items-center gap-1'}
                      >
                        <span className="text-xs">{change >= 0 ? '▲' : '▼'}</span> 
                        {getMetricTitle(d.dimension).slice(0, 2)} {change >= 0 ? '+' : ''}{change.toFixed(0)}%
                      </span>
                    );
                  })}
              </div>
            </div>
          </Card>
        </Col>
        <Col span={14}>
          <Card className="h-full">
            <h3 className="text-base font-semibold mb-2 text-gray-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-gradient-to-r from-cyan-500 to-blue-500" />
              {radarData.length > 0 ? `${radarData.length}维度对比分析` : '多维度对比分析'}
            </h3>
            <RadarChart data={radarData} benchmarkData={radarBenchmarkData} dimensionNameMap={dimensionNameMap} />
          </Card>
        </Col>
      </Row>

      {/* 指标卡片 - 动态显示所有维度 */}
      <Row gutter={[16, 16]}>
        {metricCards.length > 0 ? (
          metricCards.map((card, index) => (
            <Col 
              key={card.dimension || index}
              xs={24} sm={12} md={8} lg={metricCards.length <= 4 ? 6 : 4}
            >
              <MetricCard
                title={card.title}
                value={card.value}
                status={card.status}
                dimension={card.dimension}
                anomalyCount={card.anomalyCount}
                hasSevereAnomaly={card.hasSevereAnomaly}
                metricsDetail={card.metricsDetail}
                onDetailClick={() => {
                  if (latestDiagnosisId && card.metricName) {
                    navigate(
                      `/diagnosis/${latestDiagnosisId}/drill-down/${encodeURIComponent(card.metricName)}?dimension=${card.rawDimension}`
                    );
                  }
                }}
                onMetricClick={(metricName) => {
                  if (latestDiagnosisId) {
                    navigate(
                      `/diagnosis/${latestDiagnosisId}/drill-down/${encodeURIComponent(metricName)}?dimension=${card.rawDimension}`
                    );
                  }
                }}
              />
            </Col>
          ))
        ) : (
          // 默认显示4个空卡片位置（无数据时）
          <>
            <Col span={6}><Card className="h-32" /></Col>
            <Col span={6}><Card className="h-32" /></Col>
            <Col span={6}><Card className="h-32" /></Col>
            <Col span={6}><Card className="h-32" /></Col>
          </>
        )}
      </Row>

      {/* 异常指标预警 */}
      <Card 
        title={
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
              ⚠️
            </span>
            <span className="text-base font-semibold">异常指标预警</span>
            {isDiagnosing ? (
              <Tag icon={<SyncOutlined spin />} color="processing" className="!m-0 !ml-2 !px-3 !py-0.5 !text-xs !font-semibold">
                诊断中...
              </Tag>
            ) : (
              <Tag color="red" className="!m-0 !ml-2 !px-3 !py-0.5 !text-xs !font-semibold">
                {anomalies.length}项需要关注
              </Tag>
            )}
          </div>
        }
        extra={
          !isDiagnosing && anomalies.length > 0 && latestDiagnosisId ? (
            <Button
              type="primary"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => navigate(`/solutions/${latestDiagnosisId}`)}
            >
              查看优化方案
            </Button>
          ) : null
        }
      >
        {isDiagnosing ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <SyncOutlined spin className="text-3xl text-blue-400 mb-4" />
            <p className="text-base">正在重新分析异常指标...</p>
            <p className="text-sm text-gray-500 mt-1">诊断完成后将显示最新的异常预警</p>
          </div>
        ) : (
            <AnomalyList 
              anomalies={anomalies}
              diagnosisId={latestDiagnosisId}
              hasSolutions={hasSolutions}
              anomalyIdsWithSolutions={anomalyIdsWithSolutions}
              generatingAnomalyId={isBackgroundGenerating || generateSolutions.isPending ? '__all__' : null}
              onGenerateSolution={handleGenerateSolution}
            />
        )}
      </Card>
    </div>
  );
}
