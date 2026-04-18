import { useEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useQueries, useQueryClient } from '@tanstack/react-query';
import {
  App,
  Button,
  Card,
  Col,
  Empty,
  Modal,
  Row,
  Spin,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  LineChartOutlined,
  RiseOutlined,
  StopOutlined,
  SyncOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { DiagnosisHistorySelect } from '@/components/diagnosis-history-select';
import { TrackingHeaderStatus } from '@/components/tracking-header-status';
import { formatListPersistentStatus } from '@/lib/tracking-persistent-status';
import { useAppStore } from '@/stores/app-store';
import {
  useCancelTracking,
  useCompleteTracking,
  useDiagnosisSelection,
  useStartReviewNow,
  useTakeSnapshot,
  useTrackingCompletionPoll,
  useTrackingList,
  reviewProgressLooksActive,
} from '@/lib/hooks';
import type { TrackingSummary, TrackingReviewProgress } from '@/lib/types';
import { trackingApi } from '@/lib/api';

interface SnapshotItem {
  snapshot_id: string;
  snapshot_at: string;
  health_score?: number;
  indicator_count: number;
}

interface SnapshotRow extends SnapshotItem {
  tracking_id: string;
}

const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  active: { color: 'processing', icon: <SyncOutlined spin />, text: '追踪中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  cancelled: { color: 'default', icon: <StopOutlined />, text: '已取消' },
  paused: { color: 'warning', icon: <ClockCircleOutlined />, text: '已暂停' },
  scheduled: { color: 'warning', icon: <ClockCircleOutlined />, text: '待自动复盘' },
};

export default function TrackingPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  const { diagnosisItems, selectedDiagnosisId, setSelectedDiagnosisId, listLoading } =
    useDiagnosisSelection(enterpriseId);

  const { data: trackingsData, isLoading, refetch } = useTrackingList(
    enterpriseId,
    undefined,
    0,
    100,
    selectedDiagnosisId,
  );

  const items = (trackingsData?.items ?? []) as TrackingSummary[];
  const itemsProgressKey = useMemo(
    () => items.map((t) => `${t.tracking_id}:${t.status}`).join('|'),
    [items],
  );
  const takeSnapshot = useTakeSnapshot();
  const completeTracking = useCompleteTracking();
  const cancelTracking = useCancelTracking();
  const startReviewNow = useStartReviewNow();
  const [isCompleting, setIsCompleting] = useState(false);
  const [completeProgress, setCompleteProgress] = useState<{ message: string; type: string }>({
    message: '',
    type: '',
  });
  const completingFlowRef = useRef(false);
  const completingTrackingIdRef = useRef('');
  const [completionPollId, setCompletionPollId] = useState<string | null>(null);

  useTrackingCompletionPoll(completionPollId, !!completionPollId && isCompleting, {
    onProgress: ({ message: line }) => {
      setCompleteProgress({ message: line, type: 'progress' });
    },
    onCompleted: () => {
      completingFlowRef.current = false;
      message.success('追踪已完成');
      void queryClient.invalidateQueries({ queryKey: ['tracking'] });
      setCompleteProgress({ message: '追踪已完成，复盘报告已生成', type: 'completed' });
      setCompletionPollId(null);
      setTimeout(() => {
        setIsCompleting(false);
        setCompleteProgress({ message: '', type: '' });
      }, 1500);
    },
    onError: (errMsg) => {
      completingFlowRef.current = false;
      message.error(errMsg);
      setCompleteProgress({ message: errMsg, type: 'error' });
      setCompletionPollId(null);
      void queryClient.invalidateQueries({ queryKey: ['tracking'] });
    },
  });

  /** 刷新/返回列表：若某条追踪的复盘仍在跑，恢复状态文案与轮询 */
  useEffect(() => {
    if (!enterpriseId || !selectedDiagnosisId || isLoading || !itemsProgressKey) return;
    if (isCompleting || completionPollId) return;

    const candidates = items.filter((t) => t.status === 'active' || t.status === 'scheduled');
    if (!candidates.length) return;

    let cancelled = false;
    (async () => {
      for (const t of candidates) {
        try {
          const data = (await trackingApi.getReviewProgress(t.tracking_id)) as TrackingReviewProgress;
          if (cancelled) return;
          if (!reviewProgressLooksActive(data)) continue;
          completingTrackingIdRef.current = t.tracking_id;
          completingFlowRef.current = true;
          flushSync(() => {
            setIsCompleting(true);
            setCompletionPollId(t.tracking_id);
            const msg = (data.message && String(data.message).trim()) || '处理中…';
            setCompleteProgress({ message: msg, type: 'progress' });
          });
          return;
        } catch {
          // 忽略
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    enterpriseId,
    selectedDiagnosisId,
    isLoading,
    itemsProgressKey,
    isCompleting,
    completionPollId,
  ]);

  const activeRow = useMemo(
    () => items.find((t: TrackingSummary) => t.status === 'active') ?? null,
    [items]
  );
  const scheduledRow = useMemo(
    () => items.find((t: TrackingSummary) => t.status === 'scheduled') ?? null,
    [items]
  );

  const snapshotQueries = useQueries({
    queries: items.map((t: TrackingSummary) => ({
      queryKey: ['tracking', 'snapshots', t.tracking_id],
      queryFn: () => trackingApi.getSnapshots(t.tracking_id),
      enabled: t.status !== 'scheduled',
      staleTime: 30_000,
    })),
  });

  const snapshotRows = useMemo<SnapshotRow[]>(() => {
    const rows: SnapshotRow[] = [];
    items.forEach((tracking: TrackingSummary, idx: number) => {
      const data = snapshotQueries[idx]?.data as { items?: SnapshotItem[] } | undefined;
      const snaps = data?.items ?? [];
      snaps.forEach((s) => {
        rows.push({
          ...s,
          tracking_id: tracking.tracking_id,
        });
      });
    });
    return rows.sort((a, b) => dayjs(b.snapshot_at).valueOf() - dayjs(a.snapshot_at).valueOf());
  }, [items, snapshotQueries]);

  const trendDelta = useMemo(() => {
    const valid = snapshotRows.filter((r) => r.health_score != null);
    if (valid.length < 2) return null;
    const latest = Number(valid[0].health_score);
    const earliest = Number(valid[valid.length - 1].health_score);
    return latest - earliest;
  }, [snapshotRows]);

  const stats = useMemo(() => {
    const scored = items.filter((t: TrackingSummary) => t.current_score != null);
    const avg = scored.length
      ? Math.round(
          scored.reduce(
            (sum: number, t: TrackingSummary) => sum + Number(t.current_score || 0),
            0
          ) / scored.length
        )
      : 0;
    return {
      totalTracking: items.length,
      active: items.filter((t: TrackingSummary) => t.status === 'active').length,
      completed: items.filter((t: TrackingSummary) => t.status === 'completed').length,
      snapshotTotal: snapshotRows.length,
      avgScore: avg,
    };
  }, [items, snapshotRows.length]);

  const trackingStatusText = useMemo(() => {
    if (activeRow) return '追踪中';
    if (scheduledRow) return '待复盘';
    if (stats.completed > 0) return '已完成';
    if (stats.totalTracking > 0) return '已停止';
    return '-';
  }, [activeRow, scheduledRow, stats.completed, stats.totalTracking]);

  const trackingStatusIcon = useMemo(() => {
    if (activeRow) return <SyncOutlined spin className="text-3xl text-amber-400" />;
    if (scheduledRow) return <ClockCircleOutlined className="text-3xl text-blue-400 animate-pulse" />;
    if (stats.completed > 0) return <CheckCircleOutlined className="text-3xl text-emerald-400 animate-pulse" />;
    if (stats.totalTracking > 0) return <StopOutlined className="text-3xl text-gray-400 animate-pulse" />;
    return <ClockCircleOutlined className="text-3xl text-gray-500" />;
  }, [activeRow, scheduledRow, stats.completed, stats.totalTracking]);

  const handleSnapshot = async () => {
    if (!enterpriseId || !selectedDiagnosisId) {
      message.warning('请先选择诊断');
      return;
    }
    const targetId = activeRow?.tracking_id || scheduledRow?.tracking_id || selectedDiagnosisId;
    try {
      await takeSnapshot.mutateAsync({ trackingId: targetId, enterpriseId });
      message.success('快照已采集');
      refetch();
    } catch {
      // 失败提示已由 api 响应拦截器展示
    }
  };

  const handleReviewNow = () => {
    if (!selectedDiagnosisId) return;
    if (scheduledRow) {
      Modal.confirm({
        title: '立即复盘',
        content: '将跳过等待期并执行复盘，是否继续？',
        okText: '开始',
        cancelText: '取消',
        onOk: async () => {
          await startReviewNow.mutateAsync(scheduledRow.tracking_id);
          message.success('已触发立即复盘');
          refetch();
        },
      });
      return;
    }
    if (activeRow) {
      Modal.confirm({
        title: '立即复盘',
        content: '将结束追踪并生成复盘报告，是否继续？',
        okText: '确认',
        cancelText: '取消',
        onOk: async () => {
          completingTrackingIdRef.current = activeRow.tracking_id;
          completingFlowRef.current = true;
          flushSync(() => {
            setIsCompleting(true);
            setCompletionPollId(activeRow.tracking_id);
            setCompleteProgress({ message: '正在提交完成追踪…', type: 'progress' });
          });
          try {
            await completeTracking.mutateAsync(activeRow.tracking_id);
          } catch {
            completingFlowRef.current = false;
            setIsCompleting(false);
            setCompletionPollId(null);
            setCompleteProgress({ message: '', type: '' });
            void queryClient.invalidateQueries({ queryKey: ['tracking'] });
          }
        },
      });
      return;
    }
    Modal.confirm({
      title: '立即复盘',
      content: '将使用当前诊断会话尝试触发复盘，是否继续？',
      onOk: async () => {
        await startReviewNow.mutateAsync(selectedDiagnosisId);
        message.success('已触发立即复盘');
        refetch();
      },
    });
  };

  const handleStop = () => {
    const tid = activeRow?.tracking_id ?? scheduledRow?.tracking_id;
    if (!tid) return;
    const pendingOnly = !!scheduledRow && !activeRow;
    Modal.confirm({
      title: '确认停止追踪',
      content: pendingOnly
        ? '将取消待自动复盘调度，是否确认？'
        : '停止后将无法继续采集数据，是否确认？',
      okText: '确认停止',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        await cancelTracking.mutateAsync(tid);
        message.success(pendingOnly ? '已取消待复盘调度' : '追踪已停止');
        refetch();
      },
    });
  };

  const columns: ColumnsType<SnapshotRow> = [
    {
      title: '追踪时间',
      dataIndex: 'snapshot_at',
      key: 'snapshot_at',
      width: 180,
      render: (v: string) => <span className="text-gray-300">{dayjs(v).format('YYYY-MM-DD HH:mm')}</span>,
    },
    {
      title: '得分',
      dataIndex: 'health_score',
      key: 'health_score',
      width: 120,
      render: (v?: number) => (v == null ? '-' : Number(v).toFixed(1)),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, row) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate('/tracking')}
        >
          详情
        </Button>
      ),
    },
  ];

  if (!enterpriseId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Empty description="请先选择企业" />
      </div>
    );
  }

  const handleCancelCompleting = () => {
    completingFlowRef.current = false;
    setIsCompleting(false);
    setCompletionPollId(null);
    setCompleteProgress({ message: '', type: '' });
  };

  const handleRetryComplete = () => {
    const tid = completingTrackingIdRef.current;
    if (!tid) return;
    completingFlowRef.current = true;
    flushSync(() => {
      setIsCompleting(true);
      setCompletionPollId(tid);
      setCompleteProgress({ message: '正在重新完成追踪…', type: 'progress' });
    });
    void completeTracking.mutateAsync(tid).catch(() => {
      completingFlowRef.current = false;
      setIsCompleting(false);
      setCompletionPollId(null);
      setCompleteProgress({ message: '', type: '' });
      void queryClient.invalidateQueries({ queryKey: ['tracking'] });
    });
  };

  const completeRunning = isCompleting && completeProgress.type === 'progress';

  const listPersistentLine = formatListPersistentStatus({
    selectedDiagnosisId,
    isLoading,
    trackingStatusText,
    totalTracking: stats.totalTracking,
    snapshotTotal: stats.snapshotTotal,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between lg:gap-4">
          <h1 className="m-0 text-3xl font-bold leading-tight tracking-tight text-[#303133] flex min-w-0 flex-1 items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-lg shadow-lg shadow-purple-500/20 text-white shrink-0">
              <LineChartOutlined />
            </span>
            效果追踪
          </h1>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap sm:justify-end lg:ml-auto shrink-0">
            {diagnosisItems.length > 0 && (
              <DiagnosisHistorySelect
                className="max-w-full shrink-0 self-center"
                diagnosisItems={diagnosisItems}
                value={selectedDiagnosisId}
                onChange={setSelectedDiagnosisId}
                loading={listLoading}
                disabled={completeRunning}
              />
            )}
            <div className="flex flex-wrap gap-2 shrink-0 items-center">
              <Tooltip title={selectedDiagnosisId ? '采集一次快照' : '请先选择历史诊断'}>
                <span>
                  <Button
                    icon={<CameraOutlined />}
                    disabled={!selectedDiagnosisId || completeRunning}
                    loading={takeSnapshot.isPending}
                    onClick={handleSnapshot}
                  >
                    快照
                  </Button>
                </span>
              </Tooltip>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                disabled={!selectedDiagnosisId || completeRunning}
                loading={startReviewNow.isPending || completeTracking.isPending}
                onClick={handleReviewNow}
              >
                立即复盘
              </Button>
              {(activeRow || scheduledRow) && (
                <Button
                  danger
                  icon={<StopOutlined />}
                  disabled={completeRunning}
                  loading={cancelTracking.isPending}
                  onClick={handleStop}
                >
                  停止追踪
                </Button>
              )}
            </div>
          </div>
        </div>
        <TrackingHeaderStatus
          persistent={listPersistentLine}
          transient={
            isCompleting ? (
              <div>
                <p
                  className={`text-sm ${
                    completeProgress.type === 'error' ? 'text-red-600' : 'text-[#606266]'
                  }`}
                >
                  {completeProgress.type === 'completed'
                    ? completeProgress.message || '复盘已完成'
                    : completeProgress.message ||
                      (completeProgress.type === 'progress' ? '正在处理中，请稍候…' : '')}
                </p>
                {completeProgress.type === 'completed' && (
                  <Button
                    type="link"
                    size="small"
                    className="mt-1 h-auto p-0"
                    onClick={() => {
                      setIsCompleting(false);
                      void queryClient.invalidateQueries({ queryKey: ['tracking'] });
                      const tid = completingTrackingIdRef.current;
                      if (tid) navigate(`/tracking/${encodeURIComponent(tid)}/report`);
                      else navigate('/tracking');
                      setCompleteProgress({ message: '', type: '' });
                    }}
                  >
                    查看复盘报告
                  </Button>
                )}
                {completeProgress.type === 'error' && (
                  <div className="mt-1 flex flex-wrap gap-x-3">
                    <Button type="link" size="small" className="h-auto p-0" onClick={handleCancelCompleting}>
                      关闭提示
                    </Button>
                    <Button
                      type="link"
                      size="small"
                      className="h-auto p-0"
                      loading={completeTracking.isPending}
                      onClick={handleRetryComplete}
                    >
                      重试
                    </Button>
                  </div>
                )}
              </div>
            ) : undefined
          }
        />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Spin size="large" />
        </div>
      ) : !selectedDiagnosisId ? (
        <Empty description="请先选择诊断" />
      ) : (
        <>
          <Row gutter={16}>
            <Col span={8}>
              <Card className="text-center"><div className="text-3xl font-bold text-blue-400">{stats.totalTracking}</div><div className="text-gray-400 text-sm mt-1">追踪总数</div></Card>
            </Col>
            <Col span={8}>
              <Card className="text-center">
                <div className="flex flex-col items-center gap-2">
                  {trackingStatusIcon}
                  <div className="text-xl font-bold text-amber-300">{trackingStatusText}</div>
                </div>
                <div className="text-gray-400 text-sm mt-1">追踪状态</div>
              </Card>
            </Col>
            <Col span={8}>
              <Card className="text-center"><div className="text-3xl font-bold text-purple-400">{stats.avgScore}</div><div className="text-gray-400 text-sm mt-1">评价评分</div></Card>
            </Col>
          </Row>

          <Card title="追踪记录">
            <Table
              rowKey={(r) => `${r.tracking_id}-${r.snapshot_id}`}
              columns={columns}
              dataSource={snapshotRows}
              loading={snapshotQueries.some((q) => q.isLoading)}
              pagination={{ pageSize: 10, showSizeChanger: false }}
              locale={{ emptyText: <Empty description="暂无采集记录" /> }}
            />
          </Card>
        </>
      )}
    </div>
  );
}
