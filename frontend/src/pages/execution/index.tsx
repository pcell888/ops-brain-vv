

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, Table, Tag, Button, Empty, Spin, Progress, Row, Col, 
  Modal, Descriptions, App, Tooltip, Segmented, Input, Alert
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  RocketOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  LoadingOutlined,
  EyeOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  BarChartOutlined,
  UnorderedListOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { 
  useExecutionPlanList, 
  useExecutionPlanSummary,
  usePlanTasks,
  useTaskDetail,
  useGanttData,
  useStartPlan,
  usePausePlan,
  useResumePlan,
  useCompleteTask,
  useFailTask,
  useRetryTask,
  useStartTracking,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { GanttChart } from '@/components/execution/gantt-chart';
import dayjs from 'dayjs';
import type { ExecutionPlanSummary, ExecutionTask, ExecutionPlanListResponse, GanttData } from '@/lib/types';
import type { PaginatedResponse } from '@/lib/types';

// 状态配置
const planStatusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  draft: { color: 'default', icon: <ClockCircleOutlined />, text: '草稿' },
  scheduled: { color: 'blue', icon: <ClockCircleOutlined />, text: '已排期' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '执行中' },
  paused: { color: 'warning', icon: <PauseCircleOutlined />, text: '已暂停' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  failed: { color: 'error', icon: <ExclamationCircleOutlined />, text: '失败' },
};

const taskStatusConfig: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '待执行' },
  ready: { color: 'blue', text: '就绪' },
  running: { color: 'processing', text: '执行中' },
  paused: { color: 'warning', text: '已暂停' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
  cancelled: { color: 'default', text: '已取消' },
};

export default function ExecutionPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'gantt'>('list');
  const [taskDetailModalOpen, setTaskDetailModalOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [failModalOpen, setFailModalOpen] = useState(false);
  const [failReason, setFailReason] = useState('');
  const [failingTaskId, setFailingTaskId] = useState<string | null>(null);
  const [trackingConfigModalOpen, setTrackingConfigModalOpen] = useState(false);
  const [trackingIntervalDays, setTrackingIntervalDays] = useState(7);
  const [trackingPlanId, setTrackingPlanId] = useState<string | null>(null);
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const skip = useMemo(() => (currentPage - 1) * pageSize, [currentPage, pageSize]);
  
  // 获取执行计划列表
  const { data: plansData, isLoading, refetch } = useExecutionPlanList(enterpriseId, undefined, skip, pageSize);
  const typedPlansData = plansData as ExecutionPlanListResponse | undefined;
  
  // 获取计划详情
  const { data: planDetail, isLoading: detailLoading } = useExecutionPlanSummary(selectedPlanId);
  const typedPlanDetail = planDetail as ExecutionPlanSummary | undefined;
  
  // 获取任务列表
  const { data: tasksData, refetch: refetchTasks } = usePlanTasks(selectedPlanId);
  const typedTasksData = tasksData as PaginatedResponse<ExecutionTask> | undefined;
  
  // 获取任务详情（当打开弹窗时强制获取最新数据）
  const { data: taskDetailData, refetch: refetchTaskDetail } = useTaskDetail(selectedTaskId);
  const typedTaskDetail = taskDetailData as ExecutionTask | undefined;
  
  // 获取甘特图数据（按需加载：只在甘特图视图时请求）
  const { data: ganttData } = useGanttData(selectedPlanId, viewMode === 'gantt');
  const typedGanttData = ganttData as GanttData | undefined;
  
  // 操作 hooks
  const startPlan = useStartPlan();
  const pausePlan = usePausePlan();
  const resumePlan = useResumePlan();
  const completeTask = useCompleteTask();
  const failTask = useFailTask();
  const retryTask = useRetryTask();
  const startTracking = useStartTracking();

  // 处理启动计划
  const handleStartPlan = async (planId: string) => {
    try {
      await startPlan.mutateAsync(planId);
      message.success('计划已启动');
      refetch();
    } catch {
      message.error('启动失败');
    }
  };

  // 处理暂停计划
  const handlePausePlan = async (planId: string) => {
    try {
      await pausePlan.mutateAsync(planId);
      message.success('计划已暂停');
      refetch();
    } catch {
      message.error('暂停失败');
    }
  };

  // 处理恢复计划
  const handleResumePlan = async (planId: string) => {
    try {
      await resumePlan.mutateAsync(planId);
      message.success('计划已恢复');
      refetch();
    } catch {
      message.error('恢复失败');
    }
  };

  // 处理完成任务
  const handleCompleteTask = async (taskId: string) => {
    try {
      await completeTask.mutateAsync({ taskId });
      message.success('任务已完成');
      refetchTasks();
    } catch {
      message.error('操作失败');
    }
  };

  // 打开失败弹窗
  const openFailModal = (taskId: string) => {
    setFailingTaskId(taskId);
    setFailModalOpen(true);
  };

  // 处理标记失败
  const handleFailTask = async () => {
    if (!failingTaskId) return;
    try {
      await failTask.mutateAsync({ taskId: failingTaskId, errorMessage: failReason || '手动标记为失败' });
      message.success('任务已标记为失败');
      setFailModalOpen(false);
      setFailReason('');
      setFailingTaskId(null);
      refetchTasks();
    } catch {
      message.error('操作失败');
    }
  };

  // 处理重试任务
  const handleRetryTask = async (taskId: string) => {
    try {
      await retryTask.mutateAsync(taskId);
      message.success('任务已重试');
      refetchTasks();
    } catch {
      message.error('重试失败');
    }
  };

  // 处理启动追踪
  const handleStartTracking = async () => {
    if (!enterpriseId || !trackingPlanId) return;
    try {
      const result = await startTracking.mutateAsync({ 
        enterprise_id: enterpriseId, 
        plan_id: trackingPlanId,
        tracking_interval_days: trackingIntervalDays 
      });
      message.success('效果追踪已启动');
      setTrackingConfigModalOpen(false);
      setTrackingPlanId(null);
      // 跳转到追踪详情页
      if (result?.tracking_id) {
        navigate(`/tracking/${result.tracking_id}`);
      }
      refetch(); // 刷新列表以更新 tracking_id
    } catch {
      message.error('启动追踪失败');
    }
  };

  // 处理查看效果追踪
  const handleViewTracking = (trackingId: string) => {
    navigate(`/tracking/${trackingId}`);
  };

  // 查看详情 - 跳转到详情页
  const handleViewDetail = (planId: string) => {
    navigate(`/execution/${planId}`);
  };

  // 查看任务详情
  const handleViewTaskDetail = (taskId: string) => {
    setSelectedTaskId(taskId);
    setTaskDetailModalOpen(true);
    // 强制刷新任务详情数据
    setTimeout(() => {
      if (taskId) {
        refetchTaskDetail();
      }
    }, 100);
  };

  // 从甘特图点击任务
  const handleGanttTaskClick = (taskId: string) => {
    handleViewTaskDetail(taskId);
  };

  const columns: ColumnsType<ExecutionPlanSummary> = [
    {
      title: '计划名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <span className="font-medium text-white">{name}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const config = planStatusConfig[status] || planStatusConfig.draft;
        return (
          <Tag icon={config.icon} color={config.color}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 180,
      render: (progress: number) => (
        <div className="flex items-center gap-2">
          <Progress 
            percent={progress} 
            size="small" 
            strokeColor={progress >= 100 ? '#10b981' : '#3b82f6'}
            className="w-24"
          />
          <span className="text-gray-400">{progress}%</span>
        </div>
      ),
    },
    {
      title: '任务统计',
      dataIndex: 'task_stats',
      key: 'task_stats',
      width: 200,
      render: (stats: ExecutionPlanSummary['task_stats']) => (
        <div className="flex gap-2 text-xs">
          <Tooltip title="已完成">
            <Tag color="green">{stats.completed}</Tag>
          </Tooltip>
          <Tooltip title="执行中">
            <Tag color="blue">{stats.running}</Tag>
          </Tooltip>
          <Tooltip title="待执行">
            <Tag color="default">{stats.pending + stats.ready}</Tag>
          </Tooltip>
          {stats.failed > 0 && (
            <Tooltip title="失败">
              <Tag color="red">{stats.failed}</Tag>
            </Tooltip>
          )}
        </div>
      ),
    },
    {
      title: '计划时间',
      dataIndex: 'planned_start',
      key: 'planned_start',
      width: 180,
      render: (start: string, record) => (
        <div className="text-xs text-gray-400">
          <div>{dayjs(start).format('MM-DD')} ~ {dayjs(record.planned_end).format('MM-DD')}</div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 300,
      render: (_, record) => (
        <div className="flex gap-1">
          <Button 
            type="link" 
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record.plan_id)}
          >
            详情
          </Button>
          {record.status === 'scheduled' && (
            <Button 
              type="link" 
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStartPlan(record.plan_id)}
            >
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button 
              type="link" 
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handlePausePlan(record.plan_id)}
            >
              暂停
            </Button>
          )}
          {record.status === 'paused' && (
            <Button 
              type="link" 
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleResumePlan(record.plan_id)}
            >
              恢复
            </Button>
          )}
          {record.status === 'completed' && (
            record.tracking_id ? (
              <Button 
                type="link" 
                size="small"
                icon={<RocketOutlined />}
                onClick={() => handleViewTracking(record.tracking_id!)}
              >
                追踪
              </Button>
            ) : (
              <Button 
                type="link" 
                size="small"
                icon={<RocketOutlined />}
                onClick={() => {
                  setTrackingPlanId(record.plan_id);
                  setTrackingConfigModalOpen(true);
                }}
                loading={startTracking.isPending}
              >
                追踪
              </Button>
            )
          )}
        </div>
      ),
    },
  ];

  // 任务列表列
  const taskColumns: ColumnsType<ExecutionTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Button type="link" size="small" onClick={() => handleViewTaskDetail(record.id)}>
          {name}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = taskStatusConfig[status] || taskStatusConfig.pending;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '类型',
      dataIndex: 'execution_type',
      key: 'execution_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'auto' ? 'purple' : 'blue'}>
          {type === 'auto' ? '自动' : '手动'}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number) => (
        <Progress percent={progress} size="small" />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <div className="flex gap-1">
          {record.status === 'running' && record.execution_type === 'manual' && (
            <>
              <Button 
                type="link" 
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handleCompleteTask(record.id)}
              >
                完成
              </Button>
              <Button 
                type="link" 
                size="small"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => openFailModal(record.id)}
              >
                失败
              </Button>
            </>
          )}
          {record.status === 'failed' && (
            <Button 
              type="link" 
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetryTask(record.id)}
            >
              重试
            </Button>
          )}
        </div>
      ),
    },
  ];

  // 统计数据
  const stats = typedPlansData?.items ? {
    total: typedPlansData.total,
    running: typedPlansData.items.filter(p => p.status === 'running').length,
    completed: typedPlansData.items.filter(p => p.status === 'completed').length,
    avgProgress: Math.round(typedPlansData.items.reduce((sum, p) => sum + p.progress, 0) / typedPlansData.items.length) || 0,
  } : null;

  // 获取选中的任务详情（优先使用任务详情API，否则从列表查找）
  const selectedTask = typedTaskDetail || typedTasksData?.items?.find((t: ExecutionTask) => t.id === selectedTaskId);

  // 未选择企业
  if (!enterpriseId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Empty description="请先选择企业" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-lg shadow-lg shadow-green-500/20">
              <RocketOutlined />
            </span>
            执行监控
          </h1>
          <p className="text-gray-400 mt-2 text-sm">
            监控执行计划进度，管理任务状态
          </p>
        </div>
        <Button icon={<SyncOutlined />} onClick={() => refetch()}>
          刷新
        </Button>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">{stats.total}</div>
              <div className="text-gray-400 text-sm mt-1">计划总数</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-amber-400">{stats.running}</div>
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
              <div className="text-3xl font-bold text-purple-400">{stats.avgProgress}%</div>
              <div className="text-gray-400 text-sm mt-1">平均进度</div>
            </Card>
          </Col>
        </Row>
      )}

      {/* 计划列表 */}
      <Card>
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={typedPlansData?.items || []}
            rowKey="plan_id"
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: typedPlansData?.total || 0,
              showTotal: (total) => `共 ${total} 个计划`,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (page, size) => {
                setCurrentPage(page);
                if (size !== pageSize) {
                  setPageSize(size);
                  setCurrentPage(1);
                }
              },
              onShowSizeChange: (current, size) => {
                setPageSize(size);
                setCurrentPage(1);
              },
            }}
            locale={{
              emptyText: <Empty description="暂无执行计划，请先在方案页面创建执行计划" />,
            }}
          />
        )}
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title={
          <div className="flex items-center justify-between pr-8">
            <div className="flex items-center gap-2">
              <RocketOutlined className="text-green-400" />
              <span>执行计划详情</span>
            </div>
            <Segmented
              value={viewMode}
              onChange={(v) => setViewMode(v as 'list' | 'gantt')}
              options={[
                { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
                { value: 'gantt', icon: <BarChartOutlined />, label: '甘特图' },
              ]}
              size="small"
            />
          </div>
        }
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedPlanId(null);
          setViewMode('list');
        }}
        footer={null}
        width={1100}
      >
        {detailLoading ? (
          <div className="flex items-center justify-center py-10">
            <Spin />
          </div>
        ) : typedPlanDetail ? (
          <div className="space-y-4">
            {/* 操作按钮区 */}
            <div className="flex items-center justify-between bg-gray-800/50 rounded-lg p-3">
              <div className="flex items-center gap-3">
                <Tag color={typedPlanDetail?.status ? planStatusConfig[typedPlanDetail.status]?.color : undefined} className="!text-base !py-1 !px-3">
                  {typedPlanDetail?.status ? (planStatusConfig[typedPlanDetail.status]?.text || typedPlanDetail.status) : ''}
                </Tag>
                <span className="text-gray-400">整体进度:</span>
                <Progress percent={typedPlanDetail?.progress} size="small" className="!w-32 !m-0" />
              </div>
              <div className="flex gap-2">
                {(!typedPlanDetail?.status || typedPlanDetail?.status === 'pending' || typedPlanDetail?.status === 'draft') && (
                  <Button 
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={() => handleStartPlan(typedPlanDetail.plan_id)}
                    loading={startPlan.isPending}
                  >
                    启动执行
                  </Button>
                )}
                {typedPlanDetail.status === 'running' && (
                  <Button 
                    icon={<PauseCircleOutlined />}
                    onClick={() => handlePausePlan(typedPlanDetail.plan_id)}
                    loading={pausePlan.isPending}
                  >
                    暂停
                  </Button>
                )}
                {typedPlanDetail.status === 'paused' && (
                  <Button 
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={() => handleResumePlan(typedPlanDetail.plan_id)}
                    loading={resumePlan.isPending}
                  >
                    继续执行
                  </Button>
                )}
              </div>
            </div>

            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="计划名称" span={2}>
                <span className="font-medium">{typedPlanDetail.name}</span>
              </Descriptions.Item>
              <Descriptions.Item label="计划开始">
                {dayjs(typedPlanDetail.planned_start).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="计划结束">
                {dayjs(typedPlanDetail.planned_end).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              {typedPlanDetail.actual_start && (
                <Descriptions.Item label="实际开始">
                  {dayjs(typedPlanDetail.actual_start).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
              {typedPlanDetail.actual_end && (
                <Descriptions.Item label="实际结束">
                  {dayjs(typedPlanDetail.actual_end).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* 任务统计 */}
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">任务统计</h4>
              <div className="grid grid-cols-7 gap-2">
                {Object.entries(typedPlanDetail.task_stats).map(([key, value]) => (
                  <div 
                    key={key}
                    className="bg-gray-800/50 rounded-lg p-2 text-center"
                  >
                    <div className="text-lg font-bold text-white">{value}</div>
                    <div className="text-xs text-gray-500">{taskStatusConfig[key]?.text || key}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 任务视图 */}
            {viewMode === 'list' ? (
              typedTasksData?.items && (
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">
                    任务列表 <Tag className="ml-2">{typedTasksData.total}</Tag>
                  </h4>
                  <Table
                    columns={taskColumns}
                    dataSource={typedTasksData.items}
                    rowKey="id"
                    size="small"
                    pagination={false}
                    scroll={{ y: 300 }}
                  />
                </div>
              )
            ) : (
              ganttData && (
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">
                    甘特图视图
                  </h4>
                  <GanttChart
                    tasks={typedGanttData?.tasks || []}
                    milestones={typedGanttData?.milestones || []}
                    planStart={typedPlanDetail.planned_start}
                    planEnd={typedPlanDetail.planned_end}
                    onTaskClick={handleGanttTaskClick}
                  />
                </div>
              )
            )}
          </div>
        ) : (
          <Empty description="无法加载计划详情" />
        )}
      </Modal>

      {/* 任务详情弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <CheckCircleOutlined className="text-blue-400" />
            <span>任务详情</span>
          </div>
        }
        open={taskDetailModalOpen}
        onCancel={() => {
          setTaskDetailModalOpen(false);
          setSelectedTaskId(null);
        }}
        footer={null}
        width={600}
      >
        {selectedTask ? (
          <div className="space-y-4">
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="任务名称" span={2}>
                <span className="font-medium">{selectedTask.name}</span>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={taskStatusConfig[selectedTask.status]?.color}>
                  {taskStatusConfig[selectedTask.status]?.text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="执行类型">
                <Tag color={selectedTask.execution_type === 'auto' ? 'purple' : 'blue'}>
                  {selectedTask.execution_type === 'auto' ? '自动执行' : '手动执行'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress percent={selectedTask.progress} size="small" />
              </Descriptions.Item>
              <Descriptions.Item label="负责人">
                {selectedTask.assigned_to || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="计划开始">
                {selectedTask.scheduled_start ? dayjs(selectedTask.scheduled_start).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="计划结束">
                {selectedTask.scheduled_end ? dayjs(selectedTask.scheduled_end).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="实际开始">
                {selectedTask.actual_start ? dayjs(selectedTask.actual_start).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="实际结束">
                {selectedTask.actual_end ? dayjs(selectedTask.actual_end).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              {selectedTask.retry_count && selectedTask.retry_count > 0 && (
                <Descriptions.Item label="重试次数">
                  <Tag color="orange">{selectedTask.retry_count}</Tag>
                </Descriptions.Item>
              )}
            </Descriptions>

            {selectedTask.description && (
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">任务描述</h4>
                <div className="bg-gray-800/50 rounded-lg p-3 text-gray-300 text-sm">
                  {selectedTask.description}
                </div>
              </div>
            )}

            {/* 显示错误信息 - 任务失败时总是显示 */}
            {selectedTask.status === 'failed' && (
              <div>
                <h4 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
                  <ExclamationCircleOutlined />
                  错误信息
                </h4>
                <Alert
                  message={selectedTask.error_message || '任务执行失败，未提供具体错误信息'}
                  type="error"
                  showIcon
                  className="!bg-red-500/10 !border-red-500/30"
                />
              </div>
            )}

            {/* 显示执行结果 */}
            {selectedTask.result && selectedTask.status === 'completed' && (
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">执行结果</h4>
                <div className="bg-gray-800/50 rounded-lg p-3 text-gray-300 text-sm">
                  <pre className="whitespace-pre-wrap text-xs">
                    {JSON.stringify(selectedTask.result, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex gap-2 justify-end">
              {selectedTask.status === 'running' && selectedTask.execution_type === 'manual' && (
                <>
                  <Button 
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    onClick={() => {
                      handleCompleteTask(selectedTask.id);
                      setTaskDetailModalOpen(false);
                    }}
                  >
                    标记完成
                  </Button>
                  <Button 
                    danger
                    icon={<CloseCircleOutlined />}
                    onClick={() => {
                      setTaskDetailModalOpen(false);
                      openFailModal(selectedTask.id);
                    }}
                  >
                    标记失败
                  </Button>
                </>
              )}
              {selectedTask.status === 'failed' && (
                <Button 
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    handleRetryTask(selectedTask.id);
                    setTaskDetailModalOpen(false);
                  }}
                >
                  重试任务
                </Button>
              )}
            </div>
          </div>
        ) : (
          <Empty description="无法加载任务详情" />
        )}
      </Modal>

      {/* 标记失败弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <CloseCircleOutlined className="text-rose-400" />
            <span>标记任务失败</span>
          </div>
        }
        open={failModalOpen}
        onCancel={() => {
          setFailModalOpen(false);
          setFailReason('');
          setFailingTaskId(null);
        }}
        onOk={handleFailTask}
        okText="确认"
        okButtonProps={{ danger: true, loading: failTask.isPending }}
        cancelText="取消"
      >
        <div className="py-4">
          <p className="text-gray-400 mb-3">请输入失败原因：</p>
          <Input.TextArea
            value={failReason}
            onChange={(e) => setFailReason(e.target.value)}
            placeholder="例如：外部依赖不可用、资源不足等"
            rows={3}
          />
        </div>
      </Modal>

      {/* 效果追踪配置弹窗 */}
      <Modal
        title="配置效果追踪"
        open={trackingConfigModalOpen}
        onCancel={() => {
          setTrackingConfigModalOpen(false);
          setTrackingPlanId(null);
        }}
        onOk={handleStartTracking}
        okText="启动追踪"
        okButtonProps={{ loading: startTracking.isPending }}
        cancelText="取消"
      >
        <div className="py-4 space-y-4">
          <div>
            <h4 className="text-sm font-medium text-white mb-2">采集间隔设置</h4>
            <p className="text-gray-400 text-sm mb-3">
              设置系统自动采集指标快照的时间间隔。较短的间隔可以更及时地观察效果变化，但会产生更多数据。
            </p>
          </div>
          
          <div className="bg-gray-800/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-300">采集间隔</span>
              <span className="text-blue-400 font-medium">{trackingIntervalDays} 天</span>
            </div>
            <input
              type="range"
              min="1"
              max="30"
              value={trackingIntervalDays}
              onChange={(e) => setTrackingIntervalDays(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>1天（高频）</span>
              <span>7天（推荐）</span>
              <span>30天（低频）</span>
            </div>
          </div>

          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
            <p className="text-blue-300 text-sm">
              <strong>当前选择：</strong>
              {trackingIntervalDays === 1 && "每天采集 - 适用于关键指标实时监控"}
              {trackingIntervalDays >= 2 && trackingIntervalDays <= 3 && "每2-3天采集 - 适用于快速实验验证"}
              {trackingIntervalDays >= 4 && trackingIntervalDays <= 10 && "每周采集 - 标准优化方案推荐"}
              {trackingIntervalDays >= 11 && trackingIntervalDays <= 20 && "每两周采集 - 适用于中期观察"}
              {trackingIntervalDays >= 21 && "每月采集 - 适用于长期战略项目"}
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
}
