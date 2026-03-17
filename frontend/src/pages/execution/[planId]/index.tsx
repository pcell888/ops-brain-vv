

import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, Table, Tag, Button, Empty, Spin, Progress,
  Descriptions, App, Segmented, Input, Modal, Alert
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  ArrowLeftOutlined,
  RocketOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  BarChartOutlined,
  UnorderedListOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  AimOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { 
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
import { TaskFlowChart } from '@/components/execution/task-flow-chart';
import dayjs from 'dayjs';
import type { ExecutionTask, ExecutionPlanSummary, GanttData } from '@/lib/types';
import type { PaginatedResponse } from '@/lib/types';
import clsx from 'clsx';
import { ApartmentOutlined } from '@ant-design/icons';

// 状态配置
const planStatusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  created: { color: 'default', icon: <ClockCircleOutlined />, text: '已创建' },
  draft: { color: 'default', icon: <ClockCircleOutlined />, text: '草稿' },
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待执行' },
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

const taskTypeConfig: Record<string, { color: string; text: string }> = {
  auto: { color: 'cyan', text: '自动' },
  semi_auto: { color: 'blue', text: '半自动' },
  manual: { color: 'orange', text: '手动' },
  custom_api: { color: 'purple', text: 'API' },
  custom_script: { color: 'magenta', text: '脚本' },
};

export default function ExecutionPlanDetailPage() {
  const { message } = App.useApp();
  const params = useParams();
  const navigate = useNavigate();
  const planId = params.planId as string;
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;
  
  const [viewMode, setViewMode] = useState<'list' | 'flow' | 'gantt'>('flow');
  const [taskDetailModalOpen, setTaskDetailModalOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [failModalOpen, setFailModalOpen] = useState(false);
  const [failReason, setFailReason] = useState('');
  const [failingTaskId, setFailingTaskId] = useState<string | null>(null);
  const [trackingConfigModalOpen, setTrackingConfigModalOpen] = useState(false);
  const [trackingIntervalDays, setTrackingIntervalDays] = useState(7);
  
  // 获取计划详情（执行中/已暂停时自动每 3 秒轮询）
  const { data: planDetail, isLoading: detailLoading, refetch } = useExecutionPlanSummary(planId, true);
  const typedPlanDetail = planDetail as ExecutionPlanSummary | undefined;
  const pollTasks = typedPlanDetail?.status === 'running' || typedPlanDetail?.status === 'paused';

  // 获取任务列表（执行中时同步轮询以实时更新节点状态）
  const { data: tasksData, refetch: refetchTasks } = usePlanTasks(planId, undefined, pollTasks ? 3000 : undefined);
  const typedTasksData = tasksData as PaginatedResponse<ExecutionTask> | undefined;

  // 计划已完成时补拉一次任务列表，确保流程图节点状态与 task_stats 一致
  const hasRefetchedForCompleted = useRef(false);
  useEffect(() => {
    if (typedPlanDetail?.status === 'completed' && !hasRefetchedForCompleted.current) {
      hasRefetchedForCompleted.current = true;
      refetchTasks();
    } else if (typedPlanDetail?.status !== 'completed') {
      hasRefetchedForCompleted.current = false;
    }
  }, [typedPlanDetail?.status, refetchTasks]);
  
  // 获取任务详情（当打开弹窗时强制获取最新数据）
  const { data: taskDetailData, refetch: refetchTaskDetail } = useTaskDetail(selectedTaskId);
  const typedTaskDetail = taskDetailData as ExecutionTask | undefined;
  
  // 获取甘特图数据（按需加载：只在甘特图视图时请求）
  const { data: ganttData } = useGanttData(planId, viewMode === 'gantt');
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
  const handleStartPlan = async () => {
    try {
      await startPlan.mutateAsync(planId);
      message.success('计划已启动，任务开始执行');
    } catch {
      message.error('启动失败');
    }
  };

  // 处理暂停计划
  const handlePausePlan = async () => {
    try {
      await pausePlan.mutateAsync(planId);
      message.success('计划已暂停');
    } catch {
      message.error('暂停失败');
    }
  };

  // 处理继续执行
  const handleResumePlan = async () => {
    try {
      await resumePlan.mutateAsync(planId);
      message.success('计划继续执行');
    } catch {
      message.error('继续执行失败');
    }
  };

  // 处理完成任务
  const handleCompleteTask = async (taskId: string) => {
    try {
      await completeTask.mutateAsync({ taskId });
      message.success('任务已完成');
    } catch {
      message.error('操作失败');
    }
  };

  // 处理失败任务
  const handleFailTask = async () => {
    if (!failingTaskId) return;
    try {
      await failTask.mutateAsync({ taskId: failingTaskId, errorMessage: failReason });
      message.success('任务已标记为失败');
      setFailModalOpen(false);
      setFailReason('');
      setFailingTaskId(null);
    } catch {
      message.error('操作失败');
    }
  };

  // 处理重试任务
  const handleRetryTask = async (taskId: string) => {
    try {
      await retryTask.mutateAsync(taskId);
      message.success('任务已重试');
    } catch {
      message.error('重试失败');
    }
  };

  // 打开失败弹窗
  const openFailModal = (taskId: string) => {
    setFailingTaskId(taskId);
    setFailModalOpen(true);
  };

  // 处理启动追踪
  const handleStartTracking = async () => {
    if (!enterpriseId) return;
    try {
      const result = await startTracking.mutateAsync({ 
        enterprise_id: enterpriseId, 
        plan_id: planId,
        tracking_interval_days: trackingIntervalDays 
      });
      message.success('效果追踪已启动');
      setTrackingConfigModalOpen(false);
      // 跳转到追踪详情页
      if (result?.tracking_id) {
        navigate(`/tracking/${result.tracking_id}`);
      }
    } catch {
      message.error('启动追踪失败');
    }
  };

  // 处理查看效果追踪
  const handleViewTracking = () => {
    if (typedPlanDetail?.tracking_id) {
      navigate(`/tracking/${typedPlanDetail.tracking_id}`);
    }
  };

  // 处理甘特图任务点击
  const handleGanttTaskClick = (taskId: string) => {
    setSelectedTaskId(taskId);
    setTaskDetailModalOpen(true);
    // 强制刷新任务详情数据
    setTimeout(() => {
      if (taskId) {
        refetchTaskDetail();
      }
    }, 100);
  };

  // 处理查看任务详情
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

  // 获取选中的任务详情（优先使用任务详情API，否则从列表查找）
  const selectedTask = typedTaskDetail || typedTasksData?.items?.find((t: ExecutionTask) => t.id === selectedTaskId);

  // 任务表格列
  const taskColumns: ColumnsType<ExecutionTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <div>
          <div className="font-medium text-white">{name}</div>
          {record.description && (
            <div className="text-xs text-gray-500 truncate max-w-xs">{record.description}</div>
          )}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={taskStatusConfig[status]?.color}>
          {taskStatusConfig[status]?.text || status}
        </Tag>
      ),
    },
    {
      title: '类型',
      dataIndex: 'execution_type',
      key: 'execution_type',
      width: 80,
      render: (type: string) => (
        <Tag color={taskTypeConfig[type]?.color || 'default'}>
          {taskTypeConfig[type]?.text || type}
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
      title: '计划时间',
      key: 'schedule',
      width: 180,
      render: (_, record) => (
        <div className="text-xs text-gray-400">
          {record.scheduled_start && (
            <div>{dayjs(record.scheduled_start).format('MM-DD')} ~ {dayjs(record.scheduled_end).format('MM-DD')}</div>
          )}
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <div className="flex gap-1 flex-wrap">
          {(record.status === 'ready' || record.status === 'running') && (
            <Button 
              type="link" 
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleCompleteTask(record.id)}
            >
              完成
            </Button>
          )}
          {record.status === 'running' && (
            <Button 
              type="link" 
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => openFailModal(record.id)}
            >
              失败
            </Button>
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

  if (detailLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin size="large" />
      </div>
    );
  }

  if (!typedPlanDetail) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          返回
        </Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty description="执行计划不存在" />
        </div>
      </div>
    );
  }

  const isNotStarted = !typedPlanDetail.status || typedPlanDetail.status === 'pending' || typedPlanDetail.status === 'draft' || typedPlanDetail.status === 'scheduled' || typedPlanDetail.status === 'created';
  const isRunning = typedPlanDetail.status === 'running';
  const isPaused = typedPlanDetail.status === 'paused';
  const isCompleted = typedPlanDetail.status === 'completed';

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-lg shadow-lg shadow-green-500/20">
                <RocketOutlined />
              </span>
              执行计划详情
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              {typedPlanDetail.name}
            </p>
          </div>
        </div>
        <Segmented
          value={viewMode}
          onChange={(v) => setViewMode(v as 'list' | 'flow' | 'gantt')}
          options={[
            { value: 'flow', icon: <ApartmentOutlined />, label: '流程图' },
            { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
            { value: 'gantt', icon: <BarChartOutlined />, label: '甘特图' },
          ]}
        />
      </div>

      {/* 操作按钮区 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Card size="small" className="!bg-gray-800/50">
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-400">计划时间:</span>
              <span className="text-white">{dayjs(typedPlanDetail.planned_start).format('YYYY-MM-DD HH:mm:ss')}</span>
              <span className="text-gray-500">→</span>
              <span className="text-white">{dayjs(typedPlanDetail.planned_end).format('YYYY-MM-DD HH:mm:ss')}</span>
              {typedPlanDetail.actual_start && (
                <>
                  <span className="text-gray-500 ml-4">|</span>
                  <span className="text-gray-400">实际开始:</span>
                  <span className="text-emerald-400">{dayjs(typedPlanDetail.actual_start).format('MM-DD HH:mm:ss')}</span>
                </>
              )}
            </div>
          </Card>
        </div>
        <div className="flex gap-3">
          {isNotStarted && (
            <Button 
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleStartPlan}
              loading={startPlan.isPending}
            >
              启动执行
            </Button>
          )}
          {isRunning && (
            <Button 
              size="large"
              icon={<PauseCircleOutlined />}
              onClick={handlePausePlan}
              loading={pausePlan.isPending}
            >
              暂停
            </Button>
          )}
          {isPaused && (
            <Button 
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleResumePlan}
              loading={resumePlan.isPending}
            >
              继续执行
            </Button>
          )}
          {isCompleted && (
            typedPlanDetail?.tracking_id ? (
              <Button 
                type="default"
                size="large"
                icon={<EyeOutlined />}
                onClick={handleViewTracking}
              >
                查看效果追踪
              </Button>
            ) : (
              <Button 
                type="primary"
                size="large"
                icon={<AimOutlined />}
                onClick={() => setTrackingConfigModalOpen(true)}
                loading={startTracking.isPending}
              >
                启动效果追踪
              </Button>
            )
          )}
        </div>
      </div>

      {/* 提示信息 */}
      {isNotStarted && (
        <Alert
          type="info"
          showIcon
          icon={<ThunderboltOutlined />}
          message="计划尚未启动"
          description="点击「启动执行」按钮开始执行任务。自动类型的任务会自动执行，手动类型的任务需要人工确认完成。"
          className="!bg-blue-500/10 !border-blue-500/30"
        />
      )}

      {/* 任务视图 */}
      <Card 
        title={
          <div className="flex items-center gap-2">
            <RocketOutlined className="text-green-400" />
            <span>执行{viewMode === 'flow' ? '流程图' : viewMode === 'list' ? '任务列表' : '甘特图'}</span>
            {typedTasksData && <Tag>{typedTasksData.total}个任务</Tag>}
          </div>
        }
      >
        {viewMode === 'flow' ? (
          typedTasksData?.items ? (
            <TaskFlowChart 
              planStatus={typedPlanDetail.status}
              planProgress={typedPlanDetail.progress}
              taskStats={typedPlanDetail.task_stats}
              tasks={typedTasksData?.items ?? []}
              templateId={typedPlanDetail.template_id}
              onTaskClick={(taskId) => {
                setSelectedTaskId(taskId);
                setTaskDetailModalOpen(true);
              }}
            />
          ) : (
            <Empty description="暂无任务" />
          )
        ) : viewMode === 'list' ? (
          typedTasksData?.items ? (
            <Table
              columns={taskColumns}
              dataSource={typedTasksData.items}
              rowKey="id"
              pagination={false}
              scroll={{ y: 400 }}
            />
          ) : (
            <Empty description="暂无任务" />
          )
        ) : (
          ganttData ? (
            <div className="h-[400px]">
              <GanttChart
                tasks={typedGanttData?.tasks || []}
                milestones={typedGanttData?.milestones || []}
                planStart={typedPlanDetail.planned_start}
                planEnd={typedPlanDetail.planned_end}
                onTaskClick={handleGanttTaskClick}
              />
            </div>
          ) : (
            <Empty description="暂无甘特图数据" />
          )
        )}
      </Card>

      {/* 任务详情弹窗 */}
      <Modal
        title="任务详情"
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
              <Descriptions.Item label="类型">
                <Tag color={taskTypeConfig[selectedTask.execution_type]?.color}>
                  {taskTypeConfig[selectedTask.execution_type]?.text || selectedTask.execution_type}
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

            {/* 半自动任务提示 */}
            {selectedTask.execution_type === 'semi_auto' && (
              <Alert
                message="需要人工验证配置"
                description={
                  <div className="mt-2">
                    <div className="mb-3 p-3 bg-blue-900/20 border border-blue-700/50 rounded-lg">
                      <p className="text-blue-300 font-medium mb-2">📋 操作步骤：</p>
                      <ol className="list-decimal list-inside space-y-2 text-gray-300 text-sm">
                        <li>
                          <strong>打开 CRM 系统</strong>
                          <div className="ml-6 mt-1">
                            <Button 
                              type="link" 
                              size="small" 
                              className="p-0 h-auto text-blue-400"
                              onClick={() => window.open('http://localhost:8001/docs', '_blank')}
                            >
                              🔗 点击访问 CRM 系统 (http://localhost:8001/docs)
                            </Button>
                          </div>
                        </li>
                        <li>
                          <strong>查看分配规则列表</strong>
                          <div className="ml-6 mt-1 text-xs text-gray-400">
                            在 Swagger 页面找到 <code className="bg-gray-800 px-1 rounded">GET /api/crm/rules/assignment</code> 接口
                            <br />
                            点击 "Try it out"，输入 API Key: <code className="bg-gray-800 px-1 rounded">mock-subsystem-api-key-12345</code>
                            <br />
                            点击 "Execute" 查看所有规则
                          </div>
                        </li>
                        <li>
                          <strong>验证规则配置</strong>
                          <div className="ml-6 mt-1 text-xs text-gray-400">
                            检查规则参数：
                            <ul className="list-disc list-inside ml-2 mt-1">
                              <li>规则名称是否合理</li>
                              <li>算法类型：应为 <code className="bg-gray-800 px-1 rounded">load_balanced</code>（负载均衡）</li>
                              <li>分配因子：应包含 <code className="bg-gray-800 px-1 rounded">capacity</code>、<code className="bg-gray-800 px-1 rounded">expertise</code>、<code className="bg-gray-800 px-1 rounded">availability</code></li>
                            </ul>
                          </div>
                        </li>
                        <li>
                          <strong>确认完成</strong>
                          <div className="ml-6 mt-1 text-xs text-gray-400">
                            如果规则配置正确，点击下方 <strong className="text-blue-400">「标记完成」</strong> 按钮
                            <br />
                            如果配置需要调整，在 CRM 系统中修改后，再标记完成
                          </div>
                        </li>
                      </ol>
                    </div>
                    {selectedTask.result?.rule_id && (
                      <div className="mt-3 p-2 bg-gray-800/50 rounded text-sm border border-blue-700/30">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-gray-400">规则ID:</span>
                          <span className="text-blue-400 font-mono">{selectedTask.result.rule_id}</span>
                        </div>
                        {selectedTask.result?.rule_name && (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-gray-500">规则名称:</span>
                            <span className="text-gray-300">{selectedTask.result.rule_name}</span>
                          </div>
                        )}
                        <div className="mt-2 text-xs text-gray-500">
                          💡 可在 CRM 系统中通过此 ID 查找对应规则
                        </div>
                      </div>
                    )}
                  </div>
                }
                type="info"
                showIcon
                icon={<ExclamationCircleOutlined />}
                className="mb-4"
              />
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

            <div className="flex justify-end gap-2 mt-4">
              {(selectedTask.status === 'ready' || selectedTask.status === 'running') && (
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
              )}
              {selectedTask.status === 'running' && (
                <Button 
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() => {
                    openFailModal(selectedTask.id);
                    setTaskDetailModalOpen(false);
                  }}
                >
                  标记失败
                </Button>
              )}
              {selectedTask.status === 'failed' && (
                <Button 
                  icon={<ReloadOutlined />}
                  onClick={() => {
                    handleRetryTask(selectedTask.id);
                    setTaskDetailModalOpen(false);
                  }}
                >
                  重试
                </Button>
              )}
            </div>
          </div>
        ) : (
          <Empty description="未选中任务" />
        )}
      </Modal>

      {/* 失败原因弹窗 */}
      <Modal
        title="标记任务失败"
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
            placeholder="例如：任务执行超时、资源不足等"
            rows={3}
          />
        </div>
      </Modal>

      {/* 效果追踪配置弹窗 */}
      <Modal
        title="配置效果追踪"
        open={trackingConfigModalOpen}
        onCancel={() => setTrackingConfigModalOpen(false)}
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

