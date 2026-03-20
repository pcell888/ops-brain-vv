import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig } from 'axios';

/**
 * 说明：
 * - 我们在响应拦截器里 `return response.data`，所以运行时 `api.get/post/...` 返回的是“业务数据”，不是 AxiosResponse。
 * - 但 axios 的默认 TS 签名仍会把它推断成 AxiosResponse，导致全站出现 “Property 'x' does not exist on type 'AxiosResponse'”。
 * - 这里用一个窄化后的 AxiosInstance 类型，把 get/post/... 的返回值标注为 Promise<T>（即 data），与运行时一致。
 */
type DataAxiosInstance = Omit<
  AxiosInstance,
  'get' | 'delete' | 'post' | 'put' | 'patch'
> & {
  get<T = any, D = any>(url: string, config?: AxiosRequestConfig<D>): Promise<T>;
  delete<T = any, D = any>(url: string, config?: AxiosRequestConfig<D>): Promise<T>;
  post<T = any, D = any>(url: string, data?: D, config?: AxiosRequestConfig<D>): Promise<T>;
  put<T = any, D = any>(url: string, data?: D, config?: AxiosRequestConfig<D>): Promise<T>;
  patch<T = any, D = any>(url: string, data?: D, config?: AxiosRequestConfig<D>): Promise<T>;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
}) as DataAxiosInstance;

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 添加企业ID
    const enterpriseId = typeof window !== 'undefined' ? localStorage.getItem('enterpriseId') : null;
    if (enterpriseId) {
      config.headers['X-Enterprise-ID'] = enterpriseId;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response;
      
      if (status === 401) {
        // 未认证，跳转登录
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
      }
      
      return Promise.reject(new Error(data?.message || data?.detail || '请求失败'));
    }
    
    return Promise.reject(error);
  }
);

export default api;

// ============ 企业模块 API ============
export type EnterpriseConfig = {
  analysis_period_days?: number;
  auto_diagnosis_frequency?: string;
  industry_benchmark?: string;
  solution_sort_strategy?: string;
  max_solutions?: number;
};

export type EnterpriseContext = {
  industry?: string;
  scale?: string;
  team_size?: number;
  budget_level?: string;
  data_quality?: number;
};

export type DataQualityReport = {
  score: number;
  metric_coverage: number;
  connectivity: number;
  validity: number;
  freshness: number;
  dimensions: {
    dimension: string;
    connected: boolean;
    supported_count: number;
    fetched_count: number;
    non_zero_count: number;
    latest_at: string | null;
  }[];
  evaluated_at: string;
};

export const enterpriseApi = {
  list: () => api.get('/enterprises'),
  get: (enterpriseId: string) => api.get(`/enterprises/${enterpriseId}`),
  updateConfig: (enterpriseId: string, config: EnterpriseConfig) =>
    api.patch(`/enterprises/${enterpriseId}/config`, config),
  updateContext: (enterpriseId: string, context: EnterpriseContext) =>
    api.patch(`/enterprises/${enterpriseId}/context`, context),
  evaluateDataQuality: (enterpriseId: string) =>
    api.post<DataQualityReport>(`/enterprises/${enterpriseId}/data-quality`),
  getBenchmarks: (enterpriseId: string) =>
    api.get(`/enterprises/${enterpriseId}/benchmarks`),
};

// ============ 行业基准维护 API（系统设置 Tab） ============
export type IndustryBenchmarkItem = {
  id: string;
  industry: string;
  metric_name: string;
  /** 指标中文名（来自维度配置，列表接口返回） */
  metric_display_name?: string;
  avg_value: number | null;
  median_value: number | null;
  excellent_value: number | null;
  sample_size: number | null;
  period: string;
  source: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type IndustryBenchmarkCreateBody = {
  industry: string;
  metric_name: string;
  metric_display_name?: string;
  period: string;
  avg_value?: number;
  median_value?: number;
  excellent_value?: number;
  sample_size?: number;
  source?: string;
};

export type IndustryBenchmarkUpdateBody = Partial<IndustryBenchmarkCreateBody>;

export const industryBenchmarkApi = {
  list: (industry?: string) =>
    api.get<{ items: IndustryBenchmarkItem[]; total: number }>(
      '/enterprises/industry-benchmarks',
      { params: industry ? { industry } : {} }
    ),
  create: (body: IndustryBenchmarkCreateBody) =>
    api.post<IndustryBenchmarkItem>('/enterprises/industry-benchmarks', body),
  get: (id: string) =>
    api.get<IndustryBenchmarkItem>(`/enterprises/industry-benchmarks/${id}`),
  update: (id: string, body: IndustryBenchmarkUpdateBody) =>
    api.put<IndustryBenchmarkItem>(`/enterprises/industry-benchmarks/${id}`, body),
  delete: (id: string) =>
    api.delete<{ ok: boolean }>(`/enterprises/industry-benchmarks/${id}`),
};
export const diagnosisApi = {
  // 启动诊断（映射 enterprise_id → tenant_id/store_id）
  start: (data: { 
    enterprise_id: string; 
    trigger_type?: string;
    dimensions?: string[];
    async_mode?: boolean;
    store_id?: string;
  }) => api.post('/diagnosis/start', {
    tenant_id: data.enterprise_id,
    store_id: data.store_id || '',
    trigger_type: data.trigger_type || 'manual',
    selected_dimensions: data.dimensions || null,
  }).then((res: any) => ({
    ...res,
    diagnosis_id: res.thread_id,
    status: 'running',
  })),
  
  // 获取诊断状态
  getStatus: (diagnosisId: string) =>
    api.get(`/diagnosis/status/${diagnosisId}`),

  // 取消诊断（仅 pending/running 可取消），短超时避免挂起，最终状态由 WebSocket 推送
  cancel: (diagnosisId: string) =>
    api.post(`/diagnosis/${diagnosisId}/cancel`, undefined, { timeout: 8000 }),
  
  // 获取诊断报告
  getReport: (diagnosisId: string) =>
    api.get(`/diagnosis/report/${diagnosisId}`),
  
  // 获取单个异常指标详情
  getAnomalyDetail: (diagnosisId: string, anomalyId: string) =>
    api.get(`/diagnosis/anomaly/${diagnosisId}/${anomalyId}`),
  
  // 获取诊断历史列表
  list: (params: { enterprise_id: string; skip?: number; limit?: number }) =>
    api.get('/diagnosis/list', { params }),
  
  // 获取行业基准数据（指标级）
  getBenchmarks: (industry?: string) =>
    api.get('/diagnosis/benchmarks', { params: { industry } }),

  // 获取行业基准的维度得分（用于仪表盘雷达图「我的企业 vs 行业基准」）
  getBenchmarkDimensionScores: (industry?: string) =>
    api.get<{ industry: string; dimension_scores: { dimension: string; score: number }[] }>(
      '/diagnosis/benchmarks/dimension-scores',
      { params: { industry } }
    ),
  
  // 指标钻取
  drillDown: (metricName: string, params: { 
    enterprise_id: string; 
    dimension: string; 
    days?: number;
    page?: number;
    page_size?: number;
  }) => api.get(`/diagnosis/drill-down/${metricName}`, { params }),
};

// ============ 自定义维度 API ============
export interface MetricConfig {
  name: string;
  display_name: string;
  unit: string;
  description?: string;
  data_source: 'api' | 'manual' | 'formula';
  api_endpoint?: string;
  formula?: string;
  benchmark: { avg: number; excellent: number; median: number };
}

export interface RuleConfig {
  id: string;
  name: string;
  metric: string;
  operator: 'lt' | 'gt' | 'eq' | 'le' | 'ge' | 'ne' | 'between';
  threshold: number;
  threshold_high?: number;
  severity: 'critical' | 'warning' | 'info';
  root_cause_chain: string[];
  solution_tags: string[];
}

export interface TaskConfig {
  task_id: string;
  name: string;
  description?: string;
  execution_type: 'auto' | 'semi_auto' | 'manual' | 'custom_api' | 'custom_script';
  duration_days: number;
  dependencies?: string[];
  trigger_rules?: string[];
  config?: {
    api_url?: string;
    method?: string;
    headers?: string | Record<string, any>;
    body?: string | Record<string, any>;
    timeout?: number;
    retry_count?: number;
    expected_status?: number;
    script_type?: string;
    script_content?: string;
    script_path?: string;
    args?: string[];
    env?: Record<string, any>;
    working_dir?: string;
  };
}

export interface CustomDimensionData {
  name: string;
  display_name: string;
  description?: string;
  icon?: string;
  color?: string;
  weight: number;
  metrics: MetricConfig[];
  rules?: RuleConfig[];
  tasks?: TaskConfig[];
  enabled?: boolean;
}

export interface CustomDimension extends CustomDimensionData {
  id: string;
  enterprise_id: string;
  metrics_config: { metrics: MetricConfig[] };
  rules_config?: { rules: RuleConfig[] };
  tasks_config?: { tasks: TaskConfig[] };
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export const customDimensionApi = {
  // 创建自定义维度
  create: (enterpriseId: string, data: CustomDimensionData) =>
    api.post('/custom-dimensions', data, { params: { enterprise_id: enterpriseId } }),
  
  // 获取自定义维度列表
  list: (enterpriseId: string, params?: { enabled_only?: boolean; include_system?: boolean }) =>
    api.get('/custom-dimensions', { params: { enterprise_id: enterpriseId, ...params } }),
  
  // 获取所有可用维度（系统+自定义）
  getAllDimensions: (enterpriseId: string) =>
    api.get('/custom-dimensions/all-dimensions', { params: { enterprise_id: enterpriseId } }),
  
  // 获取单个维度详情
  get: (dimensionId: string) =>
    api.get(`/custom-dimensions/${dimensionId}`),
  
  // 更新维度
  update: (dimensionId: string, data: Partial<CustomDimensionData>) =>
    api.put(`/custom-dimensions/${dimensionId}`, data),
  
  // 删除维度
  delete: (dimensionId: string) =>
    api.delete(`/custom-dimensions/${dimensionId}`),
  
  // 切换启用状态
  toggle: (dimensionId: string) =>
    api.post(`/custom-dimensions/${dimensionId}/toggle`),
  
  // 提交指标数据
  submitMetrics: (dimensionId: string, enterpriseId: string, metrics: { metric_name: string; value: number }[]) =>
    api.post(`/custom-dimensions/${dimensionId}/metrics`, metrics, { params: { enterprise_id: enterpriseId } }),

  // 智能生成诊断规则
  generateRules: (data: { dimension_name: string; dimension_display_name: string; metrics: any[] }) =>
    api.post('/custom-dimensions/generate-rules', data),
};

// ============ 方案模块 API ============
export const solutionApi = {
  // 生成优化方案
  generate: (data: { 
    enterprise_id: string;
    diagnosis_id: string;
    anomaly_ids?: string[];
    ranking_strategy?: string;
    budget_limit?: number;
    duration_limit?: number;
  }) => api.post<{ task_id: string; status: string }>('/solutions/generate', data),
  
  // 查询方案生成任务状态
  getGenerationStatus: (taskId: string) =>
    api.get<{
      task_id: string;
      status: 'pending' | 'running' | 'completed' | 'failed';
      progress_step?: number; // 0: 正在分析异常指标, 1: 正在匹配解决方案库, 2: 正在生成优化方案, 3: 正在评估方案可行性, 4: 完成
      result?: Record<string, unknown>;
      error?: string;
    }>(`/solutions/generate/status/${taskId}`),
  
  // 查询指定诊断是否有活跃的生成任务
  getActiveGeneration: (diagnosisId: string) =>
    api.get<{
      task: {
        task_id: string;
        status: 'pending' | 'running';
        diagnosis_id: string;
        progress_step?: number;
      } | null;
    }>(`/solutions/generate/active/${diagnosisId}`),
  
  // 获取诊断对应的方案列表
  list: (diagnosisId: string) =>
    api.get(`/solutions/list/${diagnosisId}`),
  
  // 获取方案详情
  getDetail: (solutionId: string) =>
    api.get(`/solutions/detail/${solutionId}`),
  
  // 对比方案
  compare: (solutionIds: string[]) =>
    api.post('/solutions/compare', solutionIds),
  
  // 获取方案模板列表
  getTemplates: (category?: string, skip?: number, limit?: number) =>
    api.get('/solutions/templates', { params: { category, skip, limit } }),
  
  // 获取单个模板详情
  getTemplateDetail: (templateId: string) =>
    api.get(`/solutions/templates/${templateId}`),
  
  // 采纳方案
  adopt: (solutionId: string) =>
    api.put(`/solutions/${solutionId}/adopt`),
  
  // 拒绝方案
  reject: (solutionId: string, reason?: string) =>
    api.put(`/solutions/${solutionId}/reject`, null, { params: { reason } }),
};

// ============ 执行模块 API ============
export const executionApi = {
  // 创建执行计划
  createPlan: (data: { 
    enterprise_id: string;
    solution_id: string;
    start_date: string;
    scheduling_policy?: string;
  }) => api.post('/execution/plans', data),
  
  // 获取执行计划列表
  listPlans: (params: { 
    enterprise_id: string; 
    status?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/execution/plans', { params }),
  
  // 获取计划摘要
  getPlanSummary: (planId: string) =>
    api.get(`/execution/plans/${planId}`),
  
  // 获取计划甘特图数据
  getPlanGantt: (planId: string) =>
    api.get(`/execution/plans/${planId}/gantt`),
  
  // 启动执行计划
  startPlan: (planId: string) =>
    api.post(`/execution/plans/${planId}/start`),
  
  // 暂停执行计划
  pausePlan: (planId: string) =>
    api.post(`/execution/plans/${planId}/pause`),
  
  // 恢复执行计划
  resumePlan: (planId: string) =>
    api.post(`/execution/plans/${planId}/resume`),
  
  // 获取计划下的任务列表
  listPlanTasks: (planId: string, status?: string) =>
    api.get(`/execution/plans/${planId}/tasks`, { params: { status } }),
  
  // 获取任务详情
  getTaskDetail: (taskId: string) =>
    api.get(`/execution/tasks/${taskId}`),
  
  // 完成任务
  completeTask: (taskId: string, resultData?: Record<string, unknown>) =>
    api.post(`/execution/tasks/${taskId}/complete`, { result_data: resultData }),
  
  // 任务失败
  failTask: (taskId: string, errorMessage: string) =>
    api.post(`/execution/tasks/${taskId}/fail`, { error_message: errorMessage }),
  
  // 重试任务
  retryTask: (taskId: string) =>
    api.post(`/execution/tasks/${taskId}/retry`),
};

// ============ 追踪模块 API ============
export const trackingApi = {
  // 启动效果追踪
  start: (data: { enterprise_id: string; plan_id: string; tracking_interval_days?: number }) =>
    api.post('/tracking/start', data),
  
  // 获取追踪列表
  list: (params: { 
    enterprise_id: string; 
    status?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/tracking/list', { params }),
  
  // 获取追踪摘要
  getSummary: (trackingId: string) =>
    api.get(`/tracking/${trackingId}`),
  
  // 采集周期性快照
  takeSnapshot: (trackingId: string) =>
    api.post(`/tracking/${trackingId}/snapshot`),
  
  // 分析效果
  analyze: (trackingId: string) =>
    api.get(`/tracking/${trackingId}/analyze`),
  
  // 完成追踪，生成复盘报告
  complete: (trackingId: string) =>
    api.post(`/tracking/${trackingId}/complete`),
  
  // 取消/停止追踪
  cancel: (trackingId: string) =>
    api.post(`/tracking/${trackingId}/cancel`),
  
  // 获取指标趋势
  getTrends: (trackingId: string) =>
    api.get(`/tracking/${trackingId}/trends`),
  
  // 获取复盘报告
  getReport: (trackingId: string) =>
    api.get(`/tracking/${trackingId}/report`),
  
  // 获取快照列表
  getSnapshots: (trackingId: string) =>
    api.get(`/tracking/${trackingId}/snapshots`),
  
  // 搜索案例
  searchCases: (params: { 
    industry?: string; 
    problem_type?: string;
    min_score?: number;
    skip?: number;
    limit?: number;
  }) => api.get('/tracking/cases/search', { params }),
  
  // 获取案例详情
  getCaseDetail: (caseId: string) =>
    api.get(`/tracking/cases/${caseId}`),
  
  // 获取相似案例
  getSimilarCases: (params: {
    problem_type: string;
    industry?: string;
    limit?: number;
  }) => api.get('/tracking/cases/similar', { params }),
  
  // ============ 看板图表数据 API ============
  
  // 获取转化漏斗数据
  getDashboardFunnel: (trackingId: string) =>
    api.get(`/tracking/${trackingId}/dashboard/funnel`),
  
  // 获取团队对比数据
  getDashboardTeams: (trackingId: string) =>
    api.get(`/tracking/${trackingId}/dashboard/teams`),
  
  // 获取销售排名数据
  getDashboardRanking: (trackingId: string, limit?: number) =>
    api.get(`/tracking/${trackingId}/dashboard/ranking`, { params: { limit } }),
  
  // 获取看板汇总数据（包含所有图表）
  getDashboardSummary: (trackingId: string) =>
    api.get(`/tracking/${trackingId}/dashboard/summary`),
  
  // 获取快照的历史看板数据
  getSnapshotDashboard: (snapshotId: string) =>
    api.get(`/tracking/snapshots/${snapshotId}/dashboard`),
};

// ============ CRM 模块 API ============
export type LeadStatus = 'created' | 'assigned' | 'contacted' | 'qualified' | 'negotiating' | 'converted' | 'lost' | 'other';

export interface Lead {
  id: string;
  crm_lead_id: string;
  lead_name: string;
  status: LeadStatus;
  lead_phone?: string;
  lead_email?: string;
  company_name?: string;
  source?: string;
  assigned_to?: string;
  assigned_at?: string;
  converted_at?: string;
  lost_at?: string;
  lost_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface LeadListParams {
  enterprise_id: string;
  status?: string;
  limit?: number;
  skip?: number;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
}

export interface LeadStats {
  total: number;
  today: number;
  created: number;
  assigned: number;
  contacted: number;
  converted: number;
  lost: number;
}

export type LeadEventType =
  | 'lead.created'
  | 'lead.assigned'
  | 'lead.converted'
  | 'lead.lost'
  | 'alert.triggered'
  | 'response_timeout'
  | 'follow_up_overdue'
  | 'roi_low'
  | 'budget_exhausted'
  | 'churn_risk_high'
  | 'task_overdue'
  | 'sync.completed'
  | 'rule.created'
  | 'workflow.created';

export interface LeadEvent {
  id: string;
  enterprise_id: string;
  lead_id?: string;
  crm_lead_id: string;
  event_type: LeadEventType;
  event_data: Record<string, unknown>;
  source_system: string;
  webhook_timestamp?: string;
  processed: number;
  received_at: string;
  created_at: string;
}

export interface AlertEvent {
  id: string;
  event_type: LeadEventType;
  crm_lead_id: string;
  lead_name?: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  created_at: string;
}

export const crmApi = {
  /**
   * 获取线索列表
   */
  getLeads: (params: LeadListParams) =>
    api.get<LeadListResponse>('/crm/leads', { params }),

  /**
   * 获取线索详情
   */
  getLead: (enterpriseId: string, leadId: string) =>
    api.get<Lead>(`/crm/leads/${leadId}`, { params: { enterprise_id: enterpriseId } }),

  /**
   * 获取线索统计
   */
  getLeadStats: (enterpriseId: string) =>
    api.get<LeadStats>(`/crm/leads/stats`, { params: { enterprise_id: enterpriseId } }),

  /**
   * 分配线索
   */
  assignLead: (enterpriseId: string, leadId: string, salesUserId?: string) =>
    api.post<Lead>(`/crm/leads/${leadId}/assign`, null, {
      params: { enterprise_id: enterpriseId, ...(salesUserId && { sales_user_id: salesUserId }) }
    }),

  /**
   * 获取事件列表
   */
  getEvents: (params: {
    enterprise_id: string;
    limit?: number;
    event_type?: LeadEventType;
  }) => api.get<LeadEvent[]>('/crm/events', { params }),
};
