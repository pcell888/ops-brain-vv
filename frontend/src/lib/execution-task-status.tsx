import { Tag } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';

/** 与后端 status 字段对齐；未知状态原样展示，避免前端臆造映射 */
const KNOWN: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待执行' },
  ready: { color: 'blue', icon: <ClockCircleOutlined />, text: '就绪' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '执行中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  failed: { color: 'error', icon: <ExclamationCircleOutlined />, text: '失败' },
  cancelled: { color: 'default', icon: <ExclamationCircleOutlined />, text: '已取消' },
};

export function ExecutionTaskStatusTag({ status }: { status: string }) {
  const cfg = KNOWN[status] ?? {
    color: 'default',
    icon: <ClockCircleOutlined />,
    text: status || '—',
  };
  return (
    <Tag icon={cfg.icon} style={{ backgroundColor: cfg.color === 'default' ? 'rgba(107, 114, 128, 0.2)' : cfg.color === 'processing' ? 'rgba(23, 162, 184, 0.2)' : cfg.color === 'success' ? 'rgba(16, 185, 129, 0.2)' : cfg.color === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(107, 114, 128, 0.2)', color: cfg.color === 'default' ? '#6b7280' : cfg.color === 'processing' ? '#17a2b8' : cfg.color === 'success' ? '#10b981' : cfg.color === 'error' ? '#ef4444' : '#6b7280', border: 'none' }}>
      {cfg.text}
    </Tag>
  );
}
