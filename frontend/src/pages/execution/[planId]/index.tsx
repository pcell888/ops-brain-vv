import { useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Card, Table, Button, Empty, Spin,
  Row, Col, Statistic, Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ArrowLeftOutlined, RocketOutlined, LoadingOutlined, EyeOutlined,
} from '@ant-design/icons';
import { useExecutionPlanSummary, usePlanTasks } from '@/lib/hooks';
import dayjs from 'dayjs';
import type { ExecutionTask } from '@/lib/types';
import { DispatchStatusTag } from '@/lib/dispatch-status';

export default function ExecutionDetailPage() {
  const { planId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const taskListAnchorRef = useRef<HTMLDivElement>(null);

  const { data: plan, isLoading: planLoading } = useExecutionPlanSummary(planId || null, true);
  const isActive = plan?.status === 'running';
  const { data: tasksData, isLoading: tasksLoading } = usePlanTasks(planId || null, undefined, isActive ? 3000 : undefined);
  const tasks = ((tasksData as { items?: ExecutionTask[] })?.items || tasksData || []) as ExecutionTask[];

  useEffect(() => {
    if (location.hash !== '#execution-task-list' || !plan) return;
    const t = window.setTimeout(() => {
      taskListAnchorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
    return () => window.clearTimeout(t);
  }, [location.hash, plan?.plan_id, tasksLoading]);

  const columns: ColumnsType<ExecutionTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
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
      key: 'dispatch_time',
      width: 170,
      render: (_, record) => {
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
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/execution/task/${encodeURIComponent(record.id)}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  if (planLoading) {
    return <div className="flex items-center justify-center h-[60vh]"><Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} /></div>;
  }

  if (!plan) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        <Empty description="执行计划不存在" />
      </div>
    );
  }

  const stats = plan.task_stats || { pending: 0, running: 0, completed: 0, failed: 0 };
  const totalTasks = Object.values(stats).reduce((a, b) => a + (b || 0), 0);

  return (
    <div className="space-y-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-between sm:items-start">
        <div className="flex items-center gap-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}>返回</Button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg">
                <RocketOutlined />
              </span>
              {plan.name || '执行计划详情'}
            </h1>
            <Typography.Text type="secondary" className="!text-gray-400 text-sm mt-1 block">
              方案采纳后任务已自动创建并派发，进度以下方任务状态为准。
            </Typography.Text>
          </div>
        </div>
      </div>

      <Row gutter={16}>
        <Col span={6}>
          <Card className="text-center">
            <Statistic title="总进度" value={plan.progress} suffix="%" valueStyle={{ color: plan.progress >= 100 ? '#10b981' : '#3b82f6' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <Statistic title="已完成" value={stats.completed || 0} suffix={`/ ${totalTasks}`} valueStyle={{ color: '#10b981' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <Statistic title="执行中" value={stats.running || 0} valueStyle={{ color: '#3b82f6' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <Statistic title="失败" value={stats.failed || 0} valueStyle={{ color: (stats.failed || 0) > 0 ? '#ef4444' : '#6b7280' }} />
          </Card>
        </Col>
      </Row>

      <div id="execution-task-list" ref={taskListAnchorRef}>
        <Card title="任务列表">
          {tasksLoading ? (
            <div className="flex items-center justify-center py-10"><Spin /></div>
          ) : (
            <Table
              columns={columns}
              dataSource={tasks}
              rowKey="id"
              pagination={false}
              locale={{ emptyText: <Empty description="暂无任务" /> }}
            />
          )}
        </Card>
      </div>
    </div>
  );
}
