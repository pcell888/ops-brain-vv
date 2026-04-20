import dayjs from 'dayjs';

export type TrackingSummaryLike = {
  status: string;
  snapshot_count?: number;
  review_due_date?: string;
  started_at?: string;
  completed_at?: string | null;
  total_duration_days?: number;
};

function elapsedDays(startedAt?: string, endedAt?: string | null): number {
  if (!startedAt) return 0;
  const start = dayjs(startedAt);
  const end = endedAt ? dayjs(endedAt) : dayjs();
  return Math.max(0, end.diff(start, 'day'));
}

/** 展示用预计时刻：后端 active 摘要会带 review_due_date；旧数据仅前端回退推算 */
function resolveExpectedAutoCompleteAt(s: TrackingSummaryLike): string {
  if (s.review_due_date) {
    return dayjs(s.review_due_date).format('YYYY-MM-DD HH:mm');
  }
  const td = Number(s.total_duration_days);
  if (s.started_at && Number.isFinite(td) && td > 0) {
    return dayjs(s.started_at).add(Math.round(td), 'day').format('YYYY-MM-DD HH:mm');
  }
  return dayjs(s.started_at || undefined)
    .add(7, 'day')
    .format('YYYY-MM-DD HH:mm');
}

/** 效果追踪详情页：副标题下常驻一句（不含轮询临时文案） */
export function formatDetailPersistentStatus(params: {
  hasNoData: boolean;
  summary: TrackingSummaryLike | null | undefined;
  snapshotItemsLength: number;
}): string | null {
  if (params.hasNoData || !params.summary) return null;
  const s = params.summary;
  const snap = Math.max(Number(s.snapshot_count ?? 0), params.snapshotItemsLength);
  const usedDays = elapsedDays(s.started_at, s.completed_at);

  if (s.status === 'active') {
    const expectedAt = resolveExpectedAutoCompleteAt(s);
    return `已追踪「${usedDays}」天，采集快照「${snap}」次，系统预计在「${expectedAt}」自动完成追踪`;
  }

  if (s.status === 'scheduled') {
    const bits: string[] = ['待自动复盘'];
    if (s.review_due_date) {
      bits.push(`预计 ${dayjs(s.review_due_date).format('YYYY-MM-DD')}`);
    }
    bits.push('可「完成追踪」立即开始');
    return bits.join(' · ');
  }

  if (s.status === 'completed') {
    return '追踪已结束，复盘报告已生成';
  }

  if (s.status === 'paused') return '已暂停';
  if (s.status === 'cancelled') return '已取消';

  return `状态：${s.status}`;
}

/** 效果追踪列表页：副标题下常驻一句 */
export function formatListPersistentStatus(params: {
  selectedDiagnosisId: string | null;
  isLoading: boolean;
  trackingStatusText: string;
  totalTracking: number;
  snapshotTotal: number;
}): string | null {
  if (!params.selectedDiagnosisId) {
    return '请选择历史诊断。';
  }
  if (params.isLoading) return null;
  const bits: string[] = [params.trackingStatusText, `${params.totalTracking} 条追踪`, `快照 ${params.snapshotTotal} 条`];
  if (params.trackingStatusText === '追踪中') {
    bits.push('详情页可采集与「完成追踪」');
  } else if (params.trackingStatusText === '待复盘') {
    bits.push('可「立即复盘」');
  }
  return bits.join(' · ');
}
