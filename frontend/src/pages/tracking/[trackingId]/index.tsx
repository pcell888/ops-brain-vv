import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Tag, Button, Empty, Spin, Progress, Row, Col,
  Descriptions, App, Statistic, Modal, Timeline,
} from 'antd';
import {
  ArrowLeftOutlined,
  LineChartOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  EyeOutlined,
  FileTextOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  StopOutlined,
  DashboardOutlined,
  HistoryOutlined,
  TrophyOutlined,
  ExperimentOutlined,
  FilterOutlined,
  TeamOutlined,
  CrownOutlined,
  AreaChartOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import {
  useTrackingSummary,
  useMetricTrends,
  useTakeSnapshot,
  useCompleteTracking,
  useCancelTracking,
  useTrackingSnapshots,
  useAnalyzeEffect,
  useDimensionConfig,
  useDashboardFunnel,
  useDashboardTeams,
  useDashboardRanking,
  useSnapshotDashboard,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import dayjs from 'dayjs';
import type { MetricTrend } from '@/lib/types';
import { ConversionFunnel, TeamComparison, SalesRanking } from '@/components/tracking/dashboard-widgets';

// 状态配置
const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  active: { color: 'processing', icon: <SyncOutlined spin />, text: '追踪中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  cancelled: { color: 'default', icon: <StopOutlined />, text: '已取消' },
  paused: { color: 'warning', icon: <ClockCircleOutlined />, text: '已暂停' },
};

// 快照类型
interface Snapshot {
  id: string;
  type: string;
  snapshot_at?: string;
  created_at?: string;
  health_score?: number;
  metric_summary?: Array<{ name: string; value: number; unit: string }>;
}

// 分析数据类型
interface AnalysisData {
  overall_score?: number;
  goal_completion_rate?: number;
  improved_metrics_count?: number;
  effect_status?: string;
  metric_improvements?: Array<{ name: string; before: number; after: number; improvement: number }>;
  suggestions?: string[];
  risks?: string[];
}

export default function TrackingDetailPage() {
  const { message } = App.useApp();
  const params = useParams();
  const navigate = useNavigate();
  const trackingId = params.trackingId as string;
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  // 数据查询
  const { data: trackingDetail, isLoading, refetch: refetchSummary } = useTrackingSummary(trackingId);
  const { data: trendsData } = useMetricTrends(trackingId);
  const { data: snapshotsData } = useTrackingSnapshots(trackingId);
  const { data: analysisData, dataUpdatedAt: analysisUpdatedAt } = useAnalyzeEffect(trackingId) as { data: AnalysisData | undefined; dataUpdatedAt: number };
  
  // 看板图表数据
  const { data: funnelData } = useDashboardFunnel(trackingId);
  const { data: teamsData } = useDashboardTeams(trackingId);
  const { data: rankingData } = useDashboardRanking(trackingId, 10);
  
  // 历史看板数据
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [historyDashboardModalOpen, setHistoryDashboardModalOpen] = useState(false);
  const { data: historyDashboardData } = useSnapshotDashboard(selectedSnapshotId);
  
  // 帮助弹窗
  const [helpModalOpen, setHelpModalOpen] = useState(false);
  
  // 获取指标显示名称映射
  const { getMetricDisplayName } = useDimensionConfig(enterpriseId);

  // 将文本中的指标名替换为中文显示名
  const translateMetricNames = (text: string): string => {
    // 匹配「指标名」格式，替换为中文显示名
    return text.replace(/「([^」]+)」/g, (match, metricName) => {
      const displayName = getMetricDisplayName(metricName);
      return `「${displayName}」`;
    });
  };

  // 分析数据更新后，重新拉取 summary 以同步 current_score
  const prevAnalysisUpdatedAt = useRef(analysisUpdatedAt);
  useEffect(() => {
    if (analysisUpdatedAt && analysisUpdatedAt !== prevAnalysisUpdatedAt.current) {
      prevAnalysisUpdatedAt.current = analysisUpdatedAt;
      refetchSummary();
    }
  }, [analysisUpdatedAt, refetchSummary]);

  // 操作 hooks
  const takeSnapshot = useTakeSnapshot();
  const completeTracking = useCompleteTracking();
  const cancelTracking = useCancelTracking();

  const handleTakeSnapshot = async () => {
    try {
      await takeSnapshot.mutateAsync(trackingId);
      message.success('快照已采集');
    } catch {
      message.error('快照采集失败');
    }
  };

  const handleCompleteTracking = async () => {
    try {
      await completeTracking.mutateAsync(trackingId);
      message.success('追踪已完成，复盘报告已生成');
    } catch {
      message.error('完成追踪失败');
    }
  };

  const handleCancelTracking = () => {
    Modal.confirm({
      title: '确认停止追踪',
      content: '停止后将无法继续采集数据，是否确认？',
      okText: '确认停止',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await cancelTracking.mutateAsync(trackingId);
          message.success('追踪已停止');
        } catch {
          message.error('停止追踪失败');
        }
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin size="large" />
      </div>
    );
  }

  if (!trackingDetail) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty description="追踪记录不存在" />
        </div>
      </div>
    );
  }

  const isActive = trackingDetail.status === 'active';
  const isCompleted = trackingDetail.status === 'completed';
  const statusCfg = statusConfig[trackingDetail.status] || statusConfig.active;

  // 评分颜色
  const scoreColor = (score: number | null | undefined) => {
    if (!score) return 'text-gray-400';
    return score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-rose-400';
  };

  return (
    <div className="space-y-6">
      {/* 页面头部 */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-lg shadow-lg shadow-purple-500/20">
                <LineChartOutlined />
              </span>
              效果追踪详情
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              {trackingDetail.solution_name}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          {isActive && (
            <>
              <Button
                icon={<CameraOutlined />}
                onClick={handleTakeSnapshot}
                loading={takeSnapshot.isPending}
              >
                采集快照
              </Button>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={handleCompleteTracking}
                loading={completeTracking.isPending}
              >
                完成追踪
              </Button>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={handleCancelTracking}
                loading={cancelTracking.isPending}
              >
                停止
              </Button>
            </>
          )}
          {isCompleted && (
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              onClick={() => navigate(`/tracking/${trackingId}/report`)}
            >
              查看复盘报告
            </Button>
          )}
          <Button
            type="link"
            icon={<QuestionCircleOutlined />}
            onClick={() => setHelpModalOpen(true)}
            className="text-gray-400 hover:text-white"
          >
            帮助
          </Button>
        </div>
      </div>

      {/* 状态概览卡片 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card className="!bg-gray-800/50 border-gray-700/50">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
                <DashboardOutlined className="text-2xl text-blue-400" />
              </div>
              <div>
                <div className="text-gray-400 text-xs">追踪状态</div>
                <Tag icon={statusCfg.icon} color={statusCfg.color} className="mt-1 text-sm">
                  {statusCfg.text}
                </Tag>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="!bg-gray-800/50 border-gray-700/50">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-green-500/20 flex items-center justify-center">
                <TrophyOutlined className="text-2xl text-emerald-400" />
              </div>
              <div>
                <div className="text-gray-400 text-xs">当前评分</div>
                <div className={`text-2xl font-bold mt-0.5 ${scoreColor(trackingDetail.current_score)}`}>
                  {trackingDetail.current_score?.toFixed(0) || '-'}
                  <span className="text-xs text-gray-500 ml-1">分</span>
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="!bg-gray-800/50 border-gray-700/50">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
                <CameraOutlined className="text-2xl text-amber-400" />
              </div>
              <div>
                <div className="text-gray-400 text-xs">快照数量</div>
                <div className="text-2xl font-bold mt-0.5 text-amber-400">
                  {trackingDetail.snapshot_count}
                  <span className="text-xs text-gray-500 ml-1">个</span>
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="!bg-gray-800/50 border-gray-700/50">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
                <HistoryOutlined className="text-2xl text-purple-400" />
              </div>
              <div>
                <div className="text-gray-400 text-xs">追踪时长</div>
                <div className="text-2xl font-bold mt-0.5 text-purple-400">
                  {Math.max(1, dayjs().diff(dayjs(trackingDetail.started_at), 'day'))}
                  <span className="text-xs text-gray-500 ml-1">天</span>
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 基本信息 */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <EyeOutlined className="text-blue-400" />
            <span>基本信息</span>
          </div>
        }
      >
        <Descriptions bordered column={3} size="small">
          <Descriptions.Item label="方案名称" span={3}>
            <span className="font-medium text-white">{trackingDetail.solution_name}</span>
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {dayjs(trackingDetail.started_at).format('YYYY-MM-DD HH:mm')}
          </Descriptions.Item>
          <Descriptions.Item label="最近快照">
            {trackingDetail.last_snapshot_at
              ? dayjs(trackingDetail.last_snapshot_at).format('YYYY-MM-DD HH:mm')
              : '-'}
          </Descriptions.Item>
          {isCompleted && (
            <Descriptions.Item label="完成时间">
              {trackingDetail.completed_at
                ? dayjs(trackingDetail.completed_at).format('YYYY-MM-DD HH:mm')
                : '-'}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* 效果分析 + 指标趋势 */}
      <Row gutter={16}>
        {/* 效果分析 */}
        <Col span={12}>
          <Card
            title={
              <div className="flex items-center gap-2">
                <ExperimentOutlined className="text-cyan-400" />
                <span>效果分析</span>
              </div>
            }
            className="h-full"
          >
            {analysisData ? (
              <div className="space-y-4">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="整体效果评分"
                      value={analysisData.overall_score !== null && analysisData.overall_score !== undefined ? analysisData.overall_score : '-'}
                      suffix="分"
                      valueStyle={{
                        color: (analysisData.overall_score ?? 0) >= 80 ? '#10b981' : '#f59e0b',
                        fontSize: 28,
                      }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="目标达成率"
                      value={analysisData.goal_completion_rate || 0}
                      suffix="%"
                      valueStyle={{ fontSize: 24, color: '#fff' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="改善指标数"
                      value={analysisData.improved_metrics_count || 0}
                      suffix="个"
                      valueStyle={{ fontSize: 24, color: '#10b981' }}
                    />
                  </Col>
                </Row>

                {/* 指标改善详情 */}
                {analysisData.metric_improvements && analysisData.metric_improvements.length > 0 && (
                  <div className="space-y-2 mt-4">
                    <div className="text-xs text-gray-400 font-medium mb-2">指标改善详情</div>
                    {analysisData.metric_improvements.map((metric, index) => (
                      <div
                        key={index}
                        className="p-3 bg-gray-800/50 rounded-lg flex items-center justify-between"
                      >
                        <div className="flex-1">
                          <div className="text-white font-medium text-sm">{getMetricDisplayName(metric.name)}</div>
                          <div className="text-xs text-gray-500 mt-1">
                            {metric.before.toFixed(1)} → {metric.after.toFixed(1)}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Progress
                            percent={Math.min(100, Math.abs(metric.improvement))}
                            size="small"
                            strokeColor={metric.improvement >= 0 ? '#10b981' : '#ef4444'}
                            showInfo={false}
                            className="w-20"
                          />
                          <span className={`font-bold text-sm ${
                            metric.improvement >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}>
                            {metric.improvement >= 0 ? '+' : ''}{metric.improvement.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 建议 */}
                {analysisData.suggestions && analysisData.suggestions.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs text-gray-400 font-medium mb-2">分析建议</div>
                    <ul className="space-y-1.5">
                      {analysisData.suggestions.map((s, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                          <span className="text-cyan-400 mt-0.5">💡</span>
                          {translateMetricNames(s)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 风险提示 */}
                {analysisData.risks && analysisData.risks.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs text-gray-400 font-medium mb-2">风险提示</div>
                    <ul className="space-y-1.5">
                      {analysisData.risks.map((r, i) => (
                        <li key={i} className="flex items-start gap-2 p-2 bg-rose-500/10 rounded-lg border border-rose-500/20 text-sm text-gray-300">
                          <span className="text-rose-400 mt-0.5">⚠️</span>
                          {translateMetricNames(r)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <Empty description="暂无分析数据，请先采集快照" className="py-8" />
            )}
          </Card>
        </Col>

        {/* 指标趋势 */}
        <Col span={12}>
          <Card
            title={
              <div className="flex items-center gap-2">
                <BarChartOutlined className="text-green-400" />
                <span>指标趋势</span>
              </div>
            }
            className="h-full"
          >
            {trendsData?.trends && trendsData.trends.length > 0 ? (
              <div className="space-y-3">
                {trendsData.trends.map((trend: MetricTrend) => (
                  <div
                    key={trend.metric_name}
                    className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30"
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-white font-medium">{getMetricDisplayName(trend.metric_name)}</span>
                      <span className={`flex items-center gap-1 font-bold ${
                        trend.improvement >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}>
                        {trend.improvement >= 0 ? <RiseOutlined /> : <FallOutlined />}
                        {Math.abs(trend.improvement).toFixed(1)}%
                      </span>
                    </div>
                    {/* 简化趋势图：显示数值点 */}
                    {trend.values && trend.values.length > 0 && (
                      <div className="mt-2">
                        <div className="flex items-end gap-1 h-10">
                          {trend.values.map((v, i) => {
                            const allValues = trend.values.map(x => x.value);
                            const max = Math.max(...allValues);
                            const min = Math.min(...allValues);
                            const range = max - min || 1;
                            const height = ((v.value - min) / range * 70) + 30;
                            return (
                              <div
                                key={i}
                                className="flex-1 rounded-t transition-all"
                                style={{
                                  height: `${height}%`,
                                  background: trend.improvement >= 0
                                    ? `rgba(16, 185, 129, ${0.3 + (i / trend.values.length) * 0.7})`
                                    : `rgba(239, 68, 68, ${0.3 + (i / trend.values.length) * 0.7})`,
                                }}
                                title={`${dayjs(v.date).format('MM-DD')}: ${v.value.toFixed(1)}`}
                              />
                            );
                          })}
                        </div>
                        <div className="flex justify-between mt-1">
                          <span className="text-xs text-gray-500">
                            {dayjs(trend.values[0].date).format('MM-DD')}
                          </span>
                          <span className="text-xs text-gray-400">
                            最新: <span className="text-white">{trend.values[trend.values.length - 1]?.value.toFixed(1)}</span>
                          </span>
                          <span className="text-xs text-gray-500">
                            {dayjs(trend.values[trend.values.length - 1].date).format('MM-DD')}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="暂无趋势数据" className="py-8" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 看板图表区域 */}
      <Row gutter={16}>
        {/* 转化漏斗 */}
        <Col span={8}>
          <Card
            title={
              <div className="flex items-center gap-2">
                <FilterOutlined className="text-blue-400" />
                <span>线索转化漏斗</span>
              </div>
            }
            className="h-full"
          >
            <ConversionFunnel 
              data={funnelData?.funnel || []} 
              showIcon={false}
            />
          </Card>
        </Col>

        {/* 团队对比 */}
        <Col span={8}>
          <Card
            title={
              <div className="flex items-center gap-2">
                <TeamOutlined className="text-green-400" />
                <span>团队转化率对比</span>
              </div>
            }
            className="h-full"
          >
            <TeamComparison 
              data={teamsData?.teams || []} 
              showIcon={false}
            />
          </Card>
        </Col>

        {/* 销售排名 */}
        <Col span={8}>
          <Card
            title={
              <div className="flex items-center gap-2">
                <CrownOutlined className="text-yellow-400" />
                <span>销售排行榜</span>
                {rankingData?.ranking && (
                  <Tag className="ml-1 text-xs">{rankingData.ranking.length}人</Tag>
                )}
              </div>
            }
            className="h-full"
          >
            <SalesRanking 
              data={rankingData?.ranking || []} 
              showIcon={false}
              showCount={false}
            />
          </Card>
        </Col>
      </Row>

      {/* 快照记录 */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <HistoryOutlined className="text-amber-400" />
            <span>快照记录</span>
            {snapshotsData?.snapshots && (
              <Tag className="ml-1">{snapshotsData.snapshots.length}条</Tag>
            )}
          </div>
        }
        extra={
          isActive && (
            <Button
              type="primary"
              size="small"
              icon={<CameraOutlined />}
              onClick={handleTakeSnapshot}
              loading={takeSnapshot.isPending}
            >
              采集新快照
            </Button>
          )
        }
      >
        {snapshotsData?.snapshots && snapshotsData.snapshots.length > 0 ? (
          <Timeline
            items={snapshotsData.snapshots.map((snapshot: Snapshot) => ({
              color: snapshot.type === 'baseline' ? 'purple' : snapshot.type === 'final' ? 'green' : 'blue',
              children: (
                <div className="p-3 bg-gray-800/30 rounded-lg border border-gray-700/30 -mt-1">
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium text-sm">
                        {dayjs(snapshot.snapshot_at || snapshot.created_at).format('YYYY-MM-DD HH:mm')}
                      </span>
                      <Tag
                        color={
                          snapshot.type === 'baseline' ? 'purple' :
                          snapshot.type === 'final' ? 'green' : 'blue'
                        }
                      >
                        {snapshot.type === 'baseline' ? '基线快照' :
                         snapshot.type === 'final' ? '结案快照' : '周期快照'}
                      </Tag>
                    </div>
                    {snapshot.health_score !== undefined && (
                      <span className={`font-bold text-lg ${
                        snapshot.health_score >= 60 ? 'text-emerald-400' :
                        snapshot.health_score >= 40 ? 'text-amber-400' : 'text-rose-400'
                      }`}>
                        {snapshot.health_score.toFixed(0)}分
                      </span>
                    )}
                  </div>
                  {snapshot.metric_summary && snapshot.metric_summary.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {snapshot.metric_summary.map((m, idx) => (
                        <span
                          key={idx}
                          className="text-xs text-gray-400 bg-gray-700/50 px-2.5 py-1 rounded-full"
                        >
                          {getMetricDisplayName(m.name)}: <span className="text-white font-medium">{m.value?.toFixed(1)}{m.unit}</span>
                        </span>
                      ))}
                    </div>
                  )}
                  {/* 查看历史看板数据按钮 */}
                  <div className="mt-2 flex justify-end">
                    <Button
                      type="link"
                      size="small"
                      icon={<AreaChartOutlined />}
                      onClick={() => {
                        setSelectedSnapshotId(snapshot.id);
                        setHistoryDashboardModalOpen(true);
                      }}
                    >
                      查看当时看板
                    </Button>
                  </div>
                </div>
              ),
            }))}
          />
        ) : (
          <Empty description="暂无快照记录" className="py-8" />
        )}
      </Card>

      {/* 历史看板数据弹窗 */}
      <Modal
        title="历史看板数据"
        open={historyDashboardModalOpen}
        onCancel={() => {
          setHistoryDashboardModalOpen(false);
          setSelectedSnapshotId(null);
        }}
        footer={null}
        width={1200}
      >
        {historyDashboardData?.dashboard_data ? (
          <div className="py-4">
            {/* 快照信息 */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 mb-4">
              <div className="flex items-center justify-between">
                <span className="text-blue-300">
                  快照类型: <strong>{historyDashboardData.snapshot_type === 'baseline' ? '基线快照' : historyDashboardData.snapshot_type === 'final' ? '结案快照' : '周期快照'}</strong>
                </span>
                <span className="text-gray-400 text-sm">
                  {dayjs(historyDashboardData.created_at).format('YYYY-MM-DD HH:mm')}
                </span>
              </div>
            </div>

            {/* 三列布局 - 复用父页面组件，保持顶部对齐 */}
            <Row gutter={16} align="top">
              <Col span={8}>
                <ConversionFunnel 
                  data={historyDashboardData.dashboard_data.funnel || []} 
                  title="转化漏斗"
                  compact
                />
              </Col>
              <Col span={8}>
                <TeamComparison 
                  data={historyDashboardData.dashboard_data.teams || []} 
                  title="团队对比"
                  compact
                  syncHeight
                />
              </Col>
              <Col span={8}>
                <SalesRanking 
                  data={historyDashboardData.dashboard_data.ranking || []} 
                  title="销售排名"
                  compact
                  syncHeight
                />
              </Col>
            </Row>
          </div>
        ) : (
          <Empty description="该快照没有保存看板数据" className="py-8" />
        )}
      </Modal>

      {/* 帮助弹窗 - 什么时候完成追踪 */}
      <Modal
        title="什么时候完成追踪比较合适？"
        open={helpModalOpen}
        onCancel={() => setHelpModalOpen(false)}
        footer={null}
        width={700}
      >
        <div className="space-y-6 py-4">
          {/* 按追踪时长 */}
          <div>
            <h4 className="text-base font-medium text-white mb-3 flex items-center gap-2">
              <ClockCircleOutlined className="text-blue-400" />
              按追踪时长
            </h4>
            <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between py-2 border-b border-gray-700/50">
                <span className="text-gray-300">快速实验（A/B测试）</span>
                <Tag color="blue">2-4周</Tag>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-700/50">
                <span className="text-gray-300">标准优化（线索转化等）</span>
                <Tag color="green">4-6周</Tag>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-gray-300">长期战略（流程改造等）</span>
                <Tag color="purple">8-12周</Tag>
              </div>
            </div>
          </div>

          {/* 按数据指标 */}
          <div>
            <h4 className="text-base font-medium text-white mb-3 flex items-center gap-2">
              <BarChartOutlined className="text-green-400" />
              按数据指标
            </h4>
            <div className="bg-gray-800/50 rounded-lg p-3 space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-blue-400 text-xs font-bold">1</span>
                </div>
                <div>
                  <div className="text-white font-medium">采集足够快照</div>
                  <div className="text-gray-400 text-sm">至少 2-3 个周期快照（基线→周期1→周期2→结案）</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-green-400 text-xs font-bold">2</span>
                </div>
                <div>
                  <div className="text-white font-medium">效果趋于稳定</div>
                  <div className="text-gray-400 text-sm">连续 2 个周期指标变化 &lt; 10%</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-purple-400 text-xs font-bold">3</span>
                </div>
                <div>
                  <div className="text-white font-medium">达成目标或验证无效</div>
                  <div className="text-gray-400 text-sm">达成预期目标，或确认方案无效（可考虑停止）</div>
                </div>
              </div>
            </div>
          </div>

          {/* 注意事项 */}
          <div>
            <h4 className="text-base font-medium text-white mb-3 flex items-center gap-2">
              <ExperimentOutlined className="text-amber-400" />
              注意事项
            </h4>
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2 text-amber-200 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                <span>不要太早完成：少于 2 周或 2 个快照，数据不足</span>
              </div>
              <div className="flex items-center gap-2 text-amber-200 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                <span>也不要无限期：超过 3 个月效果已稳定，继续追踪意义不大</span>
              </div>
              <div className="flex items-center gap-2 text-amber-200 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                <span>确保覆盖完整业务周期，避开节假日等异常时段</span>
              </div>
            </div>
          </div>

          {/* 建议流程 */}
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
            <h4 className="text-sm font-medium text-blue-300 mb-2">建议流程</h4>
            <div className="text-sm text-gray-300">
              启动追踪 → 第 7 天（第 1 次快照） → 第 14 天（第 2 次快照） → 第 21 天（第 3 次快照） → <strong className="text-white">完成追踪</strong>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}

