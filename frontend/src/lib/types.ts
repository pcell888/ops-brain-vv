// ============ 诊断模块类型 ============

export interface DiagnosisStatusResponse {
  diagnosis_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message?: string;
  health_score?: number;
}

// 指标明细
export interface MetricDetail {
  name: string;
  display_name: string;
  value: number;
  unit: string;
  score: number;
  benchmark_avg: number;
  benchmark_excellent: number;
}

export interface DimensionScore {
  dimension: string;
  score: number;
  weight: number;
  weighted_score: number;
  status: string;
  metrics_detail?: MetricDetail[];  // 指标明细
}

export interface HealthScore {
  total_score: number;
  status: string;
  dimension_scores: DimensionScore[];
  trend: {
    previous_score?: number;
    change?: number;
    direction?: 'up' | 'down' | 'stable';
  };
}

export interface Anomaly {
  id: string;
  rule_id: string;
  rule_name: string;
  metric_name: string;
  dimension: string;
  current_value: number;
  benchmark_value?: number;
  gap_percentage?: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  root_cause_chain: string[];
  solution_tags: string[];
  unit?: string;
}

export interface RootCauseAnalysis {
  metric_name: string;
  cause_chain: Array<{
    step: number;
    description: string;
    is_root: boolean;
  }>;
  explanation: string;
  recommendations: string[];
}

export interface DiagnosisReport {
  diagnosis_id: string;
  enterprise_id: string;
  status: string;
  health_score: HealthScore;
  anomalies: Anomaly[];
  root_cause_analyses: RootCauseAnalysis[];
  created_at: string;
  completed_at?: string;
}

export interface DiagnosisListItem {
  diagnosis_id: string;
  status: string;
  progress?: number;
  message?: string;
  error_message?: string;
  health_score?: number;
  anomaly_count?: number;
  trigger_type: string;
  created_at: string;
}

export interface DiagnosisListResponse {
  items: DiagnosisListItem[];
  total: number;
}

// ============ 方案模块类型 ============

export interface SolutionTask {
  id: string;
  task_id: string;
  name: string;
  description: string;
  duration_days: number;
  execution_type: string;
  dependencies: string[];
  start_offset: number;
  end_offset: number;
}

export interface SolutionSummary {
  rank: number;
  solution_id: string;
  name: string;
  score: number;
  recommendation_reason: string;
  estimated_cost: number;
  estimated_duration: number;
  success_rate: number;
  anomaly_ids?: string[];  // 关联的异常 ID 列表
  status?: string;  // 方案状态：'adopted' | 'rejected' | 'pending' 等
  execution_plan?: ExecutionPlanInfo | null;  // 执行计划信息
}

/** 后端返回的 AI 智能建议（红框文案） */
export interface AIRecommendation {
  recommended_solution_id: string;
  reason: string;
  comparison_summary: string;
  risk_warning?: string;
}

export interface SolutionGenerateResponse {
  enterprise_id?: string;
  diagnosis_id: string;
  solution_count?: number;
  total?: number;
  solutions: SolutionSummary[];
  generated_at?: string;
  /** 后端拼接的 AI 智能建议，列表接口返回 */
  ai_recommendation?: AIRecommendation | null;
}

export interface RelatedAnomaly {
  id: string;
  rule_name: string;
  metric_name: string;
  dimension: string;
  current_value: number;
  benchmark_value?: number;
  gap_percentage?: number;
  severity: string;
  solution_tags: string[];
}

export interface ExecutionPlanInfo {
  plan_id: string;
  status: string;
  progress: number;
  created_at: string;
}

export interface SolutionDetail {
  id: string;
  name: string;
  description: string;
  category: string;
  executive_summary: string;
  problem_statement: string;
  solution_overview: string;
  expected_outcomes: string;
  implementation_roadmap: string;
  risk_assessment: string;
  success_criteria: string;
  estimated_impact: Record<string, number>;
  estimated_cost: number;
  estimated_duration: number;
  success_rate: number;
  ranking_score: number;
  ranking_reason: string;
  status: string;
  related_anomalies?: RelatedAnomaly[];  // 新增: 关联的异常指标
  tasks: SolutionTask[];
  execution_plan?: ExecutionPlanInfo | null;  // 执行计划信息
  created_at: string;
}

export interface TemplateTask {
  task_id: string;
  name: string;
  description: string;
  duration_days: number;
  execution_type: string;
  dependencies: string[];
}

export interface SolutionTemplate {
  template_id: string;
  name: string;
  description: string;
  category: string;
  applicable_tags: string[];
  estimated_impact: Record<string, number>;
  estimated_cost: number;
  estimated_duration_days: number;
  success_rate: number;
  task_count: number;
  tasks?: TemplateTask[];
}

// 模板详情（包含额外字段）
export interface SolutionTemplateDetail extends SolutionTemplate {
  implementation_guide?: string;
  prerequisites?: string[];
  industry_scope?: string[];
}

export interface SolutionTemplatesResponse {
  templates: SolutionTemplate[];
  total: number;
}

export interface ExecutionPlanListResponse {
  items: ExecutionPlanSummary[];
  total: number;
}

export interface TrackingListResponse {
  items: TrackingSummary[];
  total: number;
}

// ============ 执行模块类型 ============

export interface TaskStats {
  pending: number;
  ready: number;
  running: number;
  paused: number;
  completed: number;
  failed: number;
  cancelled: number;
}

export interface ExecutionPlanSummary {
  plan_id: string;
  solution_id: string;
  template_id?: string;
  name: string;
  status: string;
  progress: number;
  task_stats: TaskStats;
  planned_start: string;
  planned_end: string;
  actual_start?: string;
  actual_end?: string;
  tracking_id?: string;
}

export interface ExecutionTask {
  id: string;
  task_key?: string;
  name: string;
  description?: string;
  status: string;
  execution_type: string;
  dependencies?: string[];
  scheduled_start?: string;
  scheduled_end?: string;
  actual_start?: string;
  actual_end?: string;
  retry_count?: number;
  error_message?: string;
  result?: any;
  progress: number;
  assigned_to?: string;
}

export interface GanttTask {
  id: string;
  name: string;
  start: string;
  end: string;
  progress: number;
  dependencies: string[];
  status: string;
}

export interface GanttData {
  plan_id: string;
  tasks: GanttTask[];
  milestones: Array<{
    id: string;
    name: string;
    date: string;
  }>;
}

// ============ 追踪模块类型 ============

export interface TrackingSummary {
  tracking_id: string;
  plan_id: string;
  solution_name: string;
  status: string;
  current_score?: number;
  snapshot_count: number;
  started_at: string;
  last_snapshot_at?: string;
  completed_at?: string;
}

export interface MetricTrend {
  metric_name: string;
  values: Array<{
    date: string;
    value: number;
  }>;
  improvement: number;
}

export interface ReviewReport {
  tracking_id: string;
  summary: string;
  achievements: string[];
  challenges: string[];
  lessons_learned: string[];
  recommendations: string[];
  overall_score: number;
}

export interface CaseSummary {
  id: string;
  title: string;
  industry: string;
  problem_type: string;
  solution_summary: string;
  improvement_score: number;
  created_at: string;
}

// ============ 钻取数据类型 ============

export interface DrillDownDataPoint {
  date: string;
  value: number;
  sub_dimension?: string;
  breakdown?: Record<string, number>;
}

export interface DrillDownResponse {
  metric_name: string;
  dimension: string;
  time_range: {
    start: string;
    end: string;
  };
  data: DrillDownDataPoint[];
}

// ============ 通用类型 ============

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

