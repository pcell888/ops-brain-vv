import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card, Row, Col, Tag, Button, Empty, Spin,
  App, Statistic, Divider, Alert, Modal,
} from 'antd';
import {
  ArrowLeftOutlined, BulbOutlined, CheckCircleOutlined, ThunderboltOutlined,
  TrophyOutlined,
  WarningOutlined, StarOutlined, SwapOutlined, AimOutlined, RocketOutlined,
} from '@ant-design/icons';
import {
  useSolutionList, useAdoptSolution, useDiagnosisReport, adoptProgressLooksActive,
} from '@/lib/hooks';
import { solutionApi, type AdoptProgressResponse } from '@/lib/api';
import { useAppStore } from '@/stores/app-store';
import { TrackingHeaderStatus } from '@/components/tracking-header-status';
import { formatSolutionDetailPersistent } from '@/lib/solutions-header-status';
import clsx from 'clsx';
import type { SolutionSummary, SolutionGenerateResponse, DiagnosisReport, AIRecommendation } from '@/lib/types';
// 严重程度配置
const severityConfig: Record<string, { color: string; text: string; bgClass: string }> = {
  critical: { color: 'red', text: '严重', bgClass: 'bg-[rgba(255,232,232,1)]' },
  high: { color: 'orange', text: '高', bgClass: 'bg-[rgba(255,239,224,1)]' },
  medium: { color: 'gold', text: '中等', bgClass: 'bg-[rgba(0,199,119,0.08)]' },
  low: { color: 'blue', text: '低', bgClass: 'bg-[rgba(10,67,255,0.08)]' },
};

export default function SolutionDetailPage() {
  const { message } = App.useApp();
  const params = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const diagnosisId = params.diagnosisId as string;

  const solutionIdFromUrl = searchParams.get('solution_id');
  const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(solutionIdFromUrl);

  const { currentEnterprise } = useAppStore();
  const { data: solutionData, isLoading: solutionsLoading, refetch } = useSolutionList(diagnosisId);
  const typedSolutionData = solutionData as SolutionGenerateResponse | undefined;
  const { data: diagnosisReport } = useDiagnosisReport(diagnosisId);
  const adoptSolution = useAdoptSolution();

  const [isExecuting, setIsExecuting] = useState(false);
  const [executionProgress, setExecutionProgress] = useState<{ message: string; type: string }>({ message: '', type: '' });
  const [isAdopting, setIsAdopting] = useState(false);
  /** 有值时轮询 GET /solutions/{id}/adopt/progress（与 executedPlanIdRef 同步于采纳开始） */
  const [adoptPollPlanId, setAdoptPollPlanId] = useState<string | null>(null);
  const executedPlanIdRef = useRef<string | null>(null);
  const solutions = typedSolutionData?.solutions || [];
  const solutionsProbeKey = useMemo(
    () => solutions.map((s) => `${s.solution_id}:${s.status ?? ''}`).join('|'),
    [solutions],
  );
  const anySolutionAdopted = solutions.some((s) => s.status === 'adopted');
  const aiRecommendation: AIRecommendation | null = typedSolutionData?.ai_recommendation ?? null;
  const recommendedSolution = aiRecommendation
    ? solutions.find((s) => s.solution_id === aiRecommendation.recommended_solution_id)
    : undefined;
  const aiRecommendationLine = aiRecommendation
    ? (() => {
      const rest = (aiRecommendation.comparison_summary || '').trim();
      if (!rest) return aiRecommendation.reason;
      const tail = rest.replace(/^共 \d+ 个方案[，,]/, '');
      return `${aiRecommendation.reason}，${tail}`;
    })()
    : null;

  useEffect(() => {
    if (solutions.length > 0 && !selectedSolutionId) {
      if (solutionIdFromUrl) {
        const exists = solutions.some(s => s.solution_id === solutionIdFromUrl);
        if (exists) { setSelectedSolutionId(solutionIdFromUrl); return; }
      }
      setSelectedSolutionId(solutions[0].solution_id);
    }
  }, [solutions, selectedSolutionId, solutionIdFromUrl]);

  const handleAdopt = useCallback(
    async (solutionId: string, retry: boolean = false) => {
      if (!retry) {
        if (anySolutionAdopted && !solutions.find((s) => s.solution_id === solutionId && s.status === 'adopted')) {
          message.warning('已有方案被采纳，不可再采纳其他方案');
          return;
        }
        executedPlanIdRef.current = solutionId;
        setAdoptPollPlanId(solutionId);
        setIsExecuting(true);
        setExecutionProgress({ message: '正在采纳方案...', type: 'progress' });
      }

      setIsAdopting(true);
      try {
        await adoptSolution.mutateAsync(solutionId);
        message.success('方案已采纳');
        await refetch();
      } catch {
        message.error('采纳失败');
        setExecutionProgress({ message: '采纳失败', type: 'error' });
        setAdoptPollPlanId(null);
      } finally {
        setIsAdopting(false);
      }
    },
    [anySolutionAdopted, solutions, message, adoptSolution, refetch],
  );

  /** 从方案列表「采纳」跳转 ?auto_adopt=1 时，自动走同一套执行蒙层 + 进度轮询 */
  useEffect(() => {
    if (searchParams.get('auto_adopt') !== '1') return;
    if (solutionsLoading || typedSolutionData?.generating) return;

    const sid = searchParams.get('solution_id');
    const stripAuto = () => {
      const next = new URLSearchParams(searchParams);
      next.delete('auto_adopt');
      setSearchParams(next, { replace: true });
    };

    if (!sid) {
      stripAuto();
      return;
    }

    if (!solutions.some((s) => s.solution_id === sid)) {
      stripAuto();
      message.warning('未找到该方案');
      return;
    }

    const dedupeKey = `${diagnosisId}:${sid}`;
    if (typeof sessionStorage !== 'undefined') {
      const sk = `auto_adopt:${dedupeKey}`;
      if (sessionStorage.getItem(sk)) {
        stripAuto();
        return;
      }
      sessionStorage.setItem(sk, '1');
    }

    stripAuto();
    setSelectedSolutionId(sid);
    void handleAdopt(sid);
  }, [
    searchParams,
    setSearchParams,
    diagnosisId,
    solutionsLoading,
    typedSolutionData?.generating,
    solutions,
    handleAdopt,
    message,
  ]);

  /** 刷新/返回页面：若后端采纳执行任务仍在跑，恢复状态文案与轮询 */
  useEffect(() => {
    if (solutionsLoading || typedSolutionData?.generating || !diagnosisId || !solutionsProbeKey) return;
    if (isExecuting || adoptPollPlanId || isAdopting) return;

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
          executedPlanIdRef.current = s.solution_id;
          setAdoptPollPlanId(s.solution_id);
          setIsExecuting(true);
          const line = (data.message || '').trim() || '正在执行采纳方案…';
          setExecutionProgress({ message: line, type: 'progress' });
          return;
        } catch {
          // 无对应线程或已结束
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    solutionsLoading,
    typedSolutionData?.generating,
    diagnosisId,
    solutionsProbeKey,
    isExecuting,
    adoptPollPlanId,
    isAdopting,
  ]);

  /** 采纳后执行阶段：轮询兼容层 adopt/progress（与 progress_cache 同源） */
  useEffect(() => {
    if (!isExecuting || !adoptPollPlanId) return;

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
        setExecutionProgress({ message: line, type: 'error' });
        message.error(line);
        return;
      }

      if (status === 'completed' && !isRunning) {
        stopInterval();
        setExecutionProgress({ message: line, type: 'completed' });
        completionTimer = setTimeout(() => {
          if (cancelled) return;
          setIsExecuting(false);
          setAdoptPollPlanId(null);
          setExecutionProgress({ message: '', type: '' });
          navigate('/execution');
        }, 1500);
        return;
      }

      setExecutionProgress({
        message: line,
        type: 'progress',
      });
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
        setExecutionProgress({ message: errText, type: 'error' });
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
  }, [isExecuting, adoptPollPlanId, navigate, message]);

  const selectedSolution = solutions.find(s => s.solution_id === selectedSolutionId);

  const detailPersistentLine = useMemo(
    () =>
      formatSolutionDetailPersistent({
        selectedSolutionId,
        selectedStatus: selectedSolution?.status,
        solutionCount: solutions.length,
        anySolutionAdopted,
      }),
    [selectedSolutionId, selectedSolution?.status, solutions.length, anySolutionAdopted],
  );

  const handleAdoptDetailWithConfirm = () => {
    if (!selectedSolution || selectedSolution.status === 'adopted') return;
    if (anySolutionAdopted) return;
    const sid = selectedSolution.solution_id;
    Modal.confirm({
      title: '是否执行？',
      content: '确认后将采纳该方案并进入任务详情中的执行列表。',
      okText: '执行',
      cancelText: '取消',
      onOk: () => handleAdopt(sid),
    });
  };

  /** 优先级得分约 0–10（generate 节点公式），非百分制 */
  const getPriorityScoreColor = (score: number) => {
    if (score >= 7) return 'text-emerald-400';
    if (score >= 5) return 'text-amber-400';
    return 'text-rose-400';
  };

  if (solutionsLoading) {
    return <div className="flex items-center justify-center h-[60vh]"><Spin size="large" /></div>;
  }

  if (typedSolutionData?.generating) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}>返回</Button>
        <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
          <Spin size="large" />
          <p className="text-gray-400">正在生成优化方案，请稍候…</p>
        </div>
      </div>
    );
  }

  if (solutions.length === 0) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}>返回</Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty description="暂无优化方案">
            <Button type="primary" onClick={() => navigate('/solutions')}>返回方案列表</Button>
          </Empty>
        </div>
      </div>
    );
  }

  const handleCancelExecution = () => {
    setIsExecuting(false);
    setAdoptPollPlanId(null);
    setExecutionProgress({ message: '', type: '' });
  };

  const handleViewTasks = () => {
    setIsExecuting(false);
    setAdoptPollPlanId(null);
    setExecutionProgress({ message: '', type: '' });
    navigate('/execution');
  };

  const adoptRunning = isExecuting && executionProgress.type === 'progress';

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}>返回</Button>
        <div className="min-w-0 flex-1">
          <h1 className="m-0 flex items-center gap-3 text-3xl font-bold leading-tight tracking-tight text-[#303133]">
            <span className="text-[#fff] w-11 h-11 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-lg shadow-lg shadow-amber-500/20 shrink-0">
              <BulbOutlined />
            </span>
            方案详情
          </h1>
          <p className="text-muted mt-1 text-xs font-mono break-all">
            {diagnosisId}
          </p>
          {((detailPersistentLine != null && detailPersistentLine !== '') || isExecuting) && (
            <TrackingHeaderStatus
              className="!mt-0 border-t border-[#E4E7ED] pt-3"
              persistent={detailPersistentLine}
              transient={
                isExecuting ? (
                  <div>
                    <p
                      className={`text-sm ${
                        executionProgress.type === 'error' ? 'text-red-600' : 'text-[#606266]'
                      }`}
                    >
                      {executionProgress.type === 'completed'
                        ? executionProgress.message || '执行已完成'
                        : executionProgress.message ||
                          (executionProgress.type === 'progress' ? '正在处理中，请稍候…' : '')}
                    </p>
                    {executionProgress.type === 'completed' && (
                      <Button type="link" size="small" className="mt-1 h-auto p-0" onClick={handleViewTasks}>
                        查看执行任务
                      </Button>
                    )}
                    {executionProgress.type === 'error' && (
                      <div className="mt-1 flex flex-wrap gap-x-3">
                        <Button type="link" size="small" className="h-auto p-0" onClick={handleCancelExecution}>
                          关闭提示
                        </Button>
                        <Button
                          type="link"
                          size="small"
                          className="h-auto p-0"
                          loading={isAdopting}
                          onClick={() => executedPlanIdRef.current && handleAdopt(executedPlanIdRef.current, true)}
                        >
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
      </div>

      {aiRecommendation && (
        <Card className="!bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10 !border-cyan-500/30">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xl shadow-lg">
              <StarOutlined />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg font-bold text-[#303133]">AI 智能建议</span>
                <Tag
                  className={clsx(
                    "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                    'bg-[rgba(10,67,255,0.08)] text-[rgba(10,67,255,1)]'
                  )}
                >
                  自动分析
                </Tag>
              </div>
              <p className="text-[#303133] mb-3">综合优先级得分最高（5.9），推荐方案「客户留存与生命周期价值提升方案」ROI 为 5.5</p>
              {aiRecommendation.risk_warning && (
                <Alert type="warning" showIcon icon={<WarningOutlined />} message={aiRecommendation.risk_warning} className="!bg-amber-500/10 !border-amber-500/30" />
              )}
              <div className="mt-4 flex gap-3">
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleAdopt(aiRecommendation.recommended_solution_id)}
                  loading={adoptSolution.isPending}
                  disabled={
                    adoptRunning
                    || !recommendedSolution
                    || recommendedSolution.status === 'adopted'
                    || (anySolutionAdopted && recommendedSolution.status !== 'adopted')
                  }
                  title={anySolutionAdopted && recommendedSolution?.status !== 'adopted' ? '已有方案被采纳' : undefined}
                >
                  {recommendedSolution?.status === 'adopted' ? '已采纳' : '采纳推荐方案'}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {solutions.length > 1 && (
        <Card title={
          <div className="flex items-center gap-2">
            <SwapOutlined className="text-purple-400" />
            <span>方案对比</span>
            <Tag
              className={clsx(
                "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                'bg-[rgba(10,67,255,0.08)] text-[rgba(10,67,255,1)]'
              )}
            >
              {solutions.length}个方案
            </Tag>
          </div>
        }>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-[#303133] font-medium">方案</th>
                  <th className="text-center py-3 px-4 text-[#303133] font-medium">优先级</th>
                  <th className="text-center py-3 px-4 text-[#303133] font-medium">步骤</th>
                  <th className="text-center py-3 px-4 text-[#303133] font-medium">预期ROI</th>
                  <th className="text-center py-3 px-4 text-[#303133] font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {solutions.map((solution, index) => {
                  const isRecommended = solution.solution_id === aiRecommendation?.recommended_solution_id;
                  return (
                    <tr
                      key={solution.solution_id}
                      className={clsx(
                        'border-b border-gray-800 transition-colors cursor-pointer',
                        isRecommended ? 'bg-cyan-500/10' : 'hover:bg-gray-800/50',
                        selectedSolutionId === solution.solution_id && 'bg-blue-500/10'
                      )}
                      onClick={() => setSelectedSolutionId(solution.solution_id)}
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                          <div className={clsx(
                            'w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm',
                            index === 0 ? 'bg-[rgba(10,67,255,1)] text-[#fff]' : 'bg-[#D5EAFB] text-[rgba(10,67,255,1)]'
                          )}>
                            {index + 1}
                          </div>
                          <div>
                            <div className="font-medium text-[#303133] flex items-center gap-2">
                              {solution.name}
                              {isRecommended && (
                                <Tag
                                  className={clsx(
                                    "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                                    'bg-[rgba(10,67,255,0.08)] text-[rgba(10,67,255,1)]'
                                  )}
                                >
                                  推荐
                                </Tag>
                              )}
                              {solution.status === 'adopted' && (
                                <Tag
                                  className={clsx(
                                    "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                                    'bg-[rgba(0,199,119,0.08)] text-[rgba(0,199,119,1)]'
                                  )}
                                >
                                  已采纳
                                </Tag>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className="font-bold text-lg text-[#303133]">
                          {solution.score.toFixed(1)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center text-[#303133]">
                        {solution.step_count} 步
                      </td>
                      <td className="py-4 px-4 text-center">
                        <Tag
                          className={clsx(
                            "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                            'bg-[rgba(10,67,255,0.08)] text-[rgba(10,67,255,1)]'
                          )}
                        >
                          {solution.expected_roi.toFixed(1)}
                        </Tag>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <Button
                          type="link"
                          size="small"
                          icon={<CheckCircleOutlined />}
                          onClick={(e) => { e.stopPropagation(); handleAdopt(solution.solution_id); }}
                          disabled={adoptRunning || solution.status === 'adopted' || anySolutionAdopted}
                          loading={adoptSolution.isPending}
                          title={anySolutionAdopted && solution.status !== 'adopted' ? '已有方案被采纳' : undefined}
                        >
                          <span className={solution.status === "adopted" ? "text-[#fff]" : "text-[#fff]"}>
                            {solution.status === 'adopted' ? '已采纳' : '采纳'}</span>
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {selectedSolution && (
        <Row gutter={16}>
          <Col span={16}>
            <Card
              title={
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BulbOutlined className="text-amber-400" />
                    <span>{selectedSolution.name}</span>
                    {selectedSolution.status === 'adopted' && (
                      <Tag
                        className={clsx(
                          "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                          'bg-[rgba(0,199,119,0.08)] text-[rgba(0,199,119,1)]'
                        )}
                      >
                        已采纳
                      </Tag>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      onClick={handleAdoptDetailWithConfirm}
                      loading={adoptSolution.isPending}
                      disabled={adoptRunning || selectedSolution.status === 'adopted' || anySolutionAdopted}
                      title={anySolutionAdopted && selectedSolution.status !== 'adopted' ? '已有方案被采纳' : undefined}
                    >
                      {selectedSolution.status === 'adopted' ? '已采纳' : '采纳方案'}
                    </Button>
                  </div>
                </div>
              }
            >
              <div className="space-y-6">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title={<span style={{ color: '#303133' }}>优先级得分</span>}
                      value={selectedSolution.score}
                      suffix="分"
                      valueStyle={{ color: selectedSolution.score >= 7 ? '#10b981' : selectedSolution.score >= 5 ? '#f59e0b' : '#ef4444' }}
                    />
                  </Col>
                    <Col span={8}>
                    <Statistic
                      title={<span style={{ color: '#303133' }}>执行步骤</span>}
                      value={selectedSolution.step_count}
                      suffix="步"
                      valueStyle={{ color: '#303133' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title={<span style={{ color: '#303133' }}>预期 ROI</span>}
                      value={selectedSolution.expected_roi.toFixed(1)}
                      suffix=""
                      valueStyle={{ color: '#38bdf8' }}
                    />
                  </Col>
                </Row>

                <Divider />

                {selectedSolution.recommendation_reason && (
                  <div>
                    <h4 className="text-[#303133] font-medium mb-3 flex items-center gap-2">
                      <AimOutlined className="text-blue-400" />方案概述
                    </h4>
                    <div className="rounded-lg p-4 text-[#303133] leading-relaxed">
                      {selectedSolution.recommendation_reason}
                    </div>
                    <Divider />
                  </div>
                )}

                <div>
                  <h4 className="text-[#303133] font-medium mb-3 flex items-center gap-2">
                    <RocketOutlined className="text-violet-400" />
                    执行步骤
                  </h4>
                  {selectedSolution.steps && selectedSolution.steps.length > 0 ? (
                    <div className="space-y-3">
                      {selectedSolution.steps.map((st) => (
                        <div
                          key={`${selectedSolution.solution_id}-step-${st.step}`}
                          className="border border-gray-700/80 rounded-lg p-4 text-left"
                        >
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <Tag
                              className={clsx(
                                "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                                'bg-[rgba(10,67,255,0.08)] text-[rgba(10,67,255,1)]'
                              )}
                            >
                              步骤 {st.step}
                            </Tag>
                            {st.owner_dept && (
                              <Tag
                                className={clsx(
                                  "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                                  'bg-[rgba(10,67,255,0.08)] text-[rgba(10,67,255,1)]'
                                )}
                              >
                                {st.owner_dept}
                              </Tag>
                            )}
                            {st.timeline && (
                              <Tag
                                className={clsx(
                                  "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                                  'bg-gray-100 text-gray-600'
                                )}
                              >
                                {st.timeline}
                              </Tag>
                            )}
                          </div>
                          <p className="text-[#303133] leading-relaxed text-sm">{st.action}</p>
                          {st.data_context ? (
                            <p className="text-[#303133] text-xs mt-2 leading-relaxed">
                              <span className="text-[#303133]">数据依据：</span>
                              {st.data_context}
                            </p>
                          ) : null}
                          {st.implementation_steps && st.implementation_steps.length > 0 ? (
                            <div className="mt-3 text-xs text-gray-300">
                              <div className="text-[#303133] mb-1">实施步骤</div>
                              <ol className="list-decimal pl-4 space-y-1 text-[#303133]">
                                {st.implementation_steps.map((line, i) => (
                                  <li key={i}>{line}</li>
                                ))}
                              </ol>
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      description="暂无步骤明细（请重新诊断生成或检查后端方案数据）"
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      className="!my-2"
                    />
                  )}
                </div>
              </div>
            </Card>
          </Col>

          <Col span={8}>
            <Card
              title={
                <div className="flex items-center gap-2">
                  <ThunderboltOutlined className="text-amber-400" />
                  <span>针对异常</span>
                </div>
              }
              className="h-full"
            >
              {selectedSolution.anomaly_ids && selectedSolution.anomaly_ids.length > 0 ? (
                <div className="space-y-3">
                  {selectedSolution.anomaly_ids.map((aid) => {
                    const anomaly = (diagnosisReport as DiagnosisReport | undefined)?.anomalies?.find(
                      (a) => a.id === aid || a.metric_name === aid
                    );
                    if (!anomaly) return (
                      <div key={aid} className="bg-gray-800/30 rounded-lg p-3 text-gray-500 text-sm">{aid}</div>
                    );
                    return (
                      <div key={aid} className="bg-gradient-to-r from-rose-500/10 to-transparent rounded-lg p-3 border border-rose-500/20">
                        <div className="flex justify-between items-start mb-1">
                          <span className="text-[#303133] font-medium text-sm">{anomaly.rule_name}</span>
                          <Tag
                            className={clsx(
                              "!m-0 !border-0 !px-2.5 !py-0.5 !text-xs !font-medium",
                              anomaly.severity === 'critical' ? 'bg-[rgba(255,232,232,1)] text-[rgba(255,56,60,1)]' :
                                anomaly.severity === 'high' ? 'bg-[rgba(255,239,224,1)] text-[rgba(255,141,40,1)]' :
                                  'bg-[rgba(0,199,119,0.08)] text-[rgba(0,199,119,1)]'
                            )}
                          >
                            {anomaly.severity === 'critical' ? '严重' : anomaly.severity === 'high' ? '高' : '中'}
                          </Tag>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-400">
                          <span>当前: <span className="text-rose-400 font-medium">{anomaly.current_value?.toFixed(1)}{anomaly.unit || '%'}</span></span>
                          {anomaly.benchmark_value && (
                            <span>基准: <span className="text-emerald-400">{anomaly.benchmark_value?.toFixed(1)}{anomaly.unit || '%'}</span></span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Empty description="无关联异常" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}
