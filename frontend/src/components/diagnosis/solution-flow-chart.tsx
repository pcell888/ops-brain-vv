

import { Card, Tag, Empty, Tooltip } from 'antd';
import { 
  WarningOutlined, 
  TagsOutlined, 
  BulbOutlined, 
  ArrowRightOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import clsx from 'clsx';
import { getTagLabel } from '@/lib/tag-labels';

export interface AnomalyFlowItem {
  id: string;
  name: string;
  severity: 'severe' | 'moderate' | 'critical' | 'high' | 'medium' | 'low';
  currentValue?: string;
  solutionTags: string[];
}

export interface SolutionFlowItem {
  id: string;
  name: string;
  category: string;
  applicableTags: string[];
  score?: number;
}

interface SolutionFlowChartProps {
  anomalies: AnomalyFlowItem[];
  solutions: SolutionFlowItem[];
  className?: string;
}

// 方案类别显示
const categoryDisplay: Record<string, { label: string; color: string }> = {
  sales_process: { label: '销售流程', color: 'blue' },
  marketing_optimization: { label: '营销优化', color: 'purple' },
  customer_retention: { label: '客户留存', color: 'green' },
  efficiency_improvement: { label: '效率提升', color: 'orange' },
};

export function SolutionFlowChart({ anomalies, solutions, className }: SolutionFlowChartProps) {
  if (anomalies.length === 0) {
    return (
      <Empty 
        description="暂无异常指标数据" 
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  // 收集所有唯一的标签
  const allTags = Array.from(new Set(anomalies.flatMap(a => a.solutionTags)));

  // 构建标签到异常的映射
  const tagToAnomalies: Record<string, AnomalyFlowItem[]> = {};
  anomalies.forEach(anomaly => {
    anomaly.solutionTags.forEach(tag => {
      if (!tagToAnomalies[tag]) {
        tagToAnomalies[tag] = [];
      }
      tagToAnomalies[tag].push(anomaly);
    });
  });

  // 构建标签到方案的映射
  const tagToSolutions: Record<string, SolutionFlowItem[]> = {};
  solutions.forEach(solution => {
    solution.applicableTags.forEach(tag => {
      if (!tagToSolutions[tag]) {
        tagToSolutions[tag] = [];
      }
      tagToSolutions[tag].push(solution);
    });
  });

  return (
    <Card 
      title={
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-sm shadow-lg shadow-cyan-500/20">
            <ThunderboltOutlined />
          </span>
          <span className="text-base font-semibold">异常指标 → 方案生成流程</span>
        </div>
      }
      className={className}
    >
      <div className="relative">
        {/* 流程图主体 */}
        <div className="flex items-stretch gap-4 overflow-x-auto pb-4">
          {/* 第一列: 异常指标 */}
          <div className="flex-shrink-0 w-64">
            <div className="text-center mb-3">
              <Tag icon={<WarningOutlined />} color="red" className="!px-3 !py-1 !text-sm">
                异常指标
              </Tag>
            </div>
            <div className="space-y-2">
              {anomalies.map((anomaly) => (
                <Tooltip 
                  key={anomaly.id}
                  title={
                    <div>
                      <div className="font-medium mb-1">{anomaly.name}</div>
                      <div className="text-xs text-gray-400">
                        关联标签: {anomaly.solutionTags.map(t => getTagLabel(t)).join(', ')}
                      </div>
                    </div>
                  }
                >
                  <div className={clsx(
                    'p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.02]',
                    anomaly.severity === 'severe' || anomaly.severity === 'critical' || anomaly.severity === 'high'
                      ? 'border-rose-500/40 bg-rose-500/10 hover:bg-rose-500/20'
                      : 'border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20'
                  )}>
                    <div className="text-sm font-medium text-white truncate mb-1">
                      {anomaly.name}
                    </div>
                    {anomaly.currentValue && (
                      <div className={clsx(
                        'text-lg font-bold',
                        anomaly.severity === 'severe' || anomaly.severity === 'critical' || anomaly.severity === 'high'
                          ? 'text-rose-400'
                          : 'text-amber-400'
                      )}>
                        {anomaly.currentValue}
                      </div>
                    )}
                  </div>
                </Tooltip>
              ))}
            </div>
          </div>

          {/* 箭头连接 */}
          <div className="flex-shrink-0 flex items-center">
            <div className="flex flex-col items-center gap-1">
              <ArrowRightOutlined className="text-2xl text-cyan-400 animate-pulse" />
              <span className="text-xs text-gray-500">匹配</span>
            </div>
          </div>

          {/* 第二列: 方案标签 */}
          <div className="flex-shrink-0 w-48">
            <div className="text-center mb-3">
              <Tag icon={<TagsOutlined />} color="cyan" className="!px-3 !py-1 !text-sm">
                方案标签
              </Tag>
            </div>
            <div className="space-y-2">
              {allTags.map((tag) => (
                <Tooltip
                  key={tag}
                  title={
                    <div>
                      <div className="font-medium mb-1">{getTagLabel(tag)}</div>
                      <div className="text-xs text-gray-400">
                        关联 {tagToAnomalies[tag]?.length || 0} 个异常，
                        匹配 {tagToSolutions[tag]?.length || 0} 个方案
                      </div>
                    </div>
                  }
                >
                  <div className="p-3 rounded-lg border border-cyan-500/40 bg-cyan-500/10 hover:bg-cyan-500/20 cursor-pointer transition-all hover:scale-[1.02]">
                    <div className="flex items-center gap-2">
                      <TagsOutlined className="text-cyan-400" />
                      <span className="text-sm font-medium text-white">
                        {getTagLabel(tag)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                      <span className="text-rose-400">{tagToAnomalies[tag]?.length || 0} 异常</span>
                      <span>→</span>
                      <span className="text-emerald-400">{tagToSolutions[tag]?.length || 0} 方案</span>
                    </div>
                  </div>
                </Tooltip>
              ))}
            </div>
          </div>

          {/* 箭头连接 */}
          <div className="flex-shrink-0 flex items-center">
            <div className="flex flex-col items-center gap-1">
              <ArrowRightOutlined className="text-2xl text-emerald-400 animate-pulse" />
              <span className="text-xs text-gray-500">生成</span>
            </div>
          </div>

          {/* 第三列: 推荐方案 */}
          <div className="flex-shrink-0 w-72">
            <div className="text-center mb-3">
              <Tag icon={<BulbOutlined />} color="gold" className="!px-3 !py-1 !text-sm">
                推荐方案
              </Tag>
            </div>
            <div className="space-y-2">
              {solutions.length > 0 ? (
                solutions.map((solution, index) => {
                  const catConfig = categoryDisplay[solution.category] || { label: solution.category, color: 'default' };
                  return (
                    <Tooltip
                      key={solution.id}
                      title={
                        <div>
                          <div className="font-medium mb-1">{solution.name}</div>
                          <div className="text-xs text-gray-400">
                            适用标签: {solution.applicableTags.map(t => getTagLabel(t)).join(', ')}
                          </div>
                        </div>
                      }
                    >
                      <div className={clsx(
                        'p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.02]',
                        index === 0 
                          ? 'border-amber-500/60 bg-gradient-to-r from-amber-500/20 to-transparent'
                          : 'border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20'
                      )}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            {index === 0 && (
                              <span className="w-5 h-5 rounded-full bg-amber-500/30 text-amber-400 flex items-center justify-center text-xs">
                                1
                              </span>
                            )}
                            <span className="text-sm font-medium text-white truncate max-w-[180px]">
                              {solution.name}
                            </span>
                          </div>
                          {solution.score && (
                            <span className={clsx(
                              'text-sm font-bold',
                              solution.score >= 80 ? 'text-emerald-400' : 'text-amber-400'
                            )}>
                              {solution.score}分
                            </span>
                          )}
                        </div>
                        <div className="flex items-center justify-between">
                          <Tag color={catConfig.color} className="!m-0 !text-xs">
                            {catConfig.label}
                          </Tag>
                          {index === 0 && (
                            <Tag color="gold" className="!m-0 !text-xs" icon={<CheckCircleOutlined />}>
                              推荐
                            </Tag>
                          )}
                        </div>
                      </div>
                    </Tooltip>
                  );
                })
              ) : (
                <div className="p-4 rounded-lg border border-dashed border-gray-600 text-center">
                  <BulbOutlined className="text-2xl text-gray-500 mb-2" />
                  <div className="text-sm text-gray-500">点击「生成方案」</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 底部说明 */}
        <div className="mt-4 pt-4 border-t border-gray-700/50">
          <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-500/50"></div>
              <span>异常指标</span>
            </div>
            <ArrowRightOutlined className="text-gray-600" />
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-cyan-500/50"></div>
              <span>方案标签匹配</span>
            </div>
            <ArrowRightOutlined className="text-gray-600" />
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-emerald-500/50"></div>
              <span>智能生成方案</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}



