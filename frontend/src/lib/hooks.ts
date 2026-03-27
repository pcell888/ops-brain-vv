

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  diagnosisApi,
  enterpriseApi,
  solutionApi,
  executionApi,
  trackingApi,
  reviewApi,
  customDimensionApi,
} from './api';
import { wsManager, type TaskStatusMessage, type TaskStatus } from './websocket';
import type {
  DiagnosisReport,
  DiagnosisListResponse,
  DiagnosisStatusResponse,
  SolutionGenerateResponse,
  SolutionDetail,
  ExecutionPlanSummary,
  ExecutionTask,
  ExecutionTaskDetail,
  TaskStats,
  GanttData,
  TrackingSummary,
} from './types';

// ============ 诊断模块 Hooks ============

// 获取诊断报告（不做缓存，始终用最新接口结果）
export function useDiagnosisReport(diagnosisId: string | null, pauseFetching = false) {
  return useQuery<DiagnosisReport>({
    queryKey: ['diagnosis', 'report', diagnosisId],
    queryFn: () => diagnosisApi.getReport(diagnosisId!),
    enabled: !!diagnosisId && !pauseFetching,
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: 'always',
  });
}

// 获取单个异常指标详情
export function useAnomalyDetail(diagnosisId: string | null, anomalyId: string | null) {
  return useQuery({
    queryKey: ['diagnosis', 'anomaly', diagnosisId, anomalyId],
    queryFn: () => diagnosisApi.getAnomalyDetail(diagnosisId!, anomalyId!),
    enabled: !!diagnosisId && !!anomalyId,
  });
}

// 获取诊断状态（可选运行中轮询，避免切页回来后进度卡住）
export function useDiagnosisStatus(
  diagnosisId: string | null,
  options?: {
    enabled?: boolean;
    pollWhenActive?: boolean;
  }
) {
  const enabled = options?.enabled ?? true;
  const pollWhenActive = options?.pollWhenActive ?? false;
  return useQuery<DiagnosisStatusResponse>({
    queryKey: ['diagnosis', 'status', diagnosisId],
    queryFn: () => diagnosisApi.getStatus(diagnosisId!),
    enabled: !!diagnosisId && enabled,
    refetchOnMount: true,
    refetchOnWindowFocus: 'always',
    refetchInterval: (query) => {
      if (!pollWhenActive) return false;
      const s = (query.state.data as DiagnosisStatusResponse | undefined)?.status;
      return s === 'running' || s === 'pending' ? 2000 : false;
    },
  });
}

// 获取诊断历史列表
export function useDiagnosisList(enterpriseId: string | null, skip = 0, limit = 20, pauseFetching = false) {
  return useQuery<DiagnosisListResponse>({
    queryKey: ['diagnosis', 'list', enterpriseId, skip, limit],
    queryFn: () => diagnosisApi.list({ enterprise_id: enterpriseId!, skip, limit }),
    enabled: !!enterpriseId && !pauseFetching,
    staleTime: 0,
  });
}

/** 企业下历史诊断选择：默认最近一次，切换企业时重置 */
export function useDiagnosisSelection(enterpriseId: string | null) {
  const { data: diagnosisListData, isLoading: listLoading } = useDiagnosisList(enterpriseId, 0, 100);
  const diagnosisItems = useMemo(() => {
    const items = diagnosisListData?.items ?? [];
    return items
      .slice()
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
  }, [diagnosisListData?.items]);
  const [selectedDiagnosisId, setSelectedDiagnosisId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedDiagnosisId(null);
  }, [enterpriseId]);

  useEffect(() => {
    if (!diagnosisItems.length) return;
    setSelectedDiagnosisId((prev) => {
      if (prev == null || !diagnosisItems.some((i) => i.diagnosis_id === prev)) {
        return diagnosisItems[0].diagnosis_id;
      }
      return prev;
    });
  }, [diagnosisItems]);

  return { diagnosisItems, selectedDiagnosisId, setSelectedDiagnosisId, listLoading };
}

// 获取最新诊断报告
export function useLatestDiagnosisReport(enterpriseId: string | null, options?: { pauseFetching?: boolean }) {
  const pause = options?.pauseFetching ?? false;
  
  // 先获取列表，找到最新的诊断
  const listQuery = useDiagnosisList(enterpriseId, 0, 1, pause);
  const latestDiagnosis = listQuery.data?.items?.[0];
  const latestDiagnosisId = latestDiagnosis?.diagnosis_id;
  const latestStatusQuery = useDiagnosisStatus(latestDiagnosisId ?? null, {
    enabled: !!latestDiagnosisId && !pause,
    pollWhenActive: !pause && (latestDiagnosis?.status === 'running' || latestDiagnosis?.status === 'pending'),
  });
  const runtimeStatus = latestStatusQuery.data;

  // 列表与 /status 可能短暂不一致；failed 时绝不拉取报告，避免误用上一次成功的报告键或旧数据
  const listStatus = latestDiagnosis?.status;
  const effectiveStatus = runtimeStatus?.status ?? listStatus;
  const reportReady =
    effectiveStatus !== 'failed' &&
    (listStatus === 'completed' || latestDiagnosis?.report_ready === true);
  const reportQuery = useDiagnosisReport(
    reportReady && latestDiagnosisId ? latestDiagnosisId : null,
    pause
  );

  return {
    ...reportQuery,
    data: reportQuery.data as DiagnosisReport | undefined,
    isLoading: listQuery.isLoading || latestStatusQuery.isLoading || (reportReady && reportQuery.isLoading),
    latestDiagnosisId,
    lastDiagnosisDate: latestDiagnosis?.created_at,
    // 返回最新诊断的状态信息（用于进入页面时获取正在执行的任务状态）
    latestDiagnosisStatus: runtimeStatus?.status ?? latestDiagnosis?.status,
    latestDiagnosisProgress: runtimeStatus?.progress ?? latestDiagnosis?.progress,
    latestDiagnosisMessage: runtimeStatus?.message ?? latestDiagnosis?.message,
    // 刷新列表的方法
    refetchList: listQuery.refetch,
  };
}

// 启动诊断
export function useStartDiagnosis() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: { 
      enterprise_id: string; 
      trigger_type?: string;
      dimensions?: string[];
      async_mode?: boolean;
    }) => diagnosisApi.start(data),
    onSuccess: (_, variables) => {
      // 刷新诊断列表
      queryClient.invalidateQueries({ 
        queryKey: ['diagnosis', 'list', variables.enterprise_id] 
      });
    },
  });
}

// 取消诊断（pending/running 可取消）
export function useCancelDiagnosis(enterpriseId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (diagnosisId: string) => diagnosisApi.cancel(diagnosisId),
    onSuccess: () => {
      if (enterpriseId) {
        queryClient.refetchQueries(
          { queryKey: ['diagnosis', 'list', enterpriseId, 0, 1] },
          { cancelRefetch: true }
        );
        queryClient.invalidateQueries({ queryKey: ['diagnosis', 'report'] });
      }
    },
  });
}


// 获取行业基准
export function useBenchmarks(industry?: string) {
  return useQuery({
    queryKey: ['diagnosis', 'benchmarks', industry],
    queryFn: () => diagnosisApi.getBenchmarks(industry),
  });
}

// 钻取数据类型
export interface DrillDownResponse {
  metric_name: string;
  dimension: string;
  time_range: { start: string; end: string };
  data: Array<Record<string, unknown>>;
  total: number;
  page: number;
  page_size: number;
}

// 指标钻取数据（days 通常取企业配置 analysis_period_days，与系统设置「数据分析周期」一致）
export function useDrillDownData(
  metricName: string,
  enterpriseId: string | null,
  dimension: string,
  days: number = 30,
  page: number = 1,
  pageSize: number = 10,
  options?: { enabled?: boolean }
) {
  return useQuery<DrillDownResponse>({
    queryKey: ['diagnosis', 'drill-down', metricName, enterpriseId, dimension, days, page, pageSize],
    queryFn: () => diagnosisApi.drillDown(metricName, {
      enterprise_id: enterpriseId!,
      dimension,
      days,
      page,
      page_size: pageSize,
    }),
    enabled: (options?.enabled ?? true) && !!enterpriseId && !!metricName,
  });
}

/** 拉取企业详情（含 config.analysis_period_days），与 dashboard 共用 queryKey */
export function useEnterpriseDetail(enterpriseId: string | null) {
  return useQuery({
    queryKey: ['enterprise', enterpriseId],
    queryFn: () => enterpriseApi.get(enterpriseId!),
    enabled: !!enterpriseId,
  });
}

// 指标钻取
export function useDrillDown(
  metricName: string | null,
  params: { enterprise_id: string; dimension: string; days?: number } | null
) {
  return useQuery({
    queryKey: ['diagnosis', 'drillDown', metricName, params],
    queryFn: () => diagnosisApi.drillDown(metricName!, params!),
    enabled: !!metricName && !!params?.enterprise_id && !!params?.dimension,
  });
}

// ============ 方案模块 Hooks ============

// 生成方案（后台任务模式：提交 → 轮询 → 完成）
export function useGenerateSolutions(onProgress?: (progressStep: number) => void) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: { 
      enterprise_id: string;
      diagnosis_id: string;
      anomaly_ids?: string[];
      ranking_strategy?: string;
    }) => {
      // 1. 提交生成任务，立即返回 task_id
      const { task_id } = await solutionApi.generate(data);
      
      // 2. 轮询任务状态直到完成或失败
      const pollInterval = 1500; // 1.5s
      const maxAttempts = 120;   // 最多 3 分钟
      
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        const status = await solutionApi.getGenerationStatus(task_id);
        
        // 更新进度步骤
        if (status.progress_step !== undefined && onProgress) {
          onProgress(status.progress_step);
        }
        
        if (status.status === 'completed') {
          return status.result;
        }
        if (status.status === 'failed') {
          throw new Error(status.error || '方案生成失败');
        }
        // pending / running → 继续轮询
      }
      
      throw new Error('方案生成超时，请稍后刷新查看');
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: ['solutions', 'list', variables.diagnosis_id] 
      });
    },
  });
}

/**
 * 跟踪方案生成任务状态
 * 
 * 页面加载时自动检测是否有活跃的生成任务，有则恢复轮询。
 * 返回 isGenerating 状态和 progressStep 供按钮/UI 使用。
 */
export function useGenerationTask(diagnosisId: string | null) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [progressStep, setProgressStep] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const pollingRef = useRef(false);

  // 轮询任务直到完成
  const pollTask = useCallback(async (taskId: string, diagId: string) => {
    if (pollingRef.current) return; // 防止重复轮询
    pollingRef.current = true;
    setIsGenerating(true);
    setError(null);

    const pollInterval = 1500;
    const maxAttempts = 120;

    try {
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        const status = await solutionApi.getGenerationStatus(taskId);

        // 更新进度步骤
        if (status.progress_step !== undefined) {
          setProgressStep(status.progress_step);
        }

        if (status.status === 'completed') {
          queryClient.invalidateQueries({ queryKey: ['solutions', 'list', diagId] });
          setIsGenerating(false);
          setProgressStep(null);
          pollingRef.current = false;
          return;
        }
        if (status.status === 'failed') {
          setError(status.error || '方案生成失败');
          setIsGenerating(false);
          setProgressStep(null);
          pollingRef.current = false;
          return;
        }
      }
      setError('方案生成超时');
    } catch {
      setError('查询任务状态失败');
    }
    setIsGenerating(false);
    setProgressStep(null);
    pollingRef.current = false;
  }, [queryClient]);

  // 页面加载时检测活跃任务
  useEffect(() => {
    if (!diagnosisId) return;

    let cancelled = false;
    (async () => {
      try {
        const { task } = await solutionApi.getActiveGeneration(diagnosisId);
        if (task && !cancelled) {
          // 如果有进度步骤，立即设置
          if (task.progress_step !== undefined) {
            setProgressStep(task.progress_step);
          }
          pollTask(task.task_id, diagnosisId);
        }
      } catch {
        // 静默失败
      }
    })();

    return () => { cancelled = true; };
  }, [diagnosisId, pollTask]);

  return { isGenerating, progressStep, error };
}

// 获取方案列表
export function useSolutionList(diagnosisId: string | null) {
  return useQuery<SolutionGenerateResponse>({
    queryKey: ['solutions', 'list', diagnosisId],
    queryFn: () => solutionApi.list(diagnosisId!),
    enabled: !!diagnosisId,
    refetchInterval: (query) => {
      const d = query.state.data as SolutionGenerateResponse | undefined;
      if (d?.generating) return 2000;
      return false;
    },
  });
}

// 获取方案详情
export function useSolutionDetail(solutionId: string | null) {
  return useQuery<SolutionDetail>({
    queryKey: ['solutions', 'detail', solutionId],
    queryFn: () => solutionApi.getDetail(solutionId!),
    enabled: !!solutionId,
  });
}

// 采纳方案
export function useAdoptSolution() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (solutionId: string) => solutionApi.adopt(solutionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['solutions'] });
    },
  });
}

// 拒绝方案
export function useRejectSolution() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ solutionId, reason }: { solutionId: string; reason?: string }) => 
      solutionApi.reject(solutionId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['solutions'] });
    },
  });
}

// 对比方案
export interface SolutionComparisonItem {
  id: string;
  name: string;
  category: string;
  estimated_cost: number;
  estimated_duration: number;
  success_rate: number;
  ranking_score: number;
  task_count: number;
}

export interface SolutionComparisonResponse {
  solutions: SolutionComparisonItem[];
  dimensions: {
    cost: Record<string, number>;
    duration: Record<string, number>;
    success_rate: Record<string, number>;
    task_count: Record<string, number>;
  };
}

export function useCompareSolutions() {
  return useMutation<SolutionComparisonResponse, Error, string[]>({
    mutationFn: (solutionIds: string[]) => solutionApi.compare(solutionIds),
  });
}

// 获取方案模板列表
export function useSolutionTemplates(
  category?: string,
  skip: number = 0,
  limit: number = 10
) {
  return useQuery({
    queryKey: ['solutions', 'templates', category, skip, limit],
    queryFn: () => solutionApi.getTemplates(category, skip, limit),
    staleTime: 0,
    refetchOnMount: true,
  });
}

// 获取单个模板详情
export function useSolutionTemplateDetail(templateId: string | null) {
  return useQuery({
    queryKey: ['solutions', 'template', templateId],
    queryFn: () => solutionApi.getTemplateDetail(templateId!),
    enabled: !!templateId,
  });
}

// ============ 执行模块 Hooks ============

// 创建执行计划
export function useCreateExecutionPlan() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: { 
      enterprise_id: string;
      solution_id: string;
      start_date: string;
      scheduling_policy?: string;
    }) => executionApi.createPlan(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: ['execution', 'plans', variables.enterprise_id] 
      });
    },
  });
}

// 获取执行计划列表
export function useExecutionPlanList(
  enterpriseId: string | null,
  status?: string,
  skip: number = 0,
  limit: number = 10,
  diagnosisId?: string | null,
) {
  return useQuery({
    queryKey: ['execution', 'plans', enterpriseId, status, skip, limit, diagnosisId],
    queryFn: () =>
      executionApi.listPlans({
        enterprise_id: enterpriseId!,
        status,
        skip,
        limit,
        diagnosis_id: diagnosisId || undefined,
      }),
    enabled: !!enterpriseId && !!diagnosisId,
    staleTime: 0,
    refetchOnMount: true,
  });
}

/** 任务执行列表页：拉平任务行（非计划聚合） */
export function useExecutionTaskList(
  enterpriseId: string | null,
  diagnosisId?: string | null,
  limit: number = 500,
) {
  return useQuery<{ items: ExecutionTask[]; total: number; stats?: TaskStats }>({
    queryKey: ['execution', 'task-list', enterpriseId, diagnosisId, limit],
    queryFn: () =>
      executionApi.listTasks({
        enterprise_id: enterpriseId!,
        thread_id: diagnosisId || undefined,
        limit,
      }),
    enabled: !!enterpriseId && !!diagnosisId,
    staleTime: 0,
    refetchOnMount: true,
    refetchInterval: (query) => {
      const items = (query.state.data as { items?: ExecutionTask[] } | undefined)?.items || [];
      return items.some((t) => t.status === 'running') ? 3000 : false;
    },
  });
}

// 获取计划摘要（pollWhenActive 为 true 且计划为 running 时每 3 秒轮询，便于跟进未完成项）
export function useExecutionPlanSummary(planId: string | null, pollWhenActive?: boolean) {
  return useQuery<ExecutionPlanSummary>({
    queryKey: ['execution', 'plan', planId],
    queryFn: () => executionApi.getPlanSummary(planId!),
    enabled: !!planId,
    refetchInterval: (query) => {
      if (!pollWhenActive) return false;
      const s = (query.state.data as ExecutionPlanSummary)?.status;
      return s === 'running' ? 3000 : false;
    },
  });
}

// 获取甘特图数据
export function useGanttData(planId: string | null, enabled: boolean = true) {
  return useQuery<GanttData>({
    queryKey: ['execution', 'gantt', planId],
    queryFn: () => executionApi.getPlanGantt(planId!),
    enabled: !!planId && enabled,
  });
}

// ============ 追踪模块 Hooks ============

// 启动追踪
export function useStartTracking() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: { enterprise_id: string; plan_id: string; tracking_interval_days?: number }) => 
      trackingApi.start(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: ['tracking', 'list', variables.enterprise_id] 
      });
      queryClient.invalidateQueries({ 
        queryKey: ['execution', 'plan', variables.plan_id] 
      });
    },
  });
}

// 获取追踪列表（按诊断 thread_id 筛选）
export function useTrackingList(
  enterpriseId: string | null,
  status?: string,
  skip: number = 0,
  limit: number = 10,
  diagnosisId?: string | null,
) {
  return useQuery({
    queryKey: ['tracking', 'list', enterpriseId, status, skip, limit, diagnosisId],
    queryFn: () =>
      trackingApi.list({
        enterprise_id: enterpriseId!,
        status,
        skip,
        limit,
        diagnosis_id: diagnosisId || undefined,
      }),
    enabled: !!enterpriseId && !!diagnosisId,
    staleTime: 0, // 确保数据总是被认为是过期的，需要重新请求
    refetchOnMount: true, // 组件挂载时重新请求
  });
}

// 获取追踪摘要
export function useTrackingSummary(trackingId: string | null) {
  return useQuery<TrackingSummary>({
    queryKey: ['tracking', 'summary', trackingId],
    queryFn: () => trackingApi.getSummary(trackingId!),
    enabled: !!trackingId,
  });
}

// 获取指标趋势
export function useMetricTrends(
  trackingId: string | null,
  options?: { enabled?: boolean },
) {
  const on = options?.enabled ?? true;
  return useQuery({
    queryKey: ['tracking', 'trends', trackingId],
    queryFn: () => trackingApi.getTrends(trackingId!),
    enabled: !!trackingId && on,
  });
}

// 搜索案例
export function useCaseSearch(params: { 
  industry?: string; 
  problem_type?: string;
  min_score?: number;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['tracking', 'cases', params],
    queryFn: () => trackingApi.searchCases(params),
    staleTime: 0,
    refetchOnMount: true,
  });
}

// ============ 执行模块补充 Hooks ============

// 获取计划任务列表（refetchIntervalMs 用于执行中计划轮询刷新，如 3000）
export function usePlanTasks(planId: string | null, status?: string, refetchIntervalMs?: number) {
  return useQuery({
    queryKey: ['execution', 'tasks', planId, status],
    queryFn: () => executionApi.listPlanTasks(planId!, status),
    enabled: !!planId,
    refetchInterval: refetchIntervalMs ?? false,
  });
}

// 获取任务详情
export function useTaskDetail(taskId: string | null) {
  return useQuery<ExecutionTaskDetail>({
    queryKey: ['execution', 'task', taskId],
    queryFn: () => executionApi.getTaskDetail(taskId!),
    enabled: !!taskId,
    staleTime: 0,
  });
}

// 完成任务
export function useCompleteTask() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ taskId, resultData }: { taskId: string; resultData?: Record<string, unknown> }) => 
      executionApi.completeTask(taskId, resultData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['execution'] });
    },
  });
}

// 任务失败
export function useFailTask() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ taskId, errorMessage }: { taskId: string; errorMessage: string }) => 
      executionApi.failTask(taskId, errorMessage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['execution'] });
    },
  });
}

// 重试任务
export function useRetryTask() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (taskId: string) => executionApi.retryTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['execution'] });
    },
  });
}

// ============ 追踪模块补充 Hooks ============

// 采集快照（首次需带 enterpriseId 以创建追踪行）
export function useTakeSnapshot() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (variables: { trackingId: string; enterpriseId?: string | null }) =>
      trackingApi.takeSnapshot(variables.trackingId, variables.enterpriseId ? { enterprise_id: variables.enterpriseId } : {}),
    onSuccess: (_, variables) => {
      const id = variables.trackingId;
      queryClient.invalidateQueries({ queryKey: ['tracking', 'summary', id] });
      queryClient.invalidateQueries({ queryKey: ['tracking', 'snapshots', id] });
      queryClient.invalidateQueries({ queryKey: ['tracking', 'analyze', id] });
      queryClient.invalidateQueries({ queryKey: ['tracking', 'trends', id] });
      queryClient.invalidateQueries({ queryKey: ['tracking', 'list'] });
    },
  });
}

// 分析效果
export function useAnalyzeEffect(trackingId: string | null, options?: { enabled?: boolean }) {
  const on = options?.enabled ?? true;
  return useQuery({
    queryKey: ['tracking', 'analyze', trackingId],
    queryFn: () => trackingApi.analyze(trackingId!),
    enabled: !!trackingId && on,
  });
}

// 完成追踪
export function useCompleteTracking() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (trackingId: string) => trackingApi.complete(trackingId),
    onSuccess: (_, trackingId) => {
      queryClient.invalidateQueries({ queryKey: ['tracking', 'summary', trackingId] });
      queryClient.invalidateQueries({ queryKey: ['tracking', 'list'] });
    },
  });
}

export function useCancelTracking() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (trackingId: string) => trackingApi.cancel(trackingId),
    onSuccess: (_, trackingId) => {
      queryClient.invalidateQueries({ queryKey: ['tracking', 'summary', trackingId] });
      queryClient.invalidateQueries({ queryKey: ['tracking', 'list'] });
    },
  });
}

/** 待自动复盘时：跳过等待，恢复 LangGraph 执行 track_effects（复盘与沉淀） */
export function useStartReviewNow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (threadId: string) => reviewApi.start(threadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tracking', 'list'] });
    },
  });
}

// 获取复盘报告
export function useTrackingReport(trackingId: string | null) {
  return useQuery({
    queryKey: ['tracking', 'report', trackingId],
    queryFn: () => trackingApi.getReport(trackingId!),
    enabled: !!trackingId,
  });
}

// 获取快照列表
export function useTrackingSnapshots(trackingId: string | null, options?: { enabled?: boolean }) {
  const on = options?.enabled ?? true;
  return useQuery({
    queryKey: ['tracking', 'snapshots', trackingId],
    queryFn: () => trackingApi.getSnapshots(trackingId!),
    enabled: !!trackingId && on,
  });
}

// ============ 看板图表数据 Hooks ============

// 获取转化漏斗数据
export function useDashboardFunnel(trackingId: string | null, options?: { enabled?: boolean }) {
  const on = options?.enabled ?? true;
  return useQuery({
    queryKey: ['tracking', 'dashboard', 'funnel', trackingId],
    queryFn: () => trackingApi.getDashboardFunnel(trackingId!),
    enabled: !!trackingId && on,
  });
}

// 获取团队对比数据
export function useDashboardTeams(trackingId: string | null, options?: { enabled?: boolean }) {
  const on = options?.enabled ?? true;
  return useQuery({
    queryKey: ['tracking', 'dashboard', 'teams', trackingId],
    queryFn: () => trackingApi.getDashboardTeams(trackingId!),
    enabled: !!trackingId && on,
  });
}

// 获取销售排名数据
export function useDashboardRanking(trackingId: string | null, limit = 10, options?: { enabled?: boolean }) {
  const on = options?.enabled ?? true;
  return useQuery({
    queryKey: ['tracking', 'dashboard', 'ranking', trackingId, limit],
    queryFn: () => trackingApi.getDashboardRanking(trackingId!, limit),
    enabled: !!trackingId && on,
  });
}

// 获取看板汇总数据（包含所有图表）
export function useDashboardSummary(trackingId: string | null) {
  return useQuery({
    queryKey: ['tracking', 'dashboard', 'summary', trackingId],
    queryFn: () => trackingApi.getDashboardSummary(trackingId!),
    enabled: !!trackingId,
  });
}

// 获取快照的历史看板数据
export function useSnapshotDashboard(snapshotId: string | null) {
  return useQuery({
    queryKey: ['tracking', 'snapshot', 'dashboard', snapshotId],
    queryFn: () => trackingApi.getSnapshotDashboard(snapshotId!),
    enabled: !!snapshotId,
  });
}

// ============ WebSocket Hooks ============

/**
 * WebSocket 连接 Hook
 * 自动建立和维护 WebSocket 连接
 */
export function useWebSocket(enterpriseId: string | null) {
  const [connected, setConnected] = useState(false);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enterpriseId) {
      wsManager.disconnect();
      setConnected(false);
      return;
    }

    // 建立连接
    wsManager.connect(enterpriseId);

    // 监听连接状态
    const unsubConnection = wsManager.onConnectionChange((isConnected) => {
      setConnected(isConnected);
    });

    // 监听任务状态消息
    const unsubMessage = wsManager.onMessage((message: TaskStatusMessage) => {
      console.log('[WebSocket] Task status:', message);

      // 根据任务类型刷新对应的查询
      if (message.task_type === 'diagnosis') {
        // 仅完成后刷新列表。failed 时不在这里 invalidate，避免先于失败回调触发 refetch，
        // 与「暂停拉数 / 失败定格」竞态；失败后的列表刷新由页面 onFailed 等路径触发。
        if (message.status === 'completed') {
          queryClient.invalidateQueries({
            queryKey: ['diagnosis', 'list', message.enterprise_id],
          });
        }
      } else if (message.task_type === 'solution') {
        if (message.status === 'completed') {
          queryClient.invalidateQueries({ 
            queryKey: ['solutions', 'list'] 
          });
        }
      }
    });

    return () => {
      unsubConnection();
      unsubMessage();
    };
  }, [enterpriseId, queryClient]);

  return { connected };
}

/**
 * 任务状态订阅 Hook
 * 订阅特定类型任务的状态更新
 */
export function useTaskStatus(
  taskType: 'diagnosis' | 'solution' | 'tracking',
  onStatusChange?: (message: TaskStatusMessage) => void
) {
  const [latestStatus, setLatestStatus] = useState<TaskStatusMessage | null>(null);

  useEffect(() => {
    const unsubscribe = wsManager.onMessage((message: TaskStatusMessage) => {
      if (message.task_type === taskType) {
        setLatestStatus(message);
        onStatusChange?.(message);
      }
    });

    return unsubscribe;
  }, [taskType, onStatusChange]);

  return latestStatus;
}

/**
 * 诊断任务状态 Hook
 * 专门用于监听诊断任务的状态
 */
export function useDiagnosisTaskStatus(
  enterpriseId: string | null,
  options?: {
    onStarted?: (taskId: string) => void;
    onProgress?: (taskId: string, progress: number, message: string) => void;
    onCompleted?: (taskId: string, data: Record<string, unknown>) => void;
    onFailed?: (taskId: string, error: string) => void;
    /** 任务被用户取消时（WebSocket 收到 failed + message 已取消）*/
    onCancelled?: (taskId: string) => void;
    /** 采集/诊断过程中部分失败时（level=warning）*/
    onWarning?: (taskId: string, message: string) => void;
  }
) {
  const [tasks, setTasks] = useState<Record<string, TaskStatusMessage>>({});
  const [warnings, setWarnings] = useState<string[]>([]);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  useEffect(() => {
    if (!enterpriseId) return;
    setTasks({}); // 切换企业时清空，避免展示其它企业的任务
    setWarnings([]);

    const unsubscribe = wsManager.onMessage((message: TaskStatusMessage) => {
      if (message.task_type !== 'diagnosis' || message.enterprise_id !== enterpriseId) {
        return;
      }

      setTasks(prev => ({
        ...prev,
        [message.task_id]: message,
      }));

      // 仅展示 warning（部分可恢复问题）。error 级多为致命失败，由最终 failed 态与服务端 message 统一呈现，避免进度区内嵌长技术细节。
      const level = message.data?.level as string | undefined;
      if (level === 'warning') {
        const warnMsg = message.message || '未知警告';
        setWarnings(prev => [...prev, warnMsg]);
        optionsRef.current?.onWarning?.(message.task_id, warnMsg);
      }

      // 调用回调
      switch (message.status) {
        case 'running':
          if (message.progress <= 10) {
            optionsRef.current?.onStarted?.(message.task_id);
          } else {
            optionsRef.current?.onProgress?.(
              message.task_id, 
              message.progress, 
              message.message || ''
            );
          }
          break;
        case 'completed':
          optionsRef.current?.onCompleted?.(
            message.task_id, 
            message.data || {}
          );
          break;
        case 'failed': {
          const err = message.message || '未知错误';
          if (err === '已取消') {
            optionsRef.current?.onCancelled?.(message.task_id);
          }
          optionsRef.current?.onFailed?.(message.task_id, err);
          break;
        }
      }
    });

    return unsubscribe;
  }, [enterpriseId]);

  // 获取正在进行的任务
  const runningTasks = Object.values(tasks).filter(
    t => t.status === 'running' || t.status === 'pending'
  );

  // 获取最新的任务状态
  const latestTask = Object.values(tasks).sort(
    (a, b) => (b.progress || 0) - (a.progress || 0)
  )[0] || null;

  return {
    tasks,
    runningTasks,
    latestTask,
    hasRunningTask: runningTasks.length > 0,
    /** 诊断执行过程中的警告消息列表（如部分数据采集失败）*/
    warnings,
  };
}

// ============ 维度配置 Hooks ============

// 维度配置接口
export interface DimensionConfig {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  icon?: string;
  color?: string;
  weight: number;
  is_system: boolean;
  enabled: boolean;
  metrics_config?: {
    metrics: Array<{
      name: string;
      display_name: string;
      unit: string;
      description?: string;
      benchmark?: { avg: number; excellent: number; median: number };
      direction?: string;
    }>;
  };
  rules_config?: {
    rules: Array<{
      id: string;
      name: string;
      metric: string;
      operator: string;
      threshold: number;
      severity: string;
    }>;
  };
}

export interface AllDimensionsResponse {
  system_dimensions: DimensionConfig[];
  custom_dimensions: DimensionConfig[];
  all_dimensions: DimensionConfig[];
}

/**
 * 获取所有维度配置（系统+自定义）
 * 
 * 提供统一的维度配置访问，包括：
 * - 维度显示名称映射
 * - 维度到第一个指标的映射（用于钻取）
 * - 指标显示名称映射
 * - 所有维度列表
 */
export function useDimensionConfig(enterpriseId: string | null) {
  const { data, isLoading, error, refetch } = useQuery<AllDimensionsResponse>({
    queryKey: ['dimensions', 'all', enterpriseId],
    queryFn: () => customDimensionApi.getAllDimensions(enterpriseId!),
    enabled: !!enterpriseId,
    staleTime: 5 * 60 * 1000, // 5分钟缓存
  });

  // 构建维度显示名称映射 { name -> display_name }
  const dimensionNameMap = useCallback(() => {
    if (!data?.all_dimensions) return {};
    const map: Record<string, string> = {};
    for (const dim of data.all_dimensions) {
      map[dim.name] = dim.display_name;
      // 兼容旧的 key 名称
      if (dim.name === 'crm') {
        map['crm_sharing'] = dim.display_name;
      } else if (dim.name === 'marketing') {
        map['marketing_effect'] = dim.display_name;
      } else if (dim.name === 'retention') {
        map['customer_retention'] = dim.display_name;
      } else if (dim.name === 'efficiency') {
        map['operation_efficiency'] = dim.display_name;
      }
    }
    return map;
  }, [data]);

  // 构建维度到第一个指标的映射（用于钻取）
  const dimensionFirstMetricMap = useCallback(() => {
    if (!data?.all_dimensions) return {};
    const map: Record<string, string> = {};
    for (const dim of data.all_dimensions) {
      const metrics = dim.metrics_config?.metrics || [];
      if (metrics.length > 0) {
        map[dim.name] = metrics[0].name;
      }
    }
    return map;
  }, [data]);

  // 构建指标显示名称映射 { metric_name -> display_name }
  const metricNameMap = useCallback(() => {
    if (!data?.all_dimensions) return {};
    const map: Record<string, string> = {};
    for (const dim of data.all_dimensions) {
      const metrics = dim.metrics_config?.metrics || [];
      for (const metric of metrics) {
        map[metric.name] = metric.display_name;
      }
    }
    return map;
  }, [data]);

  // 获取维度显示名称（带 fallback）
  const getDimensionDisplayName = useCallback((dimensionName: string): string => {
    const map = dimensionNameMap();
    return map[dimensionName] || dimensionName;
  }, [dimensionNameMap]);

  // 获取指标显示名称（带 fallback）
  const getMetricDisplayName = useCallback((metricName: string): string => {
    const map = metricNameMap();
    return map[metricName] || metricName;
  }, [metricNameMap]);

  // 根据维度名称获取维度配置
  const getDimensionByName = useCallback((name: string): DimensionConfig | undefined => {
    return data?.all_dimensions.find(d => d.name === name);
  }, [data]);

  return {
    // 原始数据
    data,
    isLoading,
    error,
    refetch,

    // 维度列表
    allDimensions: data?.all_dimensions || [],
    systemDimensions: data?.system_dimensions || [],
    customDimensions: data?.custom_dimensions || [],

    // 映射
    dimensionNameMap: dimensionNameMap(),
    dimensionFirstMetricMap: dimensionFirstMetricMap(),
    metricNameMap: metricNameMap(),

    // 便捷方法
    getDimensionDisplayName,
    getMetricDisplayName,
    getDimensionByName,
  };
}

// ============ CRM 模块 Hooks ============

import { crmApi, type Lead, type LeadStats, type LeadEventType } from './api';
import { crmWsManager, type CRMWebSocketMessage, type LeadEvent, type AlertEvent } from './crm-websocket';

// 获取线索列表
export function useLeadList(
  enterpriseId: string | null,
  status?: string,
  skip: number = 0,
  limit: number = 50
) {
  return useQuery<{ items: Lead[]; total: number }>({
    queryKey: ['crm', 'leads', enterpriseId, status, skip, limit],
    queryFn: () => crmApi.getLeads({ enterprise_id: enterpriseId!, status, skip, limit }),
    enabled: !!enterpriseId,
    staleTime: 0,
    refetchOnMount: true,
  });
}

// 获取线索统计
export function useLeadStats(enterpriseId: string | null) {
  return useQuery<LeadStats>({
    queryKey: ['crm', 'stats', enterpriseId],
    queryFn: () => crmApi.getLeadStats(enterpriseId!),
    enabled: !!enterpriseId,
    refetchInterval: 30000, // 每30秒刷新一次
  });
}

// 获取线索详情
export function useLeadDetail(enterpriseId: string | null, leadId: string | null) {
  return useQuery<Lead>({
    queryKey: ['crm', 'lead', enterpriseId, leadId],
    queryFn: () => crmApi.getLead(enterpriseId!, leadId!),
    enabled: !!enterpriseId && !!leadId,
  });
}

// 分配线索
export function useAssignLead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ enterpriseId, leadId, salesUserId }: {
      enterpriseId: string;
      leadId: string;
      salesUserId?: string;
    }) => crmApi.assignLead(enterpriseId, leadId, salesUserId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'leads'] });
      queryClient.invalidateQueries({ queryKey: ['crm', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['crm', 'lead', variables.enterpriseId, variables.leadId] });
    },
  });
}

// 获取事件列表
export function useLeadEvents(
  enterpriseId: string | null,
  limit: number = 50,
  eventType?: LeadEventType
) {
  return useQuery({
    queryKey: ['crm', 'events', enterpriseId, limit, eventType],
    queryFn: () => crmApi.getEvents({ enterprise_id: enterpriseId!, limit, event_type: eventType }),
    enabled: !!enterpriseId,
    staleTime: 0,
  });
}

// CRM WebSocket 连接 Hook
export function useCRMWebSocket(
  enterpriseId: string | null,
  options?: {
    onLeadCreated?: (event: LeadEvent) => void;
    onLeadAssigned?: (event: LeadEvent) => void;
    onLeadConverted?: (event: LeadEvent) => void;
    onLeadLost?: (event: LeadEvent) => void;
    onAlert?: (event: AlertEvent) => void;
    onStatusUpdate?: (message: CRMWebSocketMessage) => void;
  }
) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<CRMWebSocketMessage | null>(null);
  const optionsRef = useRef(options);

  // 使用 ref 存储 options 避免 useEffect 重复执行
  useEffect(() => {
    optionsRef.current = options;
  });

  useEffect(() => {
    if (!enterpriseId) {
      setConnected(false);
      return;
    }

    // 连接 WebSocket
    crmWsManager.connect(enterpriseId);

    // 注册连接状态处理器
    const unsubscribeConnection = crmWsManager.onConnectionChange((isConnected) => {
      setConnected(isConnected);
    });

    // 注册消息处理器
    const unsubscribeMessage = crmWsManager.onMessage((message) => {
      setLastMessage(message);

      // 根据事件类型调用对应的回调
      if (message.type === 'lead_event') {
        const event = message as LeadEvent;
        switch (event.event_type) {
          case 'lead.created':
            optionsRef.current?.onLeadCreated?.(event);
            break;
          case 'lead.assigned':
            optionsRef.current?.onLeadAssigned?.(event);
            break;
          case 'lead.converted':
            optionsRef.current?.onLeadConverted?.(event);
            break;
          case 'lead.lost':
            optionsRef.current?.onLeadLost?.(event);
            break;
          default:
            // 预警事件
            if (event.event_type.includes('timeout') ||
                event.event_type.includes('overdue') ||
                event.event_type.includes('risk')) {
              optionsRef.current?.onAlert?.(event as unknown as AlertEvent);
            }
            break;
        }
      } else if (message.type === 'lead_status_update') {
        optionsRef.current?.onStatusUpdate?.(message);
      }
    });

    return () => {
      unsubscribeConnection();
      unsubscribeMessage();
      crmWsManager.disconnect();
    };
  }, [enterpriseId]); // 只依赖 enterpriseId

  return { connected, lastMessage };
}
