import { useNavigate } from 'react-router-dom';
import {
  Card, Table, Button, Empty, Spin,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  RocketOutlined, LoadingOutlined, EyeOutlined,
} from '@ant-design/icons';
import {
  useDiagnosisSelection,
  useExecutionTaskList,
} from '@/lib/hooks';
import { DiagnosisHistorySelect } from '@/components/diagnosis-history-select';
import { useAppStore } from '@/stores/app-store';
import dayjs from 'dayjs';
import type { ExecutionTask } from '@/lib/types';
import { DispatchStatusTag } from '@/lib/dispatch-status';

export default function ExecutionPage() {
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  const { diagnosisItems, selectedDiagnosisId, setSelectedDiagnosisId, listLoading } =
    useDiagnosisSelection(enterpriseId);
  const { data, isLoading } = useExecutionTaskList(enterpriseId, selectedDiagnosisId);
  const tasks = data?.items || [];
  const pageLoading = listLoading || isLoading;

  const columns: ColumnsType<ExecutionTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record) => (
        <span
          role="button"
          tabIndex={0}
          className="font-medium text-primary cursor-pointer hover:underline text-left"
          onClick={() => navigate(`/execution/task/${encodeURIComponent(record.id)}`)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              navigate(`/execution/task/${encodeURIComponent(record.id)}`);
            }
          }}
        >
          {name || '—'}
        </span>
      ),
    },
    {
      title: '接收者',
      dataIndex: 'recipient',
      key: 'recipient',
      width: 120,
      render: (_: string, record) => (
        <span className="text-secondary text-sm">{record.assignee_user_name || record.recipient || record.assigned_to || '—'}</span>
      ),
    },
    {
      title: '派发时间',
      dataIndex: 'dispatch_time',
      key: 'dispatch_time',
      width: 180,
      render: (_: string, record) => {
        const t = record.dispatch_time || record.scheduled_start;
        return (
          <span className="text-secondary text-sm">
            {t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '—'}
          </span>
        );
      },
    },
    {
      title: '派发状态',
      dataIndex: 'dispatch_status',
      key: 'dispatch_status',
      width: 110,
      render: (s: string | undefined) => <DispatchStatusTag status={s} />,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          className="!px-1"
          onClick={() => navigate(`/execution/task/${encodeURIComponent(record.id)}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  if (!enterpriseId) {
    return <div className="flex items-center justify-center h-[60vh]"><Empty description="请先选择企业" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="shrink-0">
          <h1 className="text-3xl font-bold tracking-tight text-[#303133] flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg text-white shrink-0">
              <RocketOutlined />
            </span>
            任务派发
          </h1>
        </div>
        {diagnosisItems.length > 0 && (
          <DiagnosisHistorySelect
            className="max-w-full shrink-0 sm:ml-auto"
            diagnosisItems={diagnosisItems}
            value={selectedDiagnosisId}
            onChange={setSelectedDiagnosisId}
            loading={listLoading}
          />
        )}
      </div>

      <Card>
        {pageLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : !selectedDiagnosisId ? (
          <Empty description="请先完成诊断" />
        ) : (
          <Table
            bordered={false}
            columns={columns}
            dataSource={tasks}
            rowKey="id"
            pagination={false}
            locale={{ emptyText: <Empty description="该次诊断下暂无推送任务" /> }}
          />
        )}
      </Card>
    </div>
  );
}
