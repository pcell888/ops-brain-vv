import { Select, Tag } from 'antd';
import dayjs from 'dayjs';
import type { DiagnosisListItem } from '@/lib/types';

type Props = {
  diagnosisItems: DiagnosisListItem[];
  value: string | null;
  onChange: (id: string) => void;
  loading?: boolean;
  className?: string;
};

export function DiagnosisHistorySelect({ diagnosisItems, value, onChange, loading, className }: Props) {
  if (diagnosisItems.length === 0) return null;

  const options = diagnosisItems.map((i) => ({
    value: i.diagnosis_id,
    label: (
      <span className="flex items-center justify-between gap-2">
        <span>{dayjs(i.created_at).format('YYYY-MM-DD HH:mm')}</span>
        {i.status !== 'completed' && (
          <Tag className="!m-0" color={i.status === 'running' ? 'processing' : 'default'} style={{ background: '#E7ECFF', color: 'rgba(10, 67, 255, 1)', border: 'none' }}>
            {i.status === 'running' ? '进行中' : i.status === 'failed' ? '失败' : i.status}
          </Tag>
        )}
      </span>
    ),
  }));

  return (
    <div className={className}>
      <div className="text-gray-500 text-xs mb-1">历史诊断</div>
      <Select
        className="w-full"
        value={value ?? undefined}
        options={options}
        loading={loading}
        onChange={onChange}
        placeholder="选择诊断"
        showSearch
        filterOption={(input, opt) => {
          const item = diagnosisItems.find((x) => x.diagnosis_id === opt?.value);
          if (!item) return false;
          const t = dayjs(item.created_at).format('YYYY-MM-DD HH:mm');
          return t.includes(input.trim()) || item.diagnosis_id.includes(input.trim());
        }}
      />
    </div>
  );
}
