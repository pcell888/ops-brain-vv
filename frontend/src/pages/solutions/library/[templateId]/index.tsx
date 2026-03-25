

import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, 
  Spin, 
  Tag, 
  Progress, 
  Button, 
  Descriptions, 
  Timeline, 
  Row, 
  Col,
  Statistic,
  Divider,
  Empty,
} from 'antd';
import { 
  ArrowLeftOutlined,
  AppstoreOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  TagsOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  AimOutlined,
  TeamOutlined,
  ToolOutlined,
  LoadingOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { useSolutionTemplateDetail } from '@/lib/hooks';
import type { SolutionTemplateDetail, TemplateTask } from '@/lib/types';
import { TemplateTaskFlow } from '@/components/solutions/template-task-flow';
import { getTagLabel } from '@/lib/tag-labels';
import { getTaskDoc } from '@/lib/task-docs';

// 分类配置（与后端 SolutionCategory 一致）
const categoryConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  sales_process: { label: '销售流程', color: 'blue', icon: <TeamOutlined /> },
  marketing_optimization: { label: '营销优化', color: 'purple', icon: <RocketOutlined /> },
  customer_retention: { label: '客户留存', color: 'green', icon: <AimOutlined /> },
  efficiency_improvement: { label: '效率提升', color: 'orange', icon: <ThunderboltOutlined /> },
};

// 执行类型配置
const executionTypeConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  auto: { label: '自动执行', color: 'green', icon: <ThunderboltOutlined /> },
  semi_auto: { label: '半自动', color: 'orange', icon: <ToolOutlined /> },
  manual: { label: '人工执行', color: 'default', icon: <TeamOutlined /> },
};


export default function TemplateDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const templateId = params.templateId as string;
  
  const { data: rawTemplate, isLoading, error } = useSolutionTemplateDetail(templateId);
  const template = rawTemplate as SolutionTemplateDetail | undefined;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }

  if (error || !template) {
    return (
      <div className="space-y-6">
        <Button 
          icon={<ArrowLeftOutlined />}
          style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }} 
          onClick={() => navigate(-1)}
        >
          返回
        </Button>
        <Empty description="模板不存在或加载失败" />
      </div>
    );
  }

  const categoryInfo = categoryConfig[template.category] || { 
    label: template.category, 
    color: 'default',
    icon: <AppstoreOutlined />
  };

  // 计算任务类型统计
  const taskTypeStats = template.tasks?.reduce((acc: Record<string, number>, task) => {
    acc[task.execution_type] = (acc[task.execution_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  return (
    <div className="space-y-6">
      {/* 顶部导航栏 */}
      <div className="flex items-center justify-between">
        <Button 
          type="text"
          icon={<ArrowLeftOutlined />}
          style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }} 
          onClick={() => navigate('/solutions/library')}
          className="text-gray-400 hover:text-white"
        >
          返回方案库
        </Button>
      </div>

      {/* 模板头部信息 */}
      <Card className="overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-start gap-6">
          {/* 左侧：基本信息 */}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-4">
              <span className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xl shadow-lg shadow-indigo-500/20">
                {categoryInfo.icon}
              </span>
              <div>
                <h1 className="text-2xl font-bold text-white">{template.name}</h1>
                <div className="flex items-center gap-2 mt-1">
                  <Tag style={{ backgroundColor: `${categoryInfo.color}20`, color: categoryInfo.color, border: 'none' }}>{categoryInfo.label}</Tag>
                  <span className="text-gray-400 text-sm">ID: {template.template_id}</span>
                </div>
              </div>
            </div>
            
            <p className="text-gray-300 leading-relaxed mb-4">
              {template.description || '暂无描述'}
            </p>

            {/* 适用标签 */}
            {template.applicable_tags && template.applicable_tags.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <TagsOutlined className="text-gray-400" />
                <span className="text-gray-400 text-sm">适用场景：</span>
                {template.applicable_tags.map((tag) => (
                  <Tag key={tag} style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6', border: 'none' }} className="m-0">{getTagLabel(tag)}</Tag>
                ))}
              </div>
            )}
          </div>

          {/* 右侧：核心指标 */}
          <div className="lg:w-80">
            <div className="bg-gray-800/50 rounded-xl p-4">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Statistic
                    title={<span className="text-gray-400">成功率</span>}
                    value={template.success_rate * 100}
                    precision={0}
                    suffix="%"
                    valueStyle={{ 
                      color: template.success_rate >= 0.8 ? '#10b981' : template.success_rate >= 0.6 ? '#f59e0b' : '#ef4444',
                      fontSize: 28
                    }}
                    prefix={<CheckCircleOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span className="text-gray-400">任务数量</span>}
                    value={template.task_count}
                    suffix="个"
                    valueStyle={{ color: '#8b5cf6', fontSize: 28 }}
                    prefix={<RocketOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span className="text-gray-400">预估成本</span>}
                    value={template.estimated_cost >= 10000 
                      ? template.estimated_cost / 10000 
                      : template.estimated_cost}
                    precision={template.estimated_cost >= 10000 ? 1 : 0}
                    suffix={template.estimated_cost >= 10000 ? '万' : '元'}
                    prefix={<DollarOutlined />}
                    valueStyle={{ color: '#3b82f6', fontSize: 28 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span className="text-gray-400">执行周期</span>}
                    value={template.estimated_duration_days}
                    suffix="天"
                    valueStyle={{ color: '#f59e0b', fontSize: 28 }}
                    prefix={<ClockCircleOutlined />}
                  />
                </Col>
              </Row>
            </div>
          </div>
        </div>
      </Card>

      {/* 预期效果 */}
      {template.estimated_impact && Object.keys(template.estimated_impact).length > 0 && (
        <Card 
          title={
            <div className="flex items-center gap-2">
              <AimOutlined className="text-emerald-400" />
              <span>预期效果</span>
            </div>
          }
        >
          <Row gutter={[16, 16]}>
            {Object.entries(template.estimated_impact).map(([key, value]) => (
              <Col key={key} xs={12} sm={8} md={6}>
                <div className="bg-gray-800/50 rounded-xl p-4 text-center h-full">
                  <div className="text-gray-400 text-sm mb-2">{key}</div>
                  <div className="text-2xl font-bold text-emerald-400">
                    +{(value * 100).toFixed(0)}%
                  </div>
                  <Progress 
                    percent={value * 100} 
                    showInfo={false}
                    strokeColor="#10b981"
                    trailColor="rgba(255,255,255,0.1)"
                    size="small"
                    className="mt-2"
                  />
                </div>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* 任务流程图与说明 */}
      {template.tasks && template.tasks.length > 0 && (
        <Card
          title={
            <div className="flex items-center gap-2">
              <NodeIndexOutlined className="text-cyan-400" />
              <span>方案流程与任务说明</span>
              <Tag color="cyan">{template.task_count}个任务</Tag>
            </div>
          }
          className="border-cyan-500/20"
        >
          <p className="text-gray-400 text-sm mb-4">
            本方案由一组按依赖关系排列的任务组成。下图展示执行顺序与依赖；下方「执行任务清单」中每个任务均包含：<strong className="text-gray-300">任务作用</strong>（在方案中的价值）、<strong className="text-gray-300">工作原理</strong>（执行时系统具体做什么）。
          </p>
          <TemplateTaskFlow tasks={template.tasks} templateId={template.template_id} />
        </Card>
      )}

      {/* 任务列表详情 */}
      <Card 
        title={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RocketOutlined className="text-purple-400" />
              <span>执行任务清单</span>
              <Tag color="purple">{template.task_count}个任务</Tag>
            </div>
            <div className="flex items-center gap-2">
              {Object.entries(taskTypeStats).map(([type, count]) => {
                const config = executionTypeConfig[type] || { label: type, color: 'default' };
                return (
                  <Tag key={type} color={config.color}>
                    {config.label}: {count}
                  </Tag>
                );
              })}
            </div>
          </div>
        }
      >
        {template.tasks && template.tasks.length > 0 ? (
          <div className="space-y-4">
            {template.tasks.map((task, index) => (
              <TaskCard key={task.task_id} task={task} index={index} />
            ))}
          </div>
        ) : (
          <Empty description="暂无任务配置" />
        )}
      </Card>

      {/* 任务执行时间线 */}
      {template.tasks && template.tasks.length > 0 && (
        <Card
          title={
            <div className="flex items-center gap-2">
              <ClockCircleOutlined className="text-amber-400" />
              <span>执行时间线</span>
            </div>
          }
        >
          <Timeline
            mode="left"
            items={template.tasks.map((task, index) => {
              const typeConfig = executionTypeConfig[task.execution_type] || { label: task.execution_type, color: 'default' };
              const startDay = template.tasks!
                .slice(0, index)
                .reduce((sum, t) => sum + t.duration_days, 0);
              const endDay = startDay + task.duration_days;
              
              return {
                color: typeConfig.color === 'green' ? 'green' : typeConfig.color === 'orange' ? 'orange' : 'gray',
                label: (
                  <div className="text-gray-400 text-sm">
                    第 {startDay + 1} - {endDay} 天
                  </div>
                ),
                children: (
                  <div className="bg-gray-800/30 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-white">
                        {index + 1}. {task.name}
                      </span>
                      <Tag color={typeConfig.color}>{typeConfig.label}</Tag>
                    </div>
                    <div className="text-gray-400 text-sm">{task.description}</div>
                    <div className="text-gray-500 text-xs mt-1">
                      耗时 {task.duration_days} 天
                      {task.dependencies && task.dependencies.length > 0 && (
                        <span> · 依赖: {task.dependencies.join(', ')}</span>
                      )}
                    </div>
                  </div>
                ),
              };
            })}
          />
        </Card>
      )}

      {/* 模板元信息 */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <AppstoreOutlined className="text-indigo-400" />
            <span>模板信息</span>
          </div>
        }
      >
        <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
          <Descriptions.Item label="模板ID">
            <span className="font-mono text-gray-400">{template.template_id}</span>
          </Descriptions.Item>
          <Descriptions.Item label="所属分类">
            <Tag color={categoryInfo.color}>{categoryInfo.label}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="成功率">
            <span className={`font-medium ${
              template.success_rate >= 0.8 ? 'text-emerald-400' : 
              template.success_rate >= 0.6 ? 'text-amber-400' : 'text-rose-400'
            }`}>
              {(template.success_rate * 100).toFixed(0)}%
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="执行周期">
            {template.estimated_duration_days} 天
          </Descriptions.Item>
          <Descriptions.Item label="预估成本">
            ¥{template.estimated_cost.toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="任务数量">
            {template.task_count} 个
          </Descriptions.Item>
          <Descriptions.Item label="适用标签" span={2}>
            <div className="flex flex-wrap gap-1">
              {template.applicable_tags?.map((tag) => (
                <Tag key={tag} style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6', border: 'none' }}>{getTagLabel(tag)}</Tag>
              )) || '-'}
            </div>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}

// 任务卡片组件
function TaskCard({ task, index }: { task: TemplateTask; index: number }) {
  const typeConfig = executionTypeConfig[task.execution_type] || { 
    label: task.execution_type, 
    color: 'default',
    icon: <ToolOutlined />
  };
  const doc = getTaskDoc(task.task_id);

  return (
    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50 hover:border-gray-600/50 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-indigo-500/20 flex items-center justify-center text-purple-400 font-bold text-sm">
              {index + 1}
            </span>
            <h4 className="text-white font-medium text-base">{task.name}</h4>
          </div>
          <p className="text-gray-400 text-sm ml-11 mb-2">
            {task.description || '暂无描述'}
          </p>
          {doc && (
            <div className="ml-11 space-y-2 mb-3 pl-3 border-l-2 border-gray-600/50">
              <div>
                <span className="text-gray-500 text-xs font-medium uppercase tracking-wider">任务作用</span>
                <p className="text-gray-300 text-sm mt-0.5">{doc.role}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs font-medium uppercase tracking-wider">工作原理</span>
                <p className="text-gray-300 text-sm mt-0.5">{doc.howItWorks}</p>
              </div>
            </div>
          )}
          <div className="flex items-center gap-4 ml-11">
            <div className="flex items-center gap-1 text-gray-500 text-sm">
              <ClockCircleOutlined />
              <span>{task.duration_days} 天</span>
            </div>
            {task.dependencies && task.dependencies.length > 0 && (
              <div className="text-gray-500 text-sm">
                依赖: {task.dependencies.join(', ')}
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Tag 
            style={{ backgroundColor: `${typeConfig.color}20`, color: typeConfig.color, border: 'none' }} 
            icon={typeConfig.icon}
            className="m-0"
          >
            {typeConfig.label}
          </Tag>
          <span className="text-gray-500 text-xs font-mono">
            {task.task_id}
          </span>
        </div>
      </div>
    </div>
  );
}

