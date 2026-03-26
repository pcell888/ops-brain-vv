import { useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { App, Button, Card, Empty, Modal, Spin, Tag } from 'antd';
import {
  DashboardOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  LineChartOutlined,
  StopOutlined,
  SyncOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import ReactECharts from 'echarts-for-react';
import { DiagnosisHistorySelect } from '@/components/diagnosis-history-select';
import {
  useAnalyzeEffect,
  useCancelTracking,
  useCompleteTracking,
  useDiagnosisSelection,
  useMetricTrends,
  useTrackingSnapshots,
  useTakeSnapshot,
  useTrackingSummary,
} from '@/lib/hooks';
import { trackingApi } from '@/lib/api';
import { useAppStore } from '@/stores/app-store';

const indicatorNameMap: Record<string, string> = {
  lead_conversion_rate: '线索转化率',
  conversion_rate: '线索转化率',
  order_conversion_rate: '订单转化率',
  browse_to_order_rate: '浏览-下单转化率',
  seckill_conversion_rate: '秒杀转化率',
  coupon_redemption_rate: '优惠券核销率',
  response_time_avg: '平均响应时间',
  avg_response_time: '平均响应时间',
  follow_up_count: '跟进次数',
  repurchase_rate: '复购率',
  refund_rate: '退款率',
  churn_rate: '流失率',
  positive_review_rate: '好评率',
  avg_customer_lifetime_value: '客单终身价值',
  service_completion_rate: '服务完成率',
  avg_shipping_hours: '平均发货时长',
  task_on_time_rate: '任务按时完成率',
};

const indicatorDirectionMap: Record<string, 'higher_is_better' | 'lower_is_better'> = {
  conversion_rate: 'higher_is_better',
  avg_response_time: 'lower_is_better',
  churn_rate: 'lower_is_better',
  refund_rate: 'lower_is_better',
};

const statusColorMap: Record<string, string> = {
  active: 'processing',
  completed: 'success',
  scheduled: 'warning',
  cancelled: 'default',
  paused: 'warning',
};

const statusTextMap: Record<string, string> = {
  active: '追踪中',
  completed: '已完成',
  scheduled: '待自动复盘',
  cancelled: '已取消',
  paused: '已暂停',
};

interface AnalyzeResult {
  latest_score?: number | null;
  trend?: 'improving' | 'declining' | 'stable' | 'insufficient_data' | 'no_data' | 'error';
  snapshots?: number;
  score_change?: number;
  recommendations?: string[];
  risk_hint?: string;
}

interface TrendsResult {
  timestamps?: string[];
  indicators?: Record<string, Array<number | null>>;
}

interface SnapshotIndicatorChange {
  indicator_code: string;
  name: string;
  value: number;
  unit?: string;
}

interface SnapshotItem {
  snapshot_id: string;
  snapshot_at: string;
  health_score?: number;
  snapshot_type?: 'baseline' | 'periodic' | 'closing' | string;
  indicator_count: number;
  indicator_changes?: SnapshotIndicatorChange[];
}

function getTrackingDays(startedAt?: string, endedAt?: string): number {
  if (!startedAt) return 0;
  const start = dayjs(startedAt);
  const end = endedAt ? dayjs(endedAt) : dayjs();
  return Math.max(0, end.diff(start, 'day'));
}

export default function TrackingDetailPage() {
  const { message } = App.useApp();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;
  const {
    diagnosisItems,
    selectedDiagnosisId,
    setSelectedDiagnosisId,
    listLoading: diagnosisLoading,
  } = useDiagnosisSelection(enterpriseId);

  const { data: fallbackList, isLoading: listLoading } = useQuery({
    queryKey: ['tracking', 'fallback-first', enterpriseId, selectedDiagnosisId],
    queryFn: () => trackingApi.list({
      enterprise_id: enterpriseId!,
      diagnosis_id: selectedDiagnosisId || undefined,
      skip: 0,
      limit: 1,
    }),
    enabled: !!enterpriseId && !!selectedDiagnosisId,
  });

  /** 本页为「当前选中诊断」下的效果追踪统计：由 diagnosis_id 拉列表，取该诊断下最新一条追踪（与 URL 无关） */
  const resolvedTrackingId = fallbackList?.items?.[0]?.tracking_id ?? '';

  const { data: summary, isLoading: summaryLoading, isError } = useTrackingSummary(resolvedTrackingId || null);
  const { data: analyzeData, isLoading: analyzeLoading } = useAnalyzeEffect(
    resolvedTrackingId || null,
    { enabled: !!resolvedTrackingId },
  );
  const { data: trendsData, isLoading: trendsLoading } = useMetricTrends(
    resolvedTrackingId || null,
    { enabled: !!resolvedTrackingId },
  );
  const { data: snapshotsData, isLoading: snapshotsLoading } = useTrackingSnapshots(
    resolvedTrackingId || null,
    { enabled: !!resolvedTrackingId },
  );
  const takeSnapshot = useTakeSnapshot();
  const completeTracking = useCompleteTracking();
  const cancelTracking = useCancelTracking();

  const analyze = (analyzeData ?? {}) as AnalyzeResult;
  const trends = (trendsData ?? {}) as TrendsResult;

  const trendItems = useMemo(() => {
    const indicators = trends.indicators ?? {};
    const items = Object.entries(indicators).map(([code, values]) => {
      const cleanValues = (values ?? []).filter((v): v is number => typeof v === 'number');
      const first = cleanValues.length ? cleanValues[0] : null;
      const latest = cleanValues.length ? cleanValues[cleanValues.length - 1] : null;
      const pct = first != null && first !== 0 && latest != null
        ? ((latest - first) / Math.abs(first)) * 100
        : 0;
      const direction = indicatorDirectionMap[code] ?? 'higher_is_better';
      const scorePct = direction === 'lower_is_better' ? -pct : pct;
      return {
        code,
        name: indicatorNameMap[code] || code,
        latest,
        pct,
        scorePct,
      };
    });

    if (items.length) return items;
    return [
      { code: 'conversion_rate', name: '线索转化率', latest: 9.8, pct: 0, scorePct: 0 },
      { code: 'avg_response_time', name: '平均响应时间', latest: 4.9, pct: 0, scorePct: 0 },
    ];
  }, [trends.indicators]);

  const trendChartOption = useMemo(() => {
    const timestamps = trends.timestamps ?? [];
    const indicators = trends.indicators ?? {};
    const indicatorCodes = Object.keys(indicators);
    const xAxisLabels = timestamps.map((ts) => dayjs(ts).format('MM-DD HH:mm'));

    const series = indicatorCodes.map((code) => {
      const rawValues = indicators[code] ?? [];
      const alignedValues = xAxisLabels.map((_, idx) => {
        const value = rawValues[idx];
        return typeof value === 'number' ? value : null;
      });
      return {
        name: indicatorNameMap[code] || code,
        type: 'line',
        smooth: true,
        connectNulls: false,
        showSymbol: true,
        symbolSize: 6,
        data: alignedValues,
      };
    });

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        type: 'scroll',
        top: 8,
        textStyle: { color: '#303133' },
      },
      grid: {
        left: 40,
        right: 24,
        top: 56,
        bottom: 48,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: xAxisLabels,
        axisLabel: { color: '#606266' },
        axisLine: { lineStyle: { color: '#dcdfe6' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#606266' },
        splitLine: { lineStyle: { color: 'rgba(220,224,227,0.5)' } },
      },
      series,
    };
  }, [trends.timestamps, trends.indicators]);

  const improvedCount = useMemo(
    () => trendItems.filter((item) => item.scorePct > 0).length,
    [trendItems],
  );

  const targetRate = useMemo(
    () => (trendItems.length ? Math.round((improvedCount / trendItems.length) * 100) : 0),
    [trendItems.length, improvedCount],
  );

  const analysisSuggestions = useMemo(() => {
    if (Array.isArray(analyze.recommendations) && analyze.recommendations.length > 0) {
      return analyze.recommendations.slice(0, 4);
    }
    const suggestions: string[] = [];
    const snapshotCount = analyze.snapshots ?? 0;
    const scoreChange = Number(analyze.score_change ?? 0);
    const hasTrendMetrics = trendItems.length > 0;

    if (snapshotCount < 3) {
      suggestions.push('建议增加快照采集频次（至少 3 次），提升趋势判断可靠性');
    }
    if (!hasTrendMetrics) {
      suggestions.push('建议在方案中补充可量化目标指标，便于评估执行成效');
    } else if (improvedCount === 0) {
      suggestions.push('当前核心指标暂无改善，建议复核执行动作与目标指标匹配度');
    }
    if (analyze.trend === 'declining' || scoreChange < 0) {
      suggestions.push('评分趋势下行，建议优先排查近期波动最大的负向指标');
    } else if (targetRate < 60) {
      suggestions.push('目标达成率偏低，建议聚焦 1-2 个关键指标做阶段性优化');
    }

    if (suggestions.length === 0) {
      suggestions.push('当前表现总体稳定，建议保持策略并持续跟踪关键指标波动');
    }
    return suggestions.slice(0, 4);
  }, [analyze.recommendations, analyze.score_change, analyze.snapshots, analyze.trend, improvedCount, targetRate, trendItems.length]);

  const riskHint = useMemo(() => {
    if (typeof analyze.risk_hint === 'string' && analyze.risk_hint.trim()) {
      return analyze.risk_hint;
    }
    const snapshotCount = analyze.snapshots ?? 0;
    const scoreChange = Number(analyze.score_change ?? 0);
    if (snapshotCount < 2) {
      return '⚠ 数据采集不足，无法准确评估风险';
    }
    if (analyze.trend === 'declining' || scoreChange < 0) {
      return '⚠ 近期评分呈下行趋势，建议尽快定位并处置风险指标';
    }
    if (targetRate < 50) {
      return '⚠ 目标达成率偏低，存在执行偏差风险';
    }
    return '✅ 当前风险整体可控，请继续保持稳定采集与复盘';
  }, [analyze.risk_hint, analyze.score_change, analyze.snapshots, analyze.trend, targetRate]);

  /** 去掉历史遗留的 ?trackingId / ?snapshotId，本页仅以诊断选择为准 */
  useEffect(() => {
    if (searchParams.has('trackingId') || searchParams.has('snapshotId')) {
      navigate('/tracking', { replace: true });
    }
  }, [searchParams, navigate]);

  if (diagnosisLoading || listLoading || summaryLoading || analyzeLoading || trendsLoading || snapshotsLoading) {
    return (
      <div className='flex h-[60vh] items-center justify-center'>
        <Spin size='large' />
      </div>
    );
  }

  if (!resolvedTrackingId) {
    const description = selectedDiagnosisId
      ? <span className='text-[#303133]'>当前诊断暂无效果追踪数据，请在执行中产生追踪记录或切换历史诊断</span>
      : <span className='text-[#303133]'>暂无效果追踪数据，请先选择历史诊断</span>;
    return <Empty description={description} />;
  }

  if (isError || !summary) {
    return <Empty description={<span className='text-[#303133]'>追踪记录不存在或无法加载</span>} />;
  }

  const statusText = statusTextMap[summary.status] || summary.status || '-';
  const statusDotIcon = summary.status === 'active'
    ? <SyncOutlined spin className='text-[11px]' />
    : summary.status === 'completed'
      ? <CheckCircleOutlined className='text-[11px]' />
      : <ClockCircleOutlined className='text-[11px]' />;
  const score = analyze.latest_score == null ? 0 : Math.max(0, Math.round(Number(analyze.latest_score)));
  const days = getTrackingDays(summary.started_at, summary.completed_at);
  const totalDaysRaw = Number(summary.total_duration_days);
  const totalDays = Number.isFinite(totalDaysRaw) && totalDaysRaw > 0 ? Math.round(totalDaysRaw) : null;
  const canOperate = !!resolvedTrackingId && summary.status === 'active';
  const snapshotItems = ((snapshotsData as { items?: SnapshotItem[] } | undefined)?.items ?? []).slice();

  const handleSnapshot = async () => {
    if (!resolvedTrackingId) return;
    try {
      await takeSnapshot.mutateAsync({ trackingId: resolvedTrackingId, enterpriseId });
      message.success('快照已采集');
    } catch {
      message.error('快照采集失败');
    }
  };

  const handleComplete = () => {
    if (!resolvedTrackingId) return;
    Modal.confirm({
      title: '完成追踪',
      content: '确认完成当前追踪并进入复盘阶段？',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        await completeTracking.mutateAsync(resolvedTrackingId);
        message.success('追踪已完成');
      },
    });
  };

  const handleStop = () => {
    if (!resolvedTrackingId) return;
    Modal.confirm({
      title: '停止追踪',
      content: '确认停止当前追踪？停止后将不再继续采集。',
      okText: '确认停止',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        await cancelTracking.mutateAsync(resolvedTrackingId);
        message.success('追踪已停止');
      },
    });
  };

  return (
    <div className='space-y-5'>
      <div className='flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between'>
        <div>
          {/* <h1 className='flex items-center gap-3 text-2xl font-bold text-[#303133] text-primary'>
            <span className='flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 text-lg shadow-lg shadow-purple-500/20 text-[#fff]'>
              <LineChartOutlined />
            </span>
            效果追踪
          </h1> */}
          <p className='mt-2 text-sm text-secondary text-[#303133]'>追踪状态、快照趋势与效果分析总览</p>
        </div>
        <div className='flex flex-col items-stretch gap-3 lg:items-end'>
          {diagnosisItems.length > 0 && (
            <DiagnosisHistorySelect
              className='w-full lg:w-[340px]'
              diagnosisItems={diagnosisItems}
              value={selectedDiagnosisId}
              onChange={setSelectedDiagnosisId}
              loading={diagnosisLoading}
            />
          )}
          <div className='flex flex-wrap items-center gap-2'>
            {summary.status === 'completed' ? (
              <Button
                type='primary'
                icon={<EyeOutlined />}
                onClick={() => navigate(`/tracking/${resolvedTrackingId}/report`)}
              >
                查看复盘报告
              </Button>
            ) : (
              <>
                <Button
                  icon={<CameraOutlined />}
                  onClick={handleSnapshot}
                  loading={takeSnapshot.isPending}
                  disabled={!canOperate}
                  style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}
                >
                  采集快照
                </Button>
                <Button
                  type='primary'
                  icon={<CheckCircleOutlined />}
                  onClick={handleComplete}
                  loading={completeTracking.isPending}
                  disabled={!canOperate}
                >
                  完成追踪
                </Button>
                <Button
                  icon={<StopOutlined />}
                  onClick={handleStop}
                  loading={cancelTracking.isPending}
                  disabled={!canOperate}
                  style={
                    !canOperate
                      ? { color: '#303133' }
                      : { background: '#FF4D4F', border: 'none', color: '#fff' }
                  }
                >
                  停止
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4'>
        <Card className='border-gray-200 bg-[#F0F1F9]'>
          <div className='flex items-center gap-3'>
            <span className='flex h-10 w-10 items-center justify-center rounded-xl border border-blue-200 bg-blue-50 text-blue-600'>
              <DashboardOutlined />
            </span>
            <div>
              <div className='text-xs text-secondary mb-1'>追踪状态</div>
              <span className='inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-[2px] text-xs text-blue-600 leading-none'>
                {statusDotIcon}
                {statusText}
              </span>
            </div>
          </div>
        </Card>

        <Card className='border-gray-200 bg-[#F0F1F9]'>
          <div className='flex items-center gap-3'>
            <span className='flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600'>
              <TrophyOutlined />
            </span>
            <div>
              <div className='text-xs text-secondary'>当前评分</div>
              <div className='text-[32px] font-semibold leading-none text-primary'>{score} 分</div>
            </div>
          </div>
        </Card>

        <Card className='border-gray-200 bg-[#F0F1F9]'>
          <div className='flex items-center gap-3'>
            <span className='flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600'>
              <CameraOutlined />
            </span>
            <div>
              <div className='text-xs text-secondary'>快照数量</div>
              <div className='text-[32px] font-semibold leading-none text-amber-600'>{summary.snapshot_count ?? 0} 个</div>
            </div>
          </div>
        </Card>

        <Card className='border-gray-200 bg-[#F0F1F9]'>
          <div className='flex items-center gap-3'>
            <span className='flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-600'>
              <ClockCircleOutlined />
            </span>
            <div>
              <div className='text-xs text-secondary'>追踪时长</div>
              <div className='text-[32px] font-semibold leading-none text-purple-600'>
                {totalDays ? `${days} / ${totalDays} 天` : `${days} 天`}
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card
        title={(
          <span className='flex items-center gap-2 text-primary'>
            <EyeOutlined className='text-sky-600' />
            基本信息
          </span>
        )}
        className='border-gray-200 bg-[#F0F1F9]'
      >
        <div className='overflow-hidden rounded-lg border border-gray-200 bg-gray-50'>
          <div className='grid grid-cols-12 border-b border-gray-200'>
            <div className='col-span-2 bg-gray-100 px-4 py-2.5 text-secondary text-sm'>方案名称</div>
            <div className='col-span-10 px-4 py-2.5 text-primary text-sm'>{summary.solution_name || '-'}</div>
          </div>
          <div className='grid grid-cols-12'>
            <div className='col-span-2 bg-gray-100 px-4 py-2.5 text-secondary text-sm'>开始时间</div>
            <div className='col-span-4 px-4 py-2.5 text-primary text-sm'>
              {summary.started_at ? dayjs(summary.started_at).format('YYYY-MM-DD HH:mm') : '-'}
            </div>
            <div className='col-span-2 border-l border-gray-200 bg-gray-100 px-4 py-2.5 text-secondary text-sm'>最近快照</div>
            <div className='col-span-4 px-4 py-2.5 text-primary text-sm'>
              {summary.last_snapshot_at ? dayjs(summary.last_snapshot_at).format('YYYY-MM-DD HH:mm') : '-'}
            </div>
          </div>
        </div>
      </Card>

      <div className='grid grid-cols-1 gap-4 xl:grid-cols-2'>
        <Card
          title={(
            <span className='flex items-center gap-2 text-primary'>
              <LineChartOutlined className='text-cyan-600' />
              效果分析
            </span>
          )}
          className='border-gray-200 bg-[#F0F1F9]'
        >
          <div className='mb-4 grid grid-cols-3 gap-2'>
            <div>
              <div className='text-secondary text-sm'>整体效果评分</div>
              <div className='text-[40px] leading-none font-semibold text-amber-600'>{score}分</div>
            </div>
            <div>
              <div className='text-secondary text-sm'>目标达成率</div>
              <div className='text-[36px] leading-none font-semibold text-primary'>{targetRate}%</div>
            </div>
            <div>
              <div className='text-secondary text-sm'>改善指标数</div>
              <div className='text-[36px] leading-none font-semibold text-emerald-600'>{improvedCount}个</div>
            </div>
          </div>

          <div className='space-y-2 text-sm text-primary'>
            <div className='text-secondary'>分析建议</div>
            {analysisSuggestions.map((item) => (
              <div key={item}>💡 {item}</div>
            ))}
          </div>

          <div className='mt-4 rounded-md border border-amber-200 bg-rose-50 px-3 py-2 text-rose-600 text-sm'>
            {riskHint}
          </div>
        </Card>

        <Card
          title={(
            <span className='flex items-center gap-2 text-primary'>
              <LineChartOutlined className='text-emerald-600' />
              指标趋势
            </span>
          )}
          className='border-gray-200 bg-[#F0F1F9]'
        >
          {(trends.timestamps?.length ?? 0) > 0 && Object.keys(trends.indicators ?? {}).length > 0 ? (
            <ReactECharts option={trendChartOption} style={{ height: 320, width: '100%' }} />
          ) : (
            <Empty description='暂无趋势数据' />
          )}
        </Card>
      </div>

      <Card
        title={(
          <span className='flex items-center gap-2 text-primary'>
            <CameraOutlined className='text-fuchsia-600' />
            快照记录
            <Tag
              style={{
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                color: '#3b82f6',
                border: 'none'
              }}
              className="relative !ml-1 !px-3 !py-1 !text-xs !font-semibold !flex !items-center !gap-1"
            >
              {snapshotItems.length} 条
            </Tag>
          </span>
        )}
        className='border-gray-200 bg-[#F0F1F9]'
      >
        {snapshotItems.length === 0 ? (
          <Empty description='暂无快照记录' />
        ) : (
          <div className='space-y-3'>
            {snapshotItems.map((snapshot, index) => {
              const indicatorChanges = snapshot.indicator_changes ?? [];
              const rawType = snapshot.snapshot_type;
              const normalizedType = rawType === 'closing' || rawType === 'baseline' || rawType === 'periodic'
                ? rawType
                : undefined;
              const isLatest = index === 0;
              const isOldest = index === snapshotItems.length - 1;
              const inferredType = normalizedType === 'closing'
                ? 'closing'
                : normalizedType === 'baseline'
                  ? 'baseline'
                  : isOldest
                    ? 'baseline'
                    : (summary.status === 'completed' && isLatest ? 'closing' : 'periodic');
              const typeLabel = inferredType === 'closing'
                ? '结案快照'
                : inferredType === 'baseline'
                  ? '基线快照'
                  : '周期快照';
              const typeColor = inferredType === 'closing'
                ? 'success'
                : inferredType === 'baseline'
                  ? 'default'
                  : 'processing';
              return (
                <div key={snapshot.snapshot_id} className='rounded-lg border border-gray-200 bg-gray-50 p-3'>
                  <div className='flex items-start justify-between gap-3'>
                    <div>
                      <div className='flex items-center gap-2 text-sm font-medium text-primary'>
                        {dayjs(snapshot.snapshot_at).format('YYYY-MM-DD HH:mm')}
                        <Tag
                          style={{
                            backgroundColor: 'rgba(59, 130, 246, 0.2)',
                            color: '#3b82f6',
                            border: 'none'
                          }}
                          className="relative !m-0 !px-3 !py-1 !text-xs !font-semibold !flex !items-center !gap-1"
                        >
                          {typeLabel}
                        </Tag>
                      </div>
                    </div>
                    <div className='text-right'>
                      <div className='text-xs text-secondary'>评分</div>
                      <div className='text-xl font-semibold text-rose-600'>
                        {snapshot.health_score == null ? '-' : `${Number(snapshot.health_score).toFixed(0)}分`}
                      </div>
                    </div>
                  </div>

                  {indicatorChanges.length > 0 && (
                    <div className='mt-2 flex flex-wrap gap-2'>
                      {indicatorChanges.map((change) => (
                        <Tag
                          key={`${snapshot.snapshot_id}-${change.indicator_code}`}
                          style={{
                            backgroundColor: 'rgba(59, 130, 246, 0.2)',
                            color: '#3b82f6',
                            border: 'none'
                          }}
                          className="relative !m-0 !px-3 !py-1 !text-xs !font-semibold !flex !items-center !gap-1"
                        >
                          {change.name}: {Number(change.value).toFixed(2)}{change.unit || ''}
                        </Tag>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
