

import React, { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
  Handle,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FLOW_LAYOUT, FLOW_LAYOUT_PRESETS } from '@/lib/flow-layout';
import { Tag, Progress, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  PauseCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  RocketOutlined,
  FlagOutlined,
} from '@ant-design/icons';
import clsx from 'clsx';
import type { ExecutionTask, TaskStats } from '@/lib/types';

interface TaskFlowChartProps {
  planStatus: string;
  planProgress: number;
  taskStats?: TaskStats;
  tasks: ExecutionTask[];
  templateId?: string;
  onTaskClick?: (taskId: string) => void;
}

// 状态配置
const statusConfig: Record<string, {
  bgColor: string;
  borderColor: string;
  textColor: string;
  icon: React.ReactNode;
  text: string;
}> = {
  pending: {
    bgColor: '#0f172a',
    borderColor: '#334155',
    textColor: '#94a3b8',
    icon: <ClockCircleOutlined />,
    text: '待执行'
  },
  ready: {
    bgColor: '#0c4a6e',
    borderColor: '#0ea5e9',
    textColor: '#38bdf8',
    icon: <ClockCircleOutlined />,
    text: '就绪'
  },
  running: {
    bgColor: '#064e3b',
    borderColor: '#10b981',
    textColor: '#34d399',
    icon: <SyncOutlined spin />,
    text: '执行中'
  },
  paused: {
    bgColor: '#78350f',
    borderColor: '#f59e0b',
    textColor: '#fbbf24',
    icon: <PauseCircleOutlined />,
    text: '已暂停'
  },
  completed: {
    bgColor: '#064e3b',
    borderColor: '#10b981',
    textColor: '#34d399',
    icon: <CheckCircleOutlined />,
    text: '已完成'
  },
  failed: {
    bgColor: '#7f1d1d',
    borderColor: '#ef4444',
    textColor: '#f87171',
    icon: <ExclamationCircleOutlined />,
    text: '失败'
  },
  cancelled: {
    bgColor: '#1e293b',
    borderColor: '#475569',
    textColor: '#94a3b8',
    icon: <CloseCircleOutlined />,
    text: '已取消'
  },
  skipped: {
    bgColor: '#0c4a6e',
    borderColor: '#0ea5e9',
    textColor: '#38bdf8',
    icon: <CheckCircleOutlined />,
    text: '跳过'
  },
};

// 自定义任务节点
function TaskNode({ data }: { data: any }) {
  const status = statusConfig[data.status] || statusConfig.pending;
  const isActive = ['ready', 'running', 'paused', 'failed'].includes(data.status);
  const isCompleted = data.status === 'completed';

  return (
    <div className="relative cursor-pointer group">
      <Handle 
        type="target" 
        position={Position.Left} 
        className="!w-2 !h-2 !rounded-full !border-0 !-left-1"
        style={{ backgroundColor: status.borderColor }}
      />
      
      <div
        className={clsx(
          'px-3 py-2 rounded-md transition-all min-w-[140px] max-w-[200px]',
          'group-hover:brightness-110',
          data.status === 'running' && 'animate-pulse',
        )}
        style={{
          backgroundColor: status.bgColor,
          border: `1.5px solid ${status.borderColor}`,
          boxShadow: isActive ? `0 0 12px ${status.borderColor}40` : 'none',
        }}
      >
        {/* 标题行 */}
        <div className="flex items-center gap-1.5 min-w-0">
          <span style={{ color: status.textColor }} className="text-xs shrink-0">
            {status.icon}
          </span>
          <Tooltip title={data.label}>
            <span className="text-white font-medium text-xs truncate block max-w-[160px]">
              {data.label}
            </span>
          </Tooltip>
        </div>
        
        {/* 状态和进度 */}
        <div className="flex items-center justify-between mt-1.5">
          <span 
            className="text-[10px]"
            style={{ color: status.textColor }}
          >
            {status.text}
          </span>
          <span className="text-[10px] text-slate-500">
            {data.progress || 0}%
          </span>
        </div>
      </div>

      {/* 状态指示器 */}
      {isActive && (
        <div className="absolute -top-1 -right-1 z-10">
          <span className="relative flex h-3 w-3">
            <span 
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
              style={{ backgroundColor: status.borderColor }}
            />
            <span 
              className="relative inline-flex rounded-full h-3 w-3"
              style={{ backgroundColor: status.borderColor }}
            />
          </span>
        </div>
      )}
      
      <Handle 
        type="source" 
        position={Position.Right} 
        className="!w-2 !h-2 !rounded-full !border-0 !-right-1"
        style={{ backgroundColor: status.borderColor }}
      />
    </div>
  );
}

// 计划状态节点（开始/结束）
function PlanNode({ data }: { data: any }) {
  const isStart = data.type === 'start';
  const isEnd = data.type === 'end';
  const isActive = data.isActive || (isStart && data.started);
  const isRunning = data.status === 'running';
  const isCompleted = data.status === 'completed';
  
  let bgColor = '#1e293b';
  let borderColor = '#475569';
  let textColor = '#94a3b8';
  
  if (isActive || (isStart && data.started)) {
    bgColor = '#064e3b';
    borderColor = '#10b981';
    textColor = '#34d399';
  }
  if (isRunning && isStart) {
    bgColor = '#064e3b';
    borderColor = '#10b981';
    textColor = '#34d399';
  }
  if (isCompleted && isEnd) {
    bgColor = '#064e3b';
    borderColor = '#10b981';
    textColor = '#34d399';
  }

  return (
    <div className="flex flex-col items-center">
      <div
        className={clsx(
          'w-10 h-10 rounded-full flex items-center justify-center transition-all',
          (isRunning && isStart) && 'ring-2 ring-emerald-500/40',
        )}
        style={{
          backgroundColor: bgColor,
          border: `1.5px solid ${borderColor}`,
          boxShadow: isActive ? `0 0 16px ${borderColor}50` : 'none',
        }}
      >
        {!isStart && (
          <Handle 
            type="target" 
            position={Position.Left} 
            className="!w-2 !h-2 !rounded-full !border-0 !-left-1"
            style={{ backgroundColor: borderColor }}
          />
        )}
        
        <span style={{ color: textColor }} className="text-base">
          {isStart ? <RocketOutlined /> : <FlagOutlined />}
        </span>
        
        {!isEnd && (
          <Handle 
            type="source" 
            position={Position.Right} 
            className="!w-2 !h-2 !rounded-full !border-0 !-right-1"
            style={{ backgroundColor: borderColor }}
          />
        )}
      </div>
      <span 
        className="mt-1 text-[10px]"
        style={{ color: textColor }}
      >
        {isStart ? '开始' : '完成'}
      </span>
    </div>
  );
}

// 节点类型映射
const nodeTypes = {
  task: TaskNode,
  plan: PlanNode,
};

export function TaskFlowChart({ planStatus, planProgress, taskStats, tasks, templateId, onTaskClick }: TaskFlowChartProps) {
  const preset = templateId ? FLOW_LAYOUT_PRESETS[templateId] : undefined;

  // 有预设时使用模板布局，否则用通用算法
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!tasks || tasks.length === 0) {
      return { initialNodes: [], initialEdges: [] };
    }

    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const taskMap = new Map<string, ExecutionTask>();
    tasks.forEach((t) => taskMap.set(t.task_key || t.id, t));

    const getPosition = (id: string, fallback: { x: number; y: number }) =>
      preset?.[id] ?? fallback;

    const taskLevels = new Map<string, number>();
    const getLevel = (task: ExecutionTask, visited: Set<string> = new Set()): number => {
      const key = task.task_key || task.id;
      if (taskLevels.has(key)) return taskLevels.get(key)!;
      if (visited.has(key)) return 0;
      visited.add(key);
      if (!task.dependencies || task.dependencies.length === 0) {
        taskLevels.set(key, 0);
        return 0;
      }
      let maxDepLevel = -1;
      for (const depKey of task.dependencies) {
        const dep = taskMap.get(depKey);
        if (dep) maxDepLevel = Math.max(maxDepLevel, getLevel(dep, visited));
      }
      taskLevels.set(key, maxDepLevel + 1);
      return maxDepLevel + 1;
    };
    tasks.forEach((t) => getLevel(t));

    const levelGroups = new Map<number, ExecutionTask[]>();
    tasks.forEach((task) => {
      const level = taskLevels.get(task.task_key || task.id) || 0;
      if (!levelGroups.has(level)) levelGroups.set(level, []);
      levelGroups.get(level)!.push(task);
    });

    const hasSuccessor = new Set<string>();
    tasks.forEach((task) => {
      task.dependencies?.forEach((dep) => hasSuccessor.add(dep));
    });

    const isStarted = ['running', 'paused', 'completed', 'failed'].includes(planStatus);
    const startTasks: string[] = [];
    const endTasks: string[] = [];
    const { startX, startNodeX, mainY, horizontalGap, verticalGap, endNodeOffset } = FLOW_LAYOUT;
    const maxLevel = Math.max(...Array.from(levelGroups.keys()), 0);

    nodes.push({
      id: 'start',
      type: 'plan',
      position: getPosition('start', { x: startNodeX, y: mainY }),
      data: {
        type: 'start',
        label: '开始',
        started: isStarted,
        isActive: planStatus === 'running',
        status: planStatus,
      },
    });

    for (let level = 0; level <= maxLevel; level++) {
      const group = levelGroups.get(level) || [];
      const x = startX + level * horizontalGap;
      const startY = mainY - ((group.length - 1) * verticalGap) / 2;

      group.forEach((task, idx) => {
        const key = task.task_key || task.id;
        const y = startY + idx * verticalGap;

        nodes.push({
          id: key,
          type: 'task',
          position: getPosition(key, { x, y }),
          data: {
            label: task.name,
            status: task.status,
            progress: task.progress,
            taskId: task.id,
          },
        });
        if (!task.dependencies?.length) startTasks.push(key);
        if (!hasSuccessor.has(key)) endTasks.push(key);
        task.dependencies?.forEach((depKey) => {
          const dep = taskMap.get(depKey);
          if (!dep) return;
          const ok = dep.status === 'completed';
          edges.push({
            id: `${depKey}-${key}`,
            source: depKey,
            target: key,
            type: 'smoothstep',
            animated: dep.status === 'running',
            style: { stroke: ok ? '#10b981' : '#475569', strokeWidth: 1.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: ok ? '#10b981' : '#475569', width: 12, height: 12 },
          });
        });
      });
    }

    startTasks.forEach((key) => {
      edges.push({
        id: `start-${key}`,
        source: 'start',
        target: key,
        type: 'smoothstep',
        animated: planStatus === 'running',
        style: { stroke: isStarted ? '#10b981' : '#475569', strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: isStarted ? '#10b981' : '#475569', width: 12, height: 12 },
      });
    });

    const endX = startX + (maxLevel + 1) * horizontalGap + endNodeOffset;
    nodes.push({
      id: 'end',
      type: 'plan',
      position: getPosition('end', { x: endX, y: mainY }),
      data: { type: 'end', label: '完成', isActive: planStatus === 'completed', status: planStatus },
    });

    endTasks.forEach((key) => {
      const task = taskMap.get(key);
      const ok = task?.status === 'completed';
      edges.push({
        id: `${key}-end`,
        source: key,
        target: 'end',
        type: 'smoothstep',
        animated: false,
        style: { stroke: ok ? '#10b981' : '#475569', strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: ok ? '#10b981' : '#475569', width: 12, height: 12 },
      });
    });

    return { initialNodes: nodes, initialEdges: edges };
  }, [tasks, planStatus, preset]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // 更新节点和边
  React.useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === 'task' && onTaskClick) {
      onTaskClick(node.data.taskId as string);
    }
  }, [onTaskClick]);

  // 统计显示
  const statsDisplay = taskStats ? [
    { label: '待执行', value: taskStats.pending || 0, color: '#9ca3af' },
    { label: '就绪', value: taskStats.ready || 0, color: '#60a5fa' },
    { label: '执行中', value: taskStats.running || 0, color: '#4ade80' },
    { label: '已完成', value: taskStats.completed || 0, color: '#34d399' },
    { label: '失败', value: taskStats.failed || 0, color: '#f87171' },
  ] : [];

  if (tasks.length === 0) {
    return (
      <div className="text-center text-gray-500 py-10">
        暂无任务数据
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 进度和统计 */}
      <div className="flex items-center justify-between bg-gray-800/50 rounded-lg p-4">
        <div className="flex items-center gap-4">
          <div>
            <div className="text-xs text-gray-500 mb-1">整体进度</div>
            <div className="flex items-center gap-2">
              <Progress
                percent={planProgress}
                size="small"
                showInfo={false}
                className="!w-32 !m-0"
                strokeColor={{
                  '0%': '#3b82f6',
                  '100%': '#10b981',
                }}
                trailColor="rgba(255,255,255,0.1)"
              />
              <span className={clsx(
                'text-lg font-bold',
                planProgress >= 100 ? 'text-emerald-400' : 'text-blue-400'
              )}>
                {planProgress}%
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-6">
          {statsDisplay.map(stat => (
            <div key={stat.label} className="text-center">
              <div className="text-lg font-bold" style={{ color: stat.color }}>
                {stat.value}
              </div>
              <div className="text-xs text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 流程图 */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/50" style={{ height: 500 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2, minZoom: 0.7, maxZoom: 1.5 }}
          proOptions={{ hideAttribution: true }}
          className="bg-transparent"
          minZoom={0.5}
          maxZoom={2}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
          panOnDrag={true}
          zoomOnScroll={true}
        >
          <Background color="#1e293b" gap={20} size={1} />
        </ReactFlow>
      </div>

      {/* 图例 */}
      <div className="flex items-center justify-center gap-6 flex-wrap text-xs text-gray-500">
        <span className="font-medium">状态:</span>
        {Object.entries(statusConfig).slice(0, 6).map(([key, config]) => (
          <span key={key} className="flex items-center gap-1">
            <span 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: config.borderColor }}
            />
            {config.text}
          </span>
        ))}
      </div>
    </div>
  );
}
