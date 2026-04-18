import dayjs from 'dayjs';

function elapsedDays(startedAt?: string, endedAt?: string | null): number {
  if (!startedAt) return 0;
  const start = dayjs(startedAt);
  const end = endedAt ? dayjs(endedAt) : dayjs();
  return Math.max(0, end.diff(start, 'day'));
}

export type TrackingSummaryLike = {
  status: string;
  snapshot_count?: number;
  review_due_date?: string;
  started_at?: string;
  completed_at?: string | null;
  total_duration_days?: number;
};

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
  const totalPlan = Number(s.total_duration_days);

  if (s.status === 'active') {
    const bits: string[] = ['追踪中', `${snap} 次快照`];
    if (Number.isFinite(totalPlan) && totalPlan > 0) {
      bits.push(`约 ${usedDays}/${Math.round(totalPlan)} 天`);
    } else {
      bits.push(`约 ${usedDays} 天`);
    }
    bits.push('复盘前请「完成追踪」');
    return bits.join(' · ');
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
