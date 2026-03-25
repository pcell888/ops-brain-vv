import { useMemo } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Button, Card, Empty, Spin, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ArrowLeftOutlined, CameraOutlined, LineChartOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useTrackingSnapshots, useTrackingSummary } from '@/lib/hooks';

interface IndicatorChange {
  indicator_code: string;
  name: string;
  value: number;
  unit?: string;
  delta_vs_prev?: number | null;
}

interface SnapshotItem {
  snapshot_id: string;
  snapshot_at: string;
  health_score?: number;
  indicator_count: number;
  indicator_changes?: IndicatorChange[];
}

export default function TrackingSnapshotDetailPage() {
  const { trackingId = '' } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const snapshotId = searchParams.get('snapshotId');

  const { data: summary, isLoading: summaryLoading, isError } = useTrackingSummary(trackingId);
  const { data: snapshotsData, isLoading: snapshotsLoading } = useTrackingSnapshots(trackingId, {
    enabled: !!trackingId,
  });

  const snapshots = useMemo(
    () => ((snapshotsData?.items as SnapshotItem[] | undefined) ?? []).slice(),
    [snapshotsData?.items],
  );

  const selectedSnapshot = useMemo(() => {
    if (!snapshots.length) return null;
    if (snapshotId) return snapshots.find((s) => s.snapshot_id === snapshotId) ?? snapshots[0];
    return snapshots[0];
  }, [snapshots, snapshotId]);

  const indicatorColumns: ColumnsType<IndicatorChange> = [
    { title: '指标', dataIndex: 'name', key: 'name', width: 220 },
    { title: '当前值', key: 'value', width: 160, render: (_, row) => `${Number(row.value).toFixed(2)}${row.unit || ''}` },
    {
      title: '变化',
      key: 'delta_vs_prev',
      render: (_, row) => {
        if (row.delta_vs_prev == null) return <span className="text-gray-500">首次采集</span>;
        const up = row.delta_vs_prev >= 0;
        return (
          <span className={up ? 'text-emerald-400' : 'text-rose-400'}>
            {up ? '+' : ''}
            {Number(row.delta_vs_prev).toFixed(2)}
            {row.unit || ''}
          </span>
        );
      },
    },
  ];

  if (summaryLoading || snapshotsLoading) {
    return <div className="flex items-center justify-center h-[60vh]"><Spin size="large" /></div>;
  }
  if (isError || !summary) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tracking')} style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}>返回</Button>
        <div className="flex items-center justify-center h-[50vh]"><Empty description="记录不存在或无法加载" /></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tracking')} style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}>返回列表</Button>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-lg shadow-lg shadow-purple-500/20"><CameraOutlined /></span>
            采集详情
          </h1>
          <p className="text-gray-400 mt-1 text-sm font-mono break-all">{trackingId}</p>
        </div>
      </div>

      <Card title="指标明细" extra={selectedSnapshot ? dayjs(selectedSnapshot.snapshot_at).format('YYYY-MM-DD HH:mm:ss') : '-'}>
        {selectedSnapshot ? (
          <>
            <div className="mb-3 text-gray-300 flex items-center gap-2">
              <LineChartOutlined />
              得分：{selectedSnapshot.health_score == null ? '-' : Number(selectedSnapshot.health_score).toFixed(1)}
              <Tag color="blue">指标 {selectedSnapshot.indicator_count}</Tag>
            </div>
            <Table
              rowKey={(row) => row.indicator_code}
              size="small"
              pagination={false}
              columns={indicatorColumns}
              dataSource={selectedSnapshot.indicator_changes || []}
              locale={{ emptyText: '当前记录没有指标明细' }}
            />
          </>
        ) : (
          <Empty description="暂无可查看记录" />
        )}
      </Card>
    </div>
  );
}
