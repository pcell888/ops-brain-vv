/** 优化方案列表页：标题下常驻一句（采纳轮询走 transient，与此并存） */
export function formatSolutionsListPersistent(params: {
  selectedDiagnosisId: string | null;
  isCompleted: boolean;
  isLoading: boolean;
  generating?: boolean;
  solutionCount: number;
  anyAdopted: boolean;
}): string | null {
  if (!params.selectedDiagnosisId) return null;
  if (!params.isCompleted) return '诊断未完成，完成后可查看';
  if (params.generating) return '方案生成中…';
  if (params.isLoading) return null;

  const n = params.solutionCount;
  let line = `已生成 ${n} 条方案，请「采纳」并派发任务`;
  if (params.anyAdopted) line += ' · 已有采纳见「任务执行」';
  return line;
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
  return '请「采纳」并派发任务';
}
