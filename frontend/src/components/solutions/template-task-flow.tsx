

import React, { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
  Handle,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Tag, Tooltip } from 'antd';
import {
  ThunderboltOutlined,
  ToolOutlined,
  TeamOutlined,
  RocketOutlined,
  FlagOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import clsx from 'clsx';
import type { TemplateTask } from '@/lib/types';
import { FLOW_LAYOUT, FLOW_LAYOUT_PRESETS } from '@/lib/flow-layout';

interface TemplateTaskFlowProps {
  tasks: TemplateTask[];
  templateId?: string;
  onTaskClick?: (taskId: string) => void;
}

// 执行类型配置
const executionTypeConfig: Record<string, {
  bgColor: string;
  borderColor: string;
  textColor: string;
  icon: React.ReactNode;
  label: string;
}> = {
  auto: {
    bgColor: '#064e3b',
    borderColor: '#10b981',
    textColor: '#34d399',
    icon: <ThunderboltOutlined />,
    label: '自动'
  },
  semi_auto: {
    bgColor: '#78350f',
    borderColor: '#f59e0b',
    textColor: '#fbbf24',
    icon: <ToolOutlined />,
    label: '半自动'
  },
  manual: {
    bgColor: '#1e3a5f',
    borderColor: '#3b82f6',
    textColor: '#60a5fa',
    icon: <TeamOutlined />,
    label: '手动'
  },
};

// 自定义任务节点
function TemplateTaskNode({ data }: { data: any }) {
  const typeConfig = executionTypeConfig[data.executionType] || executionTypeConfig.manual;

  return (
    <Tooltip 
      title={
        <div className="text-xs">
          <div className="font-medium mb-1">{data.label}</div>
          <div className="text-gray-300">{data.description}</div>
          <div className="mt-1 text-gray-400">
            <ClockCircleOutlined className="mr-1" />
            预计 {data.duration} 天
          </div>
          {data.dependencies && data.dependencies.length > 0 && (
            <div className="mt-1 text-gray-400">
              依赖: {data.dependencies.join(', ')}
            </div>
          )}
        </div>
      }
      placement="top"
    >
      <div className="relative cursor-pointer group">
        <Handle 
          type="target" 
          position={Position.Left} 
          className="!w-2 !h-2 !rounded-full !border-0 !-left-1"
          style={{ backgroundColor: typeConfig.borderColor }}
        />
        
        <div
          className={clsx(
            'px-3 py-2.5 rounded-lg transition-all min-w-[140px]',
            'group-hover:brightness-110 group-hover:scale-105',
          )}
          style={{
            backgroundColor: typeConfig.bgColor,
            border: `2px solid ${typeConfig.borderColor}`,
            boxShadow: `0 4px 16px ${typeConfig.borderColor}30`,
          }}
        >
          {/* 序号标识 */}
          <div 
            className="absolute -top-2 -left-2 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
            style={{ 
              backgroundColor: typeConfig.borderColor,
              color: '#fff'
            }}
          >
            {data.index}
          </div>

          {/* 标题行 */}
          <div className="flex items-center gap-1.5 mb-1">
            <span style={{ color: typeConfig.textColor }} className="text-sm">
              {typeConfig.icon}
            </span>
            <span className="text-white font-medium text-xs truncate max-w-[100px]">
              {data.label}
            </span>
          </div>
          
          {/* 执行类型和时长 */}
          <div className="flex items-center justify-between">
            <span 
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ 
                backgroundColor: `${typeConfig.borderColor}30`,
                color: typeConfig.textColor 
              }}
            >
              {typeConfig.label}
            </span>
            <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
              <ClockCircleOutlined />
              {data.duration}天
            </span>
          </div>
        </div>
        
        <Handle 
          type="source" 
          position={Position.Right} 
          className="!w-2 !h-2 !rounded-full !border-0 !-right-1"
          style={{ backgroundColor: typeConfig.borderColor }}
        />
      </div>
    </Tooltip>
  );
}

// 开始/结束节点
function FlowEndpointNode({ data }: { data: any }) {
  const isStart = data.type === 'start';
  
  const bgColor = isStart ? '#064e3b' : '#312e81';
  const borderColor = isStart ? '#10b981' : '#6366f1';
  const textColor = isStart ? '#34d399' : '#a5b4fc';

  return (
    <div className="flex flex-col items-center">
      <div
        className="w-11 h-11 rounded-full flex items-center justify-center transition-all"
        style={{
          backgroundColor: bgColor,
          border: `2px solid ${borderColor}`,
          boxShadow: `0 0 20px ${borderColor}40`,
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
        
        <span style={{ color: textColor }} className="text-lg">
          {isStart ? <RocketOutlined /> : <FlagOutlined />}
        </span>
        
        {isStart && (
          <Handle 
            type="source" 
            position={Position.Right} 
            className="!w-2 !h-2 !rounded-full !border-0 !-right-1"
            style={{ backgroundColor: borderColor }}
          />
        )}
      </div>
      <span 
        className="mt-1.5 text-[11px] font-medium"
        style={{ color: textColor }}
      >
        {isStart ? '开始' : '完成'}
      </span>
    </div>
  );
}

// 节点类型映射
const nodeTypes = {
  templateTask: TemplateTaskNode,
  endpoint: FlowEndpointNode,
};

export function TemplateTaskFlow({ tasks, templateId, onTaskClick }: TemplateTaskFlowProps) {
  const preset = templateId ? FLOW_LAYOUT_PRESETS[templateId] : undefined;

  const { initialNodes, initialEdges, totalDuration } = useMemo(() => {
    if (!tasks || tasks.length === 0) {
      return { initialNodes: [], initialEdges: [], totalDuration: 0 };
    }

    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const taskMap = new Map<string, TemplateTask>();
    tasks.forEach((t) => taskMap.set(t.task_id, t));

    const taskLevels = new Map<string, number>();
    const getLevel = (task: TemplateTask, visited: Set<string> = new Set()): number => {
      const key = task.task_id;
      if (taskLevels.has(key)) return taskLevels.get(key)!;
      if (visited.has(key)) return 0;
      visited.add(key);
      if (!task.dependencies || task.dependencies.length === 0) {
        taskLevels.set(key, 0);
        return 0;
      }
      let maxDepLevel = -1;
      for (const depKey of task.dependencies) {
        const depTask = taskMap.get(depKey);
        if (depTask) maxDepLevel = Math.max(maxDepLevel, getLevel(depTask, visited));
      }
      taskLevels.set(key, maxDepLevel + 1);
      return maxDepLevel + 1;
    };
    tasks.forEach((t) => getLevel(t));

    const levelGroups = new Map<number, TemplateTask[]>();
    tasks.forEach((task) => {
      const level = taskLevels.get(task.task_id) || 0;
      if (!levelGroups.has(level)) levelGroups.set(level, []);
      levelGroups.get(level)!.push(task);
    });

    const { startX, startNodeX, mainY, horizontalGap, verticalGap, endNodeOffset } = FLOW_LAYOUT;
    const maxLevel = Math.max(...Array.from(levelGroups.keys()), 0);
    const hasSuccessor = new Set<string>();
    tasks.forEach((task) => {
      task.dependencies?.forEach((dep) => hasSuccessor.add(dep));
    });

    const startTasks: string[] = [];
    const endTasks: string[] = [];
    let totalDays = 0;

    const getPosition = (id: string, fallback: { x: number; y: number }) =>
      preset?.[id] ?? fallback;

    nodes.push({
      id: 'start',
      type: 'endpoint',
      position: getPosition('start', { x: startNodeX, y: mainY }),
      data: { type: 'start' },
    });

    for (let level = 0; level <= maxLevel; level++) {
      const group = levelGroups.get(level) || [];
      const x = startX + level * horizontalGap;
      const startY = mainY - ((group.length - 1) * verticalGap) / 2;

      group.forEach((task, groupIndex) => {
        const key = task.task_id;
        const y = startY + groupIndex * verticalGap;
        const taskIndex = tasks.findIndex((t) => t.task_id === key) + 1;
        totalDays += task.duration_days;

        nodes.push({
          id: key,
          type: 'templateTask',
          position: getPosition(key, { x, y }),
          data: {
            label: task.name,
            description: task.description,
            executionType: task.execution_type,
            duration: task.duration_days,
            dependencies: task.dependencies,
            taskId: task.task_id,
            index: taskIndex,
          },
        });
        if (!task.dependencies?.length) startTasks.push(key);
        if (!hasSuccessor.has(key)) endTasks.push(key);
        task.dependencies?.forEach((depKey) => {
          const depTask = taskMap.get(depKey);
          if (!depTask) return;
          edges.push({
            id: `${depKey}-${key}`,
            source: depKey,
            target: key,
            type: 'smoothstep',
            animated: true,
            style: { stroke: '#6366f1', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1', width: 14, height: 14 },
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
        animated: true,
        style: { stroke: '#10b981', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981', width: 14, height: 14 },
      });
    });

    const endX = startX + (maxLevel + 1) * horizontalGap + endNodeOffset;
    nodes.push({
      id: 'end',
      type: 'endpoint',
      position: getPosition('end', { x: endX, y: mainY }),
      data: { type: 'end' },
    });

    endTasks.forEach((key) => {
      edges.push({
        id: `${key}-end`,
        source: key,
        target: 'end',
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#6366f1', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1', width: 14, height: 14 },
      });
    });

    return { initialNodes: nodes, initialEdges: edges, totalDuration: totalDays };
  }, [tasks, preset]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // 更新节点和边
  React.useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === 'templateTask' && onTaskClick) {
      onTaskClick(node.data.taskId as string);
    }
  }, [onTaskClick]);

  // 统计任务类型
  const typeStats = useMemo(() => {
    const stats = { auto: 0, semi_auto: 0, manual: 0 };
    tasks.forEach(task => {
      if (stats[task.execution_type as keyof typeof stats] !== undefined) {
        stats[task.execution_type as keyof typeof stats]++;
      }
    });
    return stats;
  }, [tasks]);

  if (tasks.length === 0) {
    return (
      <div className="text-center text-gray-500 py-10">
        暂无任务数据
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 统计信息 */}
      <div className="flex items-center justify-between bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">{tasks.length}</div>
            <div className="text-xs text-secondary">总任务数</div>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div className="text-center">
            <div className="text-2xl font-bold text-amber-600">{totalDuration}</div>
            <div className="text-xs text-secondary">总耗时(天)</div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {Object.entries(executionTypeConfig).map(([key, config]) => (
            <div key={key} className="flex items-center gap-2">
              <span 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: config.borderColor }}
              />
              <span className="text-xs text-secondary">
                {config.label}: <span className="font-medium text-primary">{typeStats[key as keyof typeof typeStats]}</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 流程图 */}
      <div className="h-[480px] bg-[#F0F1F9] rounded-xl border border-gray-200 overflow-hidden">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2, minZoom: 0.6, maxZoom: 1.5 }}
          proOptions={{ hideAttribution: true }}
          className="bg-transparent"
          minZoom={0.3}
          maxZoom={2}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
          panOnDrag={true}
          zoomOnScroll={true}
        >
          <Background color="#f0f2f5" gap={24} size={1} />
          <Controls 
            className="!bg-[#F0F1F9] !border-gray-200 !rounded-lg [&>button]:!bg-[#F0F1F9] [&>button]:!border-gray-200 [&>button]:!text-gray-600 [&>button:hover]:!bg-gray-100"
            showInteractive={false}
          />
        </ReactFlow>
      </div>

      {/* 提示 */}
      <div className="text-center text-xs text-secondary">
        💡 鼠标悬停任务节点可查看详情，支持拖拽和缩放
      </div>
    </div>
  );
}

