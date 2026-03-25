import { Tag } from 'antd';

/** 与后端 dispatch_status 对齐，未知值原样展示 */
export function DispatchStatusTag({ status }: { status?: string }) {
  const s = (status || 'dispatched').toLowerCase();
  const map: Record<string, { label: string; color: string }> = {
    dispatched: { label: '已派发', color: 'success' },
    failed: { label: '派发失败', color: 'error' },
    pending: { label: '待派发', color: 'default' },
  };
  const cfg = map[s] || { label: status || '—', color: 'default' };
  return <Tag style={{ backgroundColor: cfg.color === 'success' ? 'rgba(16, 185, 129, 0.2)' : cfg.color === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(107, 114, 128, 0.2)', color: cfg.color === 'success' ? '#10b981' : cfg.color === 'error' ? '#ef4444' : '#6b7280', border: 'none' }}>{cfg.label}</Tag>;
}
