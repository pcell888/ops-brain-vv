import { useNavigate } from 'react-router-dom';
import {
  Card, Table, Button, Empty, Spin, Row, Col, Alert,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  RocketOutlined, LoadingOutlined, LinkOutlined, EyeOutlined,
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
  const totalDispatched = data?.total ?? tasks.length;

  const columns: ColumnsType<ExecutionTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record) => (
        <Button
          type="link"
          className="!text-white !font-medium !p-0 h-auto text-left whitespace-normal"
          onClick={() => navigate(`/execution/task/${encodeURIComponent(record.id)}`)}
        >
          {name || '—'}
        </Button>
      ),
    },
    {
      title: '接收者',
      dataIndex: 'recipient',
      key: 'recipient',
      width: 120,
      render: (_: string, record) => (
        <span className="text-gray-300 text-sm">{record.recipient || record.assigned_to || '—'}</span>
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
          <span className="text-gray-400 text-sm">
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
      width: 160,
      render: (_, record) => {
        const pid = record.plan_id;
        return (
          <div className="flex flex-wrap gap-1 items-center">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              className="!px-1"
              onClick={() => navigate(`/execution/task/${encodeURIComponent(record.id)}`)}
            >
              详情
            </Button>
            {pid && (
              <Button
                type="link"
                size="small"
                icon={<LinkOutlined />}
                className="!px-1"
                onClick={() => navigate(`/execution/${encodeURIComponent(pid)}#execution-task-list`)}
              >
                计划
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  if (!enterpriseId) {
    return <div className="flex items-center justify-center h-[60vh]"><Empty description="请先选择企业" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg">
              <RocketOutlined />
            </span>
            任务派发
          </h1>
          <p className="text-gray-400 mt-2 text-sm">
            列表展示已推送任务摘要；完整业务内容请点任务名称或「详情」。
          </p>
        </div>
        {diagnosisItems.length > 0 && (
          <DiagnosisHistorySelect
            className="shrink-0 w-full sm:w-[min(100%,320px)]"
            diagnosisItems={diagnosisItems}
            value={selectedDiagnosisId}
            onChange={setSelectedDiagnosisId}
            loading={listLoading}
          />
        )}
      </div>

      <Alert
        type="info"
        showIcon
        className="!bg-gray-800/80 !border-gray-600"
        message="派发状态表示诊断侧已落库并发起推送；业务系统内办理进度请在业务端查看。"
      />

      <Row gutter={16}>
        <Col xs={24} sm={12} lg={8}>
          <Card className="text-center">
            <div className="text-3xl font-bold text-blue-400">{totalDispatched}</div>
            <div className="text-gray-400 text-sm mt-1">已推送任务条数</div>
          </Card>
        </Col>
      </Row>

      <Card title="任务列表">
        {pageLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : !selectedDiagnosisId ? (
          <Empty description="请先完成诊断" />
        ) : (
          <Table
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
