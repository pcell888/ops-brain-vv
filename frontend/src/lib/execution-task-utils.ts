import dayjs from 'dayjs';
import type { ExecutionTask } from '@/lib/types';

/** 后端 deadline 可能是 ISO 时间或「3天内」等文案 */
export function formatTaskDeadlineDisplay(value: string | undefined | null): string {
  if (value == null || value === '') return '';
  const d = dayjs(value);
  if (d.isValid()) return d.format('MM-DD HH:mm');
  return String(value);
}

export function taskHasExpandableDetail(record: ExecutionTask): boolean {
  const desc = (record.description || '').trim();
  const name = (record.name || '').trim();
  const hasDesc = Boolean(desc && desc !== name);
  const steps = record.implementation_steps?.filter(Boolean) || [];
  return hasDesc || steps.length > 0;
}
