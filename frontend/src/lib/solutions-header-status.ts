import type { AdoptProgressResponse } from '@/lib/api';

/** 采纳失败时标题区单行文案：「采纳失败，[原因]」 */
export function formatAdoptFailureLine(reason?: string | null): string {
  const r = (reason ?? '').trim();
  if (!r) return '采纳失败';
  if (r.startsWith('采纳失败')) return r;
  return `采纳失败，${r}`;
}

/** 优化方案列表页：标题下常驻一句（采纳轮询走 transient，与此并存） */
export function formatSolutionsListPersistent(params: {
  selectedDiagnosisId: string | null;
  isCompleted: boolean;
  isLoading: boolean;
  generating?: boolean;
  solutionCount: number;
  anyAdopted: boolean;
  /** 已采纳方案的展示名称（与 anyAdopted 同时为真时使用） */
  adoptedPlanName?: string | null;
}): string | null {
  if (!params.selectedDiagnosisId) return null;
  if (!params.isCompleted) return '诊断未完成，完成后可查看';
  if (params.generating) return '方案生成中…';
  if (params.isLoading) return null;

  const n = params.solutionCount;
  if (params.anyAdopted) {
    const name = (params.adoptedPlanName ?? '').trim();
    if (name) {
      return `已采纳方案「${name}」，请在「任务执行」页面中查看详情`;
    }
    return '已有方案已采纳，请在「任务执行」页面中查看详情';
  }
  return `已生成 ${n} 条方案，请「采纳」并派发任务`;
}

/** 方案详情页：采纳前常驻语境（采纳中/失败/完成由 transient 展示） */
export function formatSolutionDetailPersistent(params: {
  selectedSolutionId: string | null;
  selectedStatus?: string;
  solutionCount: number;
  anySolutionAdopted: boolean;
}): string | null {
  if (params.solutionCount <= 0) return null;
  if (!params.selectedSolutionId) return `已生成 ${params.solutionCount} 条，请选择方案`;
  if (params.selectedStatus === 'adopted') return '本方案已采纳，执行见「任务执行」';
  if (params.anySolutionAdopted && params.selectedStatus !== 'adopted') return '已有其它方案被采纳';
  return '方案已生成，请选择「采纳」方案，推送派发任务';
}

/** adopt/progress 的 last_timestamp 格式化为本地可读时间 */
export function formatAdoptProgressTimeZh(iso: string | null | undefined): string | null {
  if (iso == null || typeof iso !== 'string') return null;
  const t = iso.trim();
  if (!t) return null;
  const d = new Date(t);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * 采纳完成瞬态：用 progress 载荷中的 adopted 与时间戳拼一句（不新增列表接口字段）。
 */
export function formatAdoptCompletedTransientLine(
  data: AdoptProgressResponse,
  planDisplayName?: string | null,
): string {
  const adoptedId =
    (Array.isArray(data.adopted_plan_ids) && data.adopted_plan_ids[0]) ||
    (typeof data.solution_id === 'string' ? data.solution_id.trim() : '') ||
    '';
  const name = (planDisplayName ?? '').trim();
  const who = name ? `「${name}」` : adoptedId ? `方案 ${adoptedId}` : '方案';
  const when = formatAdoptProgressTimeZh(data.last_timestamp);
  const backend = (data.message || '').trim();
  let line = `已采纳 ${who}`;
  if (when) line += `，完成于 ${when}`;
  if (backend && !line.includes(backend)) {
    line += ` · ${backend}`;
  }
  return line;
}
