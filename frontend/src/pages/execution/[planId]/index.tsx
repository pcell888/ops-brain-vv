import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Table, Tag, Button, Empty, Spin, Progress,
  Descriptions, App, Row, Col, Statistic,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ArrowLeftOutlined, RocketOutlined, PlayCircleOutlined,
  PauseCircleOutlined, CheckCircleOutlined, ClockCircleOutlined,
  SyncOutlined, ExclamationCircleOutlined, ReloadOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import {
  useExecutionPlanSummary, usePlanTasks,
  useStartPlan, usePausePlan, useResumePlan,
  useCompleteTask, useFailTask, useRetryTask,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import dayjs from 'dayjs';
import type { ExecutionTask } from '@/lib/types';

const taskStatusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待执行' },
  ready: { color: 'blue', icon: <ClockCircleOutlined />, text: '就绪' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '执行中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  failed: { color: 'error', icon: <ExclamationCircleOutlined />, text: '失败' },
  cancelled: { color: 'default', icon: <ExclamationCircleOutlined />, text: '已取消' },
};

export default function ExecutionDetailPage() {
  const { message } = App.useApp();
  const { planId } = useParams();
  const navigate = useNavigate();

  const { data: plan, isLoading: planLoading } = useExecutionPlanSummary(planId || null, true);
  const isActive = plan?.status === 'running' || plan?.status === 'paused';
  const { data: tasksData, isLoading: tasksLoading, refetch: refetchTasks } = usePlanTasks(planId || null, undefined, isActive ? 3000 : undefined);
  const tasks = ((tasksData as any)?.items || tasksData || []) as ExecutionTask[];

  const startPlan = useStartPlan();
  const pausePlan = usePausePlan();
  const resumePlan = useResumePlan();
  const completeTask = useCompleteTask();
  const failTask = useFailTask();
  const retryTask = useRetryTask();

  const handleStart = async () => {
    try { await startPlan.mutateAsync(planId!); message.success('计划已启动'); } catch { message.error('启动失败'); }
  };
  const handlePause = async () => {
    try { await pausePlan.mutateAsync(planId!); message.success('计划已暂停'); } catch { message.error('暂停失败'); }
  };
  const handleResume = async () => {
    try { await resumePlan.mutateAsync(planId!); message.success('计划已恢复'); } catch { message.error('恢复失败'); }
  };
  const handleCompleteTask = async (taskId: string) => {
    try { await completeTask.mutateAsync({ taskId }); message.success('任务已完成'); refetchTasks(); } catch { message.error('操作失败'); }
  };
  const handleRetryTask = async (taskId: string) => {
    try { await retryTask.mutateAsync(taskId); message.success('任务已重试'); refetchTasks(); } catch { message.error('重试失败'); }
  };

  const columns: ColumnsType<ExecutionTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <span className="font-medium text-white">{name}</span>,
    },
    {
      title: '类型',
      dataIndex: 'execution_type',
      key: 'execution_type',
      width: 100,
      render: (type: string) => {
        const map: Record<string, { label: string; color: string }> = {
          auto: { label: '自动', color: 'green' },
          semi_auto: { label: '半自动', color: 'blue' },
          manual: { label: '手动', color: 'orange' },
        };
        const cfg = map[type] || { label: type, color: 'default' };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const cfg = taskStatusConfig[status] || taskStatusConfig.pending;
        return <Tag icon={cfg.icon} color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number) => <Progress percent={progress} size="small" />,
    },
    {
      title: '时间',
      key: 'time',
      width: 180,
      render: (_, record) => (
        <div className="text-xs text-gray-400">
          {record.scheduled_start && <div>计划: {dayjs(record.scheduled_start).format('MM-DD')} ~ {dayjs(record.scheduled_end).format('MM-DD')}</div>}
          {record.actual_start && <div>实际: {dayjs(record.actual_start).format('MM-DD HH:mm')}</div>}
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <div className="flex gap-1">
          {(record.status === 'running' || record.status === 'ready') && record.execution_type === 'manual' && (
            <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => handleCompleteTask(record.id)}>
              完成
            </Button>
          )}
          {record.status === 'failed' && (
            <Button type="link" size="small" icon={<ReloadOutlined />} onClick={() => handleRetryTask(record.id)}>
              重试
            </Button>
          )}
        </div>
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
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg">
                <RocketOutlined />
              </span>
              {plan.name || '执行计划详情'}
            </h1>
          </div>
        </div>
        <div className="flex gap-2">
          {plan.status === 'pending' && (
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleStart} loading={startPlan.isPending}>启动</Button>
          )}
          {plan.status === 'running' && (
            <Button icon={<PauseCircleOutlined />} onClick={handlePause} loading={pausePlan.isPending}>暂停</Button>
          )}
          {plan.status === 'paused' && (
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleResume} loading={resumePlan.isPending}>恢复</Button>
          )}
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
  );
}
