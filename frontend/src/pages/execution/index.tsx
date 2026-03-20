import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Table, Tag, Button, Empty, Spin, Progress, Row, Col, App, Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  RocketOutlined, PlayCircleOutlined, PauseCircleOutlined,
  CheckCircleOutlined, ClockCircleOutlined, SyncOutlined,
  LoadingOutlined, EyeOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  useExecutionPlanList,
  useStartPlan,
  usePausePlan,
  useResumePlan,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import dayjs from 'dayjs';
import type { ExecutionPlanSummary } from '@/lib/types';

const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待启动' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '执行中' },
  paused: { color: 'warning', icon: <PauseCircleOutlined />, text: '已暂停' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  failed: { color: 'error', icon: <ExclamationCircleOutlined />, text: '失败' },
};

export default function ExecutionPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  const { data, isLoading, refetch } = useExecutionPlanList(enterpriseId);
  const plans = (data as any)?.items || [];
  const startPlan = useStartPlan();
  const pausePlan = usePausePlan();
  const resumePlan = useResumePlan();

  const handleStart = async (planId: string) => {
    try {
      await startPlan.mutateAsync(planId);
      message.success('计划已启动');
      refetch();
    } catch { message.error('启动失败'); }
  };

  const handlePause = async (planId: string) => {
    try {
      await pausePlan.mutateAsync(planId);
      message.success('计划已暂停');
      refetch();
    } catch { message.error('暂停失败'); }
  };

  const handleResume = async (planId: string) => {
    try {
      await resumePlan.mutateAsync(planId);
      message.success('计划已恢复');
      refetch();
    } catch { message.error('恢复失败'); }
  };

  const stats = useMemo(() => ({
    total: plans.length,
    running: plans.filter((p: ExecutionPlanSummary) => p.status === 'running').length,
    completed: plans.filter((p: ExecutionPlanSummary) => p.status === 'completed').length,
    pending: plans.filter((p: ExecutionPlanSummary) => p.status === 'pending').length,
  }), [plans]);

  const columns: ColumnsType<ExecutionPlanSummary> = [
    {
      title: '计划名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Button type="link" onClick={() => navigate(`/execution/${record.plan_id}`)} className="!p-0">
          {name || `执行计划 ${record.plan_id.slice(0, 8)}`}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = statusConfig[status] || statusConfig.pending;
        return <Tag icon={cfg.icon} color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress: number) => (
        <Progress percent={progress} size="small" strokeColor={progress >= 100 ? '#10b981' : '#3b82f6'} />
      ),
    },
    {
      title: '任务统计',
      key: 'task_stats',
      width: 180,
      render: (_, record) => {
        const s = record.task_stats;
        if (!s) return '-';
        const total = (s.pending || 0) + (s.running || 0) + (s.completed || 0) + (s.failed || 0);
        return (
          <div className="text-xs text-gray-400">
            <span className="text-emerald-400">{s.completed || 0}</span>/{total} 完成
            {(s.failed || 0) > 0 && <span className="text-rose-400 ml-2">{s.failed} 失败</span>}
          </div>
        );
      },
    },
    {
      title: '计划时间',
      key: 'time',
      width: 200,
      render: (_, record) => (
        <div className="text-xs text-gray-400">
          {record.planned_start && <div>{dayjs(record.planned_start).format('YYYY-MM-DD')} ~ {dayjs(record.planned_end).format('MM-DD')}</div>}
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <div className="flex gap-1">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/execution/${record.plan_id}`)}>
            详情
          </Button>
          {record.status === 'pending' && (
            <Button type="link" size="small" icon={<PlayCircleOutlined />} onClick={() => handleStart(record.plan_id)}>
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button type="link" size="small" icon={<PauseCircleOutlined />} onClick={() => handlePause(record.plan_id)}>
              暂停
            </Button>
          )}
          {record.status === 'paused' && (
            <Button type="link" size="small" icon={<PlayCircleOutlined />} onClick={() => handleResume(record.plan_id)}>
              恢复
            </Button>
          )}
        </div>
      ),
    },
  ];

  if (!enterpriseId) {
    return <div className="flex items-center justify-center h-[60vh]"><Empty description="请先选择企业" /></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg">
            <RocketOutlined />
          </span>
          任务执行
        </h1>
        <p className="text-gray-400 mt-2 text-sm">查看和管理方案执行计划</p>
      </div>

      <Row gutter={16}>
        <Col span={6}>
          <Card className="text-center">
            <div className="text-3xl font-bold text-blue-400">{stats.total}</div>
            <div className="text-gray-400 text-sm mt-1">计划总数</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <div className="text-3xl font-bold text-cyan-400">{stats.running}</div>
            <div className="text-gray-400 text-sm mt-1">执行中</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <div className="text-3xl font-bold text-emerald-400">{stats.completed}</div>
            <div className="text-gray-400 text-sm mt-1">已完成</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card className="text-center">
            <div className="text-3xl font-bold text-gray-400">{stats.pending}</div>
            <div className="text-gray-400 text-sm mt-1">待启动</div>
          </Card>
        </Col>
      </Row>

      <Card>
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={plans}
            rowKey="plan_id"
            pagination={false}
            locale={{ emptyText: <Empty description="暂无执行计划" /> }}
          />
        )}
      </Card>
    </div>
  );
}
