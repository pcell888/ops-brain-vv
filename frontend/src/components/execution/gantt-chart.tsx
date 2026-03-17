

import { useMemo } from 'react';
import { Empty, Tag, Tooltip } from 'antd';
import dayjs from 'dayjs';
import clsx from 'clsx';

interface GanttTask {
  id: string;
  name: string;
  start: string;
  end: string;
  progress: number;
  dependencies: string[];
  status: string;
}

interface GanttMilestone {
  id: string;
  name: string;
  date: string;
}

interface GanttChartProps {
  tasks: GanttTask[];
  milestones?: GanttMilestone[];
  planStart?: string;
  planEnd?: string;
  onTaskClick?: (taskId: string) => void;
}

// 状态颜色
const statusColors: Record<string, { bg: string; border: string; text: string }> = {
  pending: { bg: 'bg-gray-600/50', border: 'border-gray-500', text: 'text-gray-300' },
  ready: { bg: 'bg-blue-600/50', border: 'border-blue-500', text: 'text-blue-300' },
  running: { bg: 'bg-cyan-600/50', border: 'border-cyan-400', text: 'text-cyan-300' },
  paused: { bg: 'bg-amber-600/50', border: 'border-amber-500', text: 'text-amber-300' },
  completed: { bg: 'bg-emerald-600/50', border: 'border-emerald-500', text: 'text-emerald-300' },
  failed: { bg: 'bg-rose-600/50', border: 'border-rose-500', text: 'text-rose-300' },
  cancelled: { bg: 'bg-gray-700/50', border: 'border-gray-600', text: 'text-gray-400' },
};

const statusLabels: Record<string, string> = {
  pending: '待执行',
  ready: '就绪',
  running: '执行中',
  paused: '已暂停',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

export function GanttChart({ 
  tasks, 
  milestones = [], 
  planStart, 
  planEnd,
  onTaskClick,
}: GanttChartProps) {
  // 计算时间范围
  const { startDate, endDate, totalDays, dayWidth } = useMemo(() => {
    if (tasks.length === 0) {
      const today = dayjs();
      return {
        startDate: today,
        endDate: today.add(30, 'day'),
        totalDays: 30,
        dayWidth: 30,
      };
    }

    let minDate = planStart ? dayjs(planStart) : dayjs(tasks[0].start);
    let maxDate = planEnd ? dayjs(planEnd) : dayjs(tasks[0].end);

    tasks.forEach((task) => {
      const taskStart = dayjs(task.start);
      const taskEnd = dayjs(task.end);
      if (taskStart.isBefore(minDate)) minDate = taskStart;
      if (taskEnd.isAfter(maxDate)) maxDate = taskEnd;
    });

    // 左右各留1天边距
    minDate = minDate.subtract(1, 'day');
    maxDate = maxDate.add(1, 'day');

    const days = maxDate.diff(minDate, 'day') + 1;
    
    return {
      startDate: minDate,
      endDate: maxDate,
      totalDays: days,
      dayWidth: Math.max(30, Math.min(50, 900 / days)),
    };
  }, [tasks, planStart, planEnd]);

  // 生成日期刻度
  const dateScale = useMemo(() => {
    const scale: { date: dayjs.Dayjs; isMonthStart: boolean; isWeekStart: boolean }[] = [];
    let current = startDate;
    
    while (current.isBefore(endDate) || current.isSame(endDate)) {
      scale.push({
        date: current,
        isMonthStart: current.date() === 1,
        isWeekStart: current.day() === 1, // 周一
      });
      current = current.add(1, 'day');
    }
    
    return scale;
  }, [startDate, endDate]);

  // 计算任务位置
  const getTaskPosition = (task: GanttTask) => {
    const taskStart = dayjs(task.start);
    const taskEnd = dayjs(task.end);
    const left = taskStart.diff(startDate, 'day') * dayWidth;
    const width = (taskEnd.diff(taskStart, 'day') + 1) * dayWidth;
    
    return { left, width };
  };

  // 计算里程碑位置
  const getMilestonePosition = (milestone: GanttMilestone) => {
    const date = dayjs(milestone.date);
    return date.diff(startDate, 'day') * dayWidth + dayWidth / 2;
  };

  if (tasks.length === 0) {
    return <Empty description="暂无任务数据" />;
  }

  const chartWidth = totalDays * dayWidth;

  return (
    <div className="overflow-x-auto">
      <div className="min-w-fit">
        {/* 时间轴头部 */}
        <div className="flex border-b border-gray-700 sticky top-0 bg-gray-900/95 z-10">
          {/* 任务名称列 */}
          <div className="w-48 flex-shrink-0 p-2 text-sm font-medium text-gray-400 border-r border-gray-700">
            任务名称
          </div>
          {/* 日期刻度 */}
          <div className="flex-1 overflow-hidden">
            <div className="flex" style={{ width: chartWidth }}>
              {dateScale.map((item, index) => (
                <div
                  key={index}
                  className={clsx(
                    'flex-shrink-0 text-center text-xs py-2 border-r border-gray-800',
                    item.isMonthStart && 'border-l-2 border-l-blue-500',
                    item.isWeekStart && 'bg-gray-800/30'
                  )}
                  style={{ width: dayWidth }}
                >
                  {item.isMonthStart ? (
                    <div>
                      <div className="text-blue-400 font-medium">{item.date.format('M月')}</div>
                      <div className="text-gray-500">{item.date.format('D')}</div>
                    </div>
                  ) : (
                    <div className="text-gray-500">{item.date.format('D')}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 任务行 */}
        {tasks.map((task, taskIndex) => {
          const { left, width } = getTaskPosition(task);
          const colors = statusColors[task.status] || statusColors.pending;
          
          return (
            <div 
              key={task.id}
              className="flex border-b border-gray-800 hover:bg-gray-800/30 transition-colors"
            >
              {/* 任务名称 */}
              <div 
                className="w-48 flex-shrink-0 p-2 border-r border-gray-700 cursor-pointer hover:bg-gray-800/50"
                onClick={() => onTaskClick?.(task.id)}
              >
                <div className="text-sm text-white truncate" title={task.name}>
                  {task.name}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {dayjs(task.start).format('MM-DD')} ~ {dayjs(task.end).format('MM-DD')}
                </div>
              </div>
              
              {/* 甘特条 */}
              <div className="flex-1 relative py-2" style={{ minHeight: 48 }}>
                <div 
                  className="absolute"
                  style={{ 
                    left, 
                    width,
                    top: '50%',
                    transform: 'translateY(-50%)',
                  }}
                >
                  <Tooltip 
                    title={
                      <div className="text-sm">
                        <div className="font-medium">{task.name}</div>
                        <div className="text-gray-300 mt-1">
                          {dayjs(task.start).format('YYYY-MM-DD')} ~ {dayjs(task.end).format('YYYY-MM-DD')}
                        </div>
                        <div className="mt-1">
                          状态: {statusLabels[task.status] || task.status}
                        </div>
                        <div>进度: {task.progress}%</div>
                      </div>
                    }
                  >
                    <div
                      className={clsx(
                        'h-7 rounded-md border-2 cursor-pointer transition-all hover:scale-[1.02]',
                        colors.bg,
                        colors.border
                      )}
                      onClick={() => onTaskClick?.(task.id)}
                    >
                      {/* 进度条 */}
                      <div 
                        className={clsx(
                          'h-full rounded-l-sm',
                          task.status === 'completed' ? 'bg-emerald-500/60' : 'bg-cyan-500/40'
                        )}
                        style={{ width: `${task.progress}%` }}
                      />
                      {/* 任务名称（如果空间足够） */}
                      {width > 80 && (
                        <div className={clsx(
                          'absolute inset-0 flex items-center justify-center text-xs font-medium truncate px-1',
                          colors.text
                        )}>
                          {task.name.length > width / 10 ? task.name.substring(0, Math.floor(width / 10)) + '...' : task.name}
                        </div>
                      )}
                    </div>
                  </Tooltip>
                </div>
              </div>
            </div>
          );
        })}

        {/* 里程碑行 */}
        {milestones.length > 0 && (
          <div className="flex border-t border-gray-700 bg-gray-800/30">
            <div className="w-48 flex-shrink-0 p-2 border-r border-gray-700">
              <span className="text-sm text-amber-400">📍 里程碑</span>
            </div>
            <div className="flex-1 relative py-3" style={{ width: chartWidth }}>
              {milestones.map((milestone) => {
                const left = getMilestonePosition(milestone);
                return (
                  <Tooltip key={milestone.id} title={`${milestone.name} - ${dayjs(milestone.date).format('YYYY-MM-DD')}`}>
                    <div
                      className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 cursor-pointer"
                      style={{ left }}
                    >
                      <div className="w-4 h-4 bg-amber-500 rotate-45 border-2 border-amber-400 shadow-lg shadow-amber-500/30" />
                    </div>
                  </Tooltip>
                );
              })}
            </div>
          </div>
        )}

        {/* 图例 */}
        <div className="flex gap-4 mt-4 p-3 bg-gray-800/30 rounded-lg">
          <span className="text-sm text-gray-400">图例:</span>
          {Object.entries(statusLabels).slice(0, 5).map(([status, label]) => {
            const colors = statusColors[status];
            return (
              <div key={status} className="flex items-center gap-1">
                <div className={clsx('w-4 h-3 rounded-sm border', colors.bg, colors.border)} />
                <span className="text-xs text-gray-400">{label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

