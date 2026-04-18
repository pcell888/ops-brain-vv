import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Button, Empty, Spin, Row, Col, App } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  BulbOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import {
  useDiagnosisSelection,
  useDiagnosisReport,
  useSolutionList,
  adoptProgressLooksActive,
} from '@/lib/hooks';
import { solutionApi, type AdoptProgressResponse } from '@/lib/api';
import { DiagnosisHistorySelect } from '@/components/diagnosis-history-select';
import { TrackingHeaderStatus } from '@/components/tracking-header-status';
import { useAppStore } from '@/stores/app-store';
import { formatSolutionsListPersistent } from '@/lib/solutions-header-status';
import type { SolutionSummary, Anomaly } from '@/lib/types';

export default function SolutionsPageWrapper() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-[60vh]"><Spin size="large" /></div>}>
      <SolutionsPage />
    </Suspense>
  );
}

function SolutionsPage() {
  const { message } = App.useApp();
  const { currentEnterprise } = useAppStore();
  const navigate = useNavigate();
  const enterpriseId = currentEnterprise?.id || null;

  const { diagnosisItems, selectedDiagnosisId, setSelectedDiagnosisId, listLoading } =
    useDiagnosisSelection(enterpriseId);

  const selectedItem = useMemo(
    () => diagnosisItems.find((i) => i.diagnosis_id === selectedDiagnosisId),
    [diagnosisItems, selectedDiagnosisId],
  );
  const isCompleted = selectedItem?.status === 'completed';

  const { data: diagnosisReport, isLoading: reportLoading } = useDiagnosisReport(
    isCompleted && selectedDiagnosisId ? selectedDiagnosisId : null,
  );
  const { data: solutionData, isLoading: solutionsLoading } = useSolutionList(
    isCompleted && selectedDiagnosisId ? selectedDiagnosisId : null,
  );

  const isLoading = listLoading || (isCompleted && (reportLoading || solutionsLoading));

  const solutions = (solutionData?.solutions ?? []) as SolutionSummary[];
  const solutionsProbeKey = useMemo(
    () => solutions.map((s) => `${s.solution_id}:${s.status ?? ''}`).join('|'),
    [solutions],
  );

  const [adoptPollPlanId, setAdoptPollPlanId] = useState<string | null>(null);
  const [adoptUiActive, setAdoptUiActive] = useState(false);
  const [adoptLine, setAdoptLine] = useState<{ message: string; type: string }>({ message: '', type: '' });
  const adoptExecutedPlanIdRef = useRef<string | null>(null);

  const adoptMonitorPause =
    isLoading || !selectedDiagnosisId || !isCompleted || Boolean(solutionData?.generating);

  /** 从详情页采纳后返回列表：若执行仍在进行，展示状态并轮询 */
  useEffect(() => {
    if (adoptMonitorPause || !selectedDiagnosisId || !solutionsProbeKey) return;
    if (adoptUiActive || adoptPollPlanId) return;

    let cancelled = false;
    (async () => {
      const ordered = [...solutions]
        .filter((s) => s.status !== 'rejected')
        .sort((a, b) => (b.status === 'adopted' ? 1 : 0) - (a.status === 'adopted' ? 1 : 0));
      for (const s of ordered) {
        try {
          const data = await solutionApi.getAdoptProgress(s.solution_id);
          if (cancelled) return;
          if (!adoptProgressLooksActive(data)) continue;
          adoptExecutedPlanIdRef.current = s.solution_id;
          setAdoptPollPlanId(s.solution_id);
          setAdoptUiActive(true);
          const line = (data.message || '').trim() || '正在执行采纳方案…';
          setAdoptLine({ message: line, type: 'progress' });
          return;
        } catch {
          // 无对应线程或已结束
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [adoptMonitorPause, selectedDiagnosisId, solutionsProbeKey, adoptUiActive, adoptPollPlanId]);

  useEffect(() => {
    if (!adoptUiActive || !adoptPollPlanId) return;

    const POLL_MS = 1200;
    let intervalId: ReturnType<typeof setInterval> | undefined;
    let cancelled = false;
    let completionTimer: ReturnType<typeof setTimeout> | undefined;

    const stopInterval = () => {
      if (intervalId !== undefined) {
        clearInterval(intervalId);
        intervalId = undefined;
      }
    };

    const applyPayload = (data: AdoptProgressResponse) => {
      if (cancelled) return;
      const status = (data.status || '').toLowerCase();
      const isRunning = Boolean(data.is_running);
      const line = (data.message || '').trim() || '请稍候…';
      if (status === 'failed' || data.event_type === 'error') {
        stopInterval();
        setAdoptPollPlanId(null);
        setAdoptLine({ message: line, type: 'error' });
        message.error(line);
        return;
      }

      if (status === 'completed' && !isRunning) {
        stopInterval();
        setAdoptLine({ message: line, type: 'completed' });
        completionTimer = setTimeout(() => {
          if (cancelled) return;
          setAdoptUiActive(false);
          setAdoptPollPlanId(null);
          setAdoptLine({ message: '', type: '' });
          navigate('/execution');
        }, 1500);
        return;
      }

      setAdoptLine({ message: line, type: 'progress' });
    };

    const tick = async () => {
      try {
        const data = await solutionApi.getAdoptProgress(adoptPollPlanId);
        if (cancelled) return;
        applyPayload(data);
      } catch (e) {
        if (cancelled) return;
        stopInterval();
        setAdoptPollPlanId(null);
        const errText = e instanceof Error ? e.message : '进度查询失败';
        setAdoptLine({ message: errText, type: 'error' });
        message.error('采纳执行进度查询失败');
      }
    };

    void tick();
    intervalId = setInterval(() => {
      void tick();
    }, POLL_MS);

    return () => {
      cancelled = true;
      stopInterval();
      if (completionTimer !== undefined) clearTimeout(completionTimer);
    };
  }, [adoptUiActive, adoptPollPlanId, navigate, message]);

  const handleDismissAdoptBar = () => {
    setAdoptUiActive(false);
    setAdoptPollPlanId(null);
    setAdoptLine({ message: '', type: '' });
  };

  const handleRetryAdoptMonitor = () => {
    const sid = adoptExecutedPlanIdRef.current;
    if (!sid) return;
    setAdoptPollPlanId(sid);
    setAdoptUiActive(true);
    setAdoptLine({ message: '正在重新查询采纳执行…', type: 'progress' });
  };

  const handleViewDetail = (solutionId: string) => {
    if (selectedDiagnosisId) {
      navigate(`/solutions/${selectedDiagnosisId}?solution_id=${solutionId}`);
    }
  };

  const columns: ColumnsType<SolutionSummary> = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 70,
      render: (rank: number) => (
        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
          rank === 1 ? 'bg-[#0A43FF] text-[#fff]' :
          rank === 2 ? 'bg-[#D5EAFB] text-[#0A43FF]' :
          rank === 3 ? 'bg-[#D5EAFB] text-[#0A43FF]' :
          'bg-[#D5EAFB] text-[#0A43FF]'
        }`}>
          {rank <= 3 ? rank : rank}
        </div>
      ),
    },
    {
      title: '方案名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <span className="font-medium text-primary">{name}</span>,
    },
    {
      title: '针对异常',
      dataIndex: 'anomaly_ids',
      key: 'anomaly_ids',
      width: 200,
      render: (anomalyIds: string[] | undefined) => {
        if (!anomalyIds || anomalyIds.length === 0) return <span className="text-gray-500">-</span>;
        const anomalies = diagnosisReport?.anomalies || [];
        const matched = anomalyIds
          .map(id => anomalies.find((a: Anomaly) => a.id === id || a.metric_name === id))
          .filter(Boolean) as Anomaly[];
        if (matched.length === 0) {
          return <span className="text-gray-500">{anomalyIds.length}个异常</span>;
        }
        return (
          <div className="flex flex-wrap gap-1">
            {matched.slice(0, 3).map((a) => (
              <Tag key={a.id} style={{ backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', border: 'none' }} className="!m-0">{a.rule_name}</Tag>
            ))}
            {matched.length > 3 && <Tag style={{ backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', border: 'none' }} className="!m-0">+{matched.length - 3}</Tag>}
          </div>
        );
      },
    },
    {
      title: '优先级',
      dataIndex: 'score',
      key: 'score',
      width: 100,
      render: (score: number) => (
        <span className={`font-bold ${score >= 7 ? 'text-emerald-400' : score >= 5 ? 'text-amber-400' : 'text-rose-400'}`}>
          {score.toFixed(1)}
        </span>
      ),
    },
    {
      title: '步骤 / ROI',
      key: 'step_roi',
      width: 120,
      render: (_, record) => (
        <span className="text-secondary text-sm">
          <ClockCircleOutlined className="mr-1" />
          {record.step_count} 步 · ROI {record.expected_roi.toFixed(1)}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => {
        if (status === 'adopted') return <Tag style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: 'none' }}>已采纳</Tag>;
        if (status === 'rejected') return <Tag style={{ backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'none' }}>已拒绝</Tag>;
        return <Tag style={{ backgroundColor: 'rgba(107, 114, 128, 0.2)', color: '#6b7280', border: 'none' }}>待评估</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_, record) => {
        const isAdopted = record.status === 'adopted';
        return (
          <div className="flex gap-1">
            <Button type="link" size="small" onClick={() => handleViewDetail(record.solution_id)}>
              详情
            </Button>
            {isAdopted && (
              <Button
                type="link"
                size="small"
                icon={<RocketOutlined />}
                onClick={() => navigate('/execution')}
              >
                查看执行
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  const anyAdopted = useMemo(() => solutions.some((s) => s.status === 'adopted'), [solutions]);

  const listPersistentLine = useMemo(
    () =>
      formatSolutionsListPersistent({
        selectedDiagnosisId,
        isCompleted,
        isLoading,
        generating: Boolean(solutionData?.generating),
        solutionCount: solutions.length,
        anyAdopted,
      }),
    [
      selectedDiagnosisId,
      isCompleted,
      isLoading,
      solutionData?.generating,
      solutions.length,
      anyAdopted,
    ],
  );

  if (!enterpriseId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Empty description="请先选择企业" />
      </div>
    );
  }

  const adoptRunning = adoptUiActive && adoptLine.type === 'progress';

  return (
    <div className="space-y-6 bg-[#F0F1F9] min-h-screen">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <h1 className="m-0 flex shrink-0 items-center gap-3 text-3xl font-bold leading-tight tracking-tight text-[#303133]">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 text-lg text-white shadow-lg shadow-amber-500/20">
              <BulbOutlined />
            </span>
            优化方案
          </h1>
          {enterpriseId && diagnosisItems.length > 0 && (
            <DiagnosisHistorySelect
              className="max-w-full shrink-0 sm:ml-auto"
              diagnosisItems={diagnosisItems}
              value={selectedDiagnosisId}
              onChange={setSelectedDiagnosisId}
              loading={listLoading}
              disabled={adoptRunning}
            />
          )}
        </div>
        {((listPersistentLine != null && listPersistentLine !== '') || adoptUiActive) && (
          <TrackingHeaderStatus
            className="!mt-0 border-t border-[#E4E7ED] pt-3"
            persistent={listPersistentLine}
            transient={
              adoptUiActive ? (
                <div>
                  <p
                    className={`text-sm ${
                      adoptLine.type === 'error' ? 'text-red-600' : 'text-[#606266]'
                    }`}
                  >
                    {adoptLine.type === 'completed'
                      ? adoptLine.message || '执行已完成'
                      : adoptLine.message ||
                        (adoptLine.type === 'progress' ? '正在处理中，请稍候…' : '')}
                  </p>
                  {adoptLine.type === 'completed' && (
                    <Button type="link" size="small" className="mt-1 h-auto p-0" onClick={() => navigate('/execution')}>
                      查看执行任务
                    </Button>
                  )}
                  {adoptLine.type === 'error' && (
                    <div className="mt-1 flex flex-wrap gap-x-3">
                      <Button type="link" size="small" className="h-auto p-0" onClick={handleDismissAdoptBar}>
                        关闭提示
                      </Button>
                      <Button type="link" size="small" className="h-auto p-0" onClick={handleRetryAdoptMonitor}>
                        重试
                      </Button>
                    </div>
                  )}
                </div>
              ) : undefined
            }
          />
        )}
      </div>

      {solutionData && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">
                {solutionData.total || solutionData.solutions?.length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">方案总数</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-emerald-400">
                {solutionData.solutions?.filter((s: SolutionSummary) => s.status === 'adopted').length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">已采纳</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-amber-400">
                {solutionData.solutions?.[0]?.score?.toFixed(1) || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">最高评分</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-purple-400">
                {diagnosisReport?.anomalies?.length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">异常指标数</div>
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : !selectedDiagnosisId ? (
          <Empty description="请先完成诊断后查看方案" />
        ) : !isCompleted ? (
          <Empty description="该次诊断尚未完成，暂无方案" />
        ) : (
          <Table
            columns={columns}
            dataSource={solutionData?.solutions || []}
            rowKey="solution_id"
            pagination={false}
            locale={{ emptyText: <Empty description="暂无方案，请先在仪表盘完成诊断" /> }}
          />
        )}
      </Card>
    </div>
  );
}
