import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Tag, Button, Empty, Spin, Progress, Row, Col,
  Descriptions, Statistic, Divider, Timeline,
} from 'antd';
import {
  ArrowLeftOutlined,
  FileTextOutlined,
  TrophyOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExperimentOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  CameraOutlined,
  BarChartOutlined,
  BulbOutlined,
  WarningOutlined,
  StarOutlined,
  RiseOutlined,
  FallOutlined,
  MinusOutlined,
  RocketOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { useTrackingReport, useDimensionConfig } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dayjs from 'dayjs';

// 效果状态配置
const effectStatusConfig: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
  exceeds_expectation: { color: '#10b981', text: '超出预期', icon: <RocketOutlined /> },
  meets_expectation: { color: '#3b82f6', text: '达到预期', icon: <CheckCircleOutlined /> },
  below_expectation: { color: '#f59e0b', text: '未达预期', icon: <WarningOutlined /> },
  no_change: { color: '#6b7280', text: '效果不明显', icon: <MinusOutlined /> },
  negative: { color: '#ef4444', text: '负面效果', icon: <CloseCircleOutlined /> },
};

// 评分等级
function getScoreLevel(score: number) {
  if (score >= 90) return { label: '卓越', color: '#10b981', bg: 'from-emerald-500/20 to-green-500/20' };
  if (score >= 80) return { label: '优秀', color: '#10b981', bg: 'from-emerald-500/20 to-green-500/20' };
  if (score >= 70) return { label: '良好', color: '#3b82f6', bg: 'from-blue-500/20 to-cyan-500/20' };
  if (score >= 60) return { label: '一般', color: '#f59e0b', bg: 'from-amber-500/20 to-yellow-500/20' };
  return { label: '待改善', color: '#ef4444', bg: 'from-rose-500/20 to-red-500/20' };
}

interface MetricEffect {
  metric_name: string;
  baseline_value: number;
  current_value: number;
  expected_change: number;
  actual_change: number;
  change_percentage: number;
  status: string;
}

interface ExecutionSummary {
  completion_rate?: number;
  planned_duration?: number;
  actual_duration?: number;
  on_time_rate?: number;
  automation_rate?: number;
  team_size?: number;
  actual_cost?: number;
  task_stats?: Record<string, number>;
}

interface ReportData {
  id: string;
  tracking_id: string;
  title: string;
  executive_summary: string;
  summary?: string;
  overall_score: number;
  sections: Array<{ title: string; content: string; charts?: Array<Record<string, unknown>> }>;
  recommendations: string[];
  created_at: string;
  solution_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  tracking_duration_days: number;
  snapshot_count: number;
  execution_summary: ExecutionSummary;
  metric_effects: MetricEffect[];
}

export default function TrackingReportPage() {
  const params = useParams();
  const navigate = useNavigate();
  const trackingId = params.trackingId as string;
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  const { data: reportData, isLoading } = useTrackingReport(trackingId) as {
    data: ReportData | undefined;
    isLoading: boolean;
  };
  
  // 获取指标显示名称映射
  const { getMetricDisplayName } = useDimensionConfig(enterpriseId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin size="large" />
      </div>
    );
  }

  if (!reportData) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          返回
        </Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty description="复盘报告不存在" />
        </div>
      </div>
    );
  }

  const score = reportData.overall_score;
  const scoreLevel = getScoreLevel(score);
  const execSummary = reportData.execution_summary || {};
  const taskStats = execSummary.task_stats || {};
  const totalTasks = Object.values(taskStats).reduce((a, b) => a + b, 0);
  const completedTasks = taskStats.completed || 0;

  // 指标效果统计
  const metrics = reportData.metric_effects || [];
  const improvedCount = metrics.filter(
    (m) => m.status === 'exceeds_expectation' || m.status === 'meets_expectation'
  ).length;
  const belowCount = metrics.filter(
    (m) => m.status === 'below_expectation' || m.status === 'negative'
  ).length;

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto px-4 pb-8">
      {/* 页头 */}
      <div className="flex items-start mb-6">
        <div className="flex items-center gap-4">
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate(`/tracking/${trackingId}`)}
            className="!border-gray-600 hover:!border-gray-500"
          >
            返回追踪
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
              <span className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-600 flex items-center justify-center text-xl shadow-lg shadow-indigo-500/30 animate-pulse">
                <FileTextOutlined />
              </span>
              复盘报告
            </h1>
            <p className="text-gray-400 text-base font-medium">{reportData.solution_name}</p>
          </div>
        </div>
      </div>

      {/* ========== 评分总览 ========== */}
      <Card className="!bg-gradient-to-br from-gray-800/90 via-gray-800/80 to-gray-900/90 border-gray-700/50 overflow-hidden relative shadow-xl">
        {/* 背景装饰 */}
        <div className="absolute top-0 right-0 w-96 h-96 rounded-full bg-gradient-to-br from-purple-500/10 via-indigo-500/5 to-transparent -translate-y-1/2 translate-x-1/2 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-72 h-72 rounded-full bg-gradient-to-tr from-blue-500/10 to-transparent translate-y-1/2 -translate-x-1/2 blur-3xl" />
        
        <Row gutter={32} align="middle" className="relative z-10">
          {/* 大评分 */}
          <Col span={6}>
            <div className="text-center">
              <div className="relative inline-flex items-center justify-center">
                <div className="absolute inset-0 rounded-full blur-xl opacity-30" style={{ background: scoreLevel.color }} />
                <Progress
                  type="circle"
                  percent={score}
                  size={180}
                  strokeColor={{
                    '0%': scoreLevel.color,
                    '100%': scoreLevel.color + '88',
                  }}
                  trailColor="rgba(255,255,255,0.08)"
                  strokeWidth={8}
                  format={() => (
                    <div>
                      <div className="text-5xl font-extrabold drop-shadow-lg" style={{ color: scoreLevel.color }}>
                        {score.toFixed(0)}
                      </div>
                      <div className="text-xs text-gray-400 mt-2 font-medium">综合评分</div>
                    </div>
                  )}
                />
              </div>
              <Tag
                className="mt-4 text-sm px-5 py-1.5 font-semibold shadow-lg"
                style={{ 
                  color: scoreLevel.color, 
                  borderColor: scoreLevel.color + '40', 
                  background: scoreLevel.color + '15',
                  backdropFilter: 'blur(10px)'
                }}
              >
                {scoreLevel.label}
              </Tag>
            </div>
          </Col>
          {/* 关键数据 */}
          <Col span={18}>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">{reportData.title}</h2>
              <p className="text-gray-400 text-sm flex items-center gap-2">
                <ClockCircleOutlined className="text-gray-500" />
                生成于 {dayjs(reportData.created_at).format('YYYY年MM月DD日 HH:mm')}
              </p>
            </div>
            <Row gutter={20}>
              <Col span={6}>
                <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 rounded-xl p-5 border border-gray-700/40 hover:border-blue-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-3 font-medium">
                    <ClockCircleOutlined className="text-blue-400" /> 追踪时长
                  </div>
                  <div className="text-2xl font-bold text-white">
                    {reportData.tracking_duration_days}<span className="text-sm text-gray-500 ml-1 font-normal">天</span>
                  </div>
                </div>
              </Col>
              <Col span={6}>
                <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 rounded-xl p-5 border border-gray-700/40 hover:border-amber-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-amber-500/10 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-3 font-medium">
                    <CameraOutlined className="text-amber-400" /> 快照数量
                  </div>
                  <div className="text-2xl font-bold text-amber-400">
                    {reportData.snapshot_count}<span className="text-sm text-gray-500 ml-1 font-normal">个</span>
                  </div>
                </div>
              </Col>
              <Col span={6}>
                <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 rounded-xl p-5 border border-gray-700/40 hover:border-emerald-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-emerald-500/10 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-3 font-medium">
                    <CheckCircleOutlined className="text-emerald-400" /> 任务完成
                  </div>
                  <div className="text-2xl font-bold text-emerald-400">
                    {execSummary.completion_rate?.toFixed(0) || 0}<span className="text-sm text-gray-500 ml-1 font-normal">%</span>
                  </div>
                </div>
              </Col>
              <Col span={6}>
                <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 rounded-xl p-5 border border-gray-700/40 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-3 font-medium">
                    <BarChartOutlined className="text-cyan-400" /> 指标达标
                  </div>
                  <div className="text-2xl font-bold text-cyan-400">
                    {improvedCount}<span className="text-sm text-gray-500 ml-1">/</span>{metrics.length}
                  </div>
                </div>
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>

      {/* ========== 执行摘要 ========== */}
      <Card
        className="!bg-gray-800/50 !border-gray-700/50 shadow-lg"
        title={
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
              <ThunderboltOutlined className="text-amber-400 text-lg" />
            </div>
            <span className="text-lg font-semibold">执行摘要</span>
          </div>
        }
      >
        <div className="text-gray-300 text-base whitespace-pre-line leading-relaxed bg-gradient-to-br from-gray-800/40 to-gray-900/40 rounded-xl p-6 border border-gray-700/30 backdrop-blur-sm">
          {reportData.executive_summary || '暂无摘要'}
        </div>
      </Card>

      {/* ========== 项目基本信息 ========== */}
      <Card
        className="!bg-gray-800/50 !border-gray-700/50 shadow-lg"
        title={
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
              <DashboardOutlined className="text-blue-400 text-lg" />
            </div>
            <span className="text-lg font-semibold">项目概况</span>
          </div>
        }
      >
        <Descriptions 
          bordered 
          column={3} 
          size="small"
          className="[&_.ant-descriptions-item-label]:!bg-gray-800/50 [&_.ant-descriptions-item-label]:!text-gray-300 [&_.ant-descriptions-item-label]:!font-medium [&_.ant-descriptions-item-content]:!bg-gray-800/30 [&_.ant-descriptions-item-content]:!text-gray-200"
        >
          <Descriptions.Item label="方案名称" span={2}>
            <span className="font-medium text-white">{reportData.solution_name}</span>
          </Descriptions.Item>
          <Descriptions.Item label="最终评分">
            <span className="font-bold text-lg" style={{ color: scoreLevel.color }}>
              {score.toFixed(0)} 分
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {reportData.started_at ? dayjs(reportData.started_at).format('YYYY-MM-DD HH:mm') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {reportData.completed_at ? dayjs(reportData.completed_at).format('YYYY-MM-DD HH:mm') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="追踪时长">
            {reportData.tracking_duration_days} 天
          </Descriptions.Item>
          <Descriptions.Item label="计划工期">
            {execSummary.planned_duration || '-'} 天
          </Descriptions.Item>
          <Descriptions.Item label="实际工期">
            <span className={
              (execSummary.actual_duration || 0) > (execSummary.planned_duration || 0)
                ? 'text-rose-400'
                : 'text-emerald-400'
            }>
              {execSummary.actual_duration || '-'} 天
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="团队规模">
            <TeamOutlined className="mr-1" />{execSummary.team_size || '-'} 人
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* ========== 指标效果分析 + 任务执行 ========== */}
      <Row gutter={16}>
        {/* 指标对比 */}
        <Col span={14}>
          <Card
            className="!bg-gray-800/50 !border-gray-700/50 shadow-lg h-full"
            title={
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
                  <ExperimentOutlined className="text-cyan-400 text-lg" />
                </div>
                <span className="text-lg font-semibold">指标效果对比</span>
                <Tag className="ml-2 !bg-cyan-500/10 !border-cyan-500/30 !text-cyan-400">{metrics.length} 项指标</Tag>
              </div>
            }
          >
            {metrics.length > 0 ? (
              <div className="space-y-3">
                {metrics.map((m, idx) => {
                  const cfg = effectStatusConfig[m.status] || effectStatusConfig.no_change;
                  const isUp = m.actual_change > 0;
                  const isDown = m.actual_change < 0;
                  return (
                    <div
                      key={idx}
                      className="p-5 bg-gradient-to-br from-gray-800/60 to-gray-900/60 rounded-xl border border-gray-700/40 hover:border-gray-600/60 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/5 backdrop-blur-sm"
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div 
                            className="w-10 h-10 rounded-lg flex items-center justify-center"
                            style={{ 
                              background: cfg.color + '15',
                              border: `1px solid ${cfg.color}30`
                            }}
                          >
                            <span style={{ color: cfg.color, fontSize: '18px' }}>{cfg.icon}</span>
                          </div>
                          <div>
                            <span className="text-white font-semibold text-base block">{getMetricDisplayName(m.metric_name)}</span>
                            <Tag
                              style={{
                                color: cfg.color,
                                borderColor: cfg.color + '40',
                                background: cfg.color + '15',
                              }}
                              className="text-xs mt-1 !border !font-medium"
                            >
                              {cfg.text}
                            </Tag>
                          </div>
                        </div>
                        <div
                          className={`font-bold text-base flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${
                            isUp ? 'text-emerald-400 bg-emerald-500/10' : isDown ? 'text-rose-400 bg-rose-500/10' : 'text-gray-400 bg-gray-500/10'
                          }`}
                        >
                          {isUp ? <RiseOutlined /> : isDown ? <FallOutlined /> : <MinusOutlined />}
                          {isUp ? '+' : ''}{m.change_percentage.toFixed(1)}%
                        </div>
                      </div>
                      {/* 数值条 */}
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <div className="text-xs text-gray-400 w-16 text-right font-medium">基线</div>
                          <div className="flex-1 relative h-8 bg-gray-700/50 rounded-lg overflow-hidden border border-gray-600/30">
                            <div
                              className="absolute top-0 left-0 h-full rounded-lg bg-gradient-to-r from-gray-600/80 to-gray-500/80 transition-all duration-500"
                              style={{
                                width: `${Math.min(100, (m.baseline_value / Math.max(m.baseline_value, m.current_value) * 100))}%`,
                              }}
                            />
                            <span className="absolute inset-0 flex items-center justify-center text-sm text-gray-200 font-semibold">
                              {m.baseline_value.toFixed(1)}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-xs text-gray-400 w-16 text-right font-medium">当前</div>
                          <div className="flex-1 relative h-8 bg-gray-700/50 rounded-lg overflow-hidden border border-gray-600/30">
                            <div
                              className="absolute top-0 left-0 h-full rounded-lg transition-all duration-500 shadow-lg"
                              style={{
                                width: `${Math.min(100, (m.current_value / Math.max(m.baseline_value, m.current_value) * 100))}%`,
                                background: `linear-gradient(to right, ${cfg.color}aa, ${cfg.color})`,
                                boxShadow: `0 0 10px ${cfg.color}40`,
                              }}
                            />
                            <span className="absolute inset-0 flex items-center justify-center text-sm text-white font-bold">
                              {m.current_value.toFixed(1)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <Empty description="暂无指标数据" className="py-8" />
            )}
          </Card>
        </Col>

        {/* 任务执行情况 */}
        <Col span={10}>
          <div className="space-y-4 h-full flex flex-col">
            {/* 任务统计 */}
            <Card
              className="!bg-gray-800/50 !border-gray-700/50 shadow-lg flex-1"
              title={
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                    <TeamOutlined className="text-green-400 text-lg" />
                  </div>
                  <span className="text-lg font-semibold">任务执行</span>
                </div>
              }
            >
              <div className="text-center mb-4">
                <Progress
                  type="circle"
                  percent={execSummary.completion_rate || 0}
                  size={100}
                  strokeColor="#10b981"
                  trailColor="rgba(255,255,255,0.06)"
                  format={(pct) => (
                    <div>
                      <div className="text-xl font-bold text-emerald-400">{pct?.toFixed(0)}%</div>
                      <div className="text-[10px] text-gray-500">完成率</div>
                    </div>
                  )}
                />
              </div>
              <Row gutter={[12, 12]}>
                <Col span={12}>
                  <div className="bg-emerald-500/10 rounded-lg p-3 text-center border border-emerald-500/20">
                    <div className="text-lg font-bold text-emerald-400">{completedTasks}</div>
                    <div className="text-xs text-gray-400">已完成</div>
                  </div>
                </Col>
                <Col span={12}>
                  <div className="bg-rose-500/10 rounded-lg p-3 text-center border border-rose-500/20">
                    <div className="text-lg font-bold text-rose-400">{taskStats.failed || 0}</div>
                    <div className="text-xs text-gray-400">失败</div>
                  </div>
                </Col>
                <Col span={12}>
                  <div className="bg-blue-500/10 rounded-lg p-3 text-center border border-blue-500/20">
                    <div className="text-lg font-bold text-blue-400">{taskStats.running || 0}</div>
                    <div className="text-xs text-gray-400">进行中</div>
                  </div>
                </Col>
                <Col span={12}>
                  <div className="bg-gray-500/10 rounded-lg p-3 text-center border border-gray-500/20">
                    <div className="text-lg font-bold text-gray-400">{taskStats.pending || 0}</div>
                    <div className="text-xs text-gray-400">未开始</div>
                  </div>
                </Col>
              </Row>
              <Divider className="!my-4 !border-gray-700/50" />
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title={<span className="text-gray-400 text-xs">按时完成率</span>}
                    value={execSummary.on_time_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#10b981', fontSize: 20 }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title={<span className="text-gray-400 text-xs">自动化比例</span>}
                    value={execSummary.automation_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#3b82f6', fontSize: 20 }}
                  />
                </Col>
              </Row>
            </Card>

            {/* 效果统计 */}
            <Card className="!bg-gradient-to-br from-gray-800/60 to-gray-900/60 !border-gray-700/50 shadow-lg">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-yellow-500/20 flex items-center justify-center">
                  <TrophyOutlined className="text-amber-400 text-lg" />
                </div>
                <span className="text-white font-semibold text-base">效果统计</span>
              </div>
              <Row gutter={12}>
                <Col span={8}>
                  <div className="text-center p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20 hover:border-emerald-500/40 transition-colors">
                    <div className="text-3xl font-bold text-emerald-400 mb-1">{improvedCount}</div>
                    <div className="text-xs text-gray-400 font-medium">达标</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div className="text-center p-3 bg-amber-500/10 rounded-lg border border-amber-500/20 hover:border-amber-500/40 transition-colors">
                    <div className="text-3xl font-bold text-amber-400 mb-1">{belowCount}</div>
                    <div className="text-xs text-gray-400 font-medium">未达标</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div className="text-center p-3 bg-gray-500/10 rounded-lg border border-gray-500/20 hover:border-gray-500/40 transition-colors">
                    <div className="text-3xl font-bold text-gray-400 mb-1">
                      {metrics.length - improvedCount - belowCount}
                    </div>
                    <div className="text-xs text-gray-400 font-medium">无变化</div>
                  </div>
                </Col>
              </Row>
            </Card>
          </div>
        </Col>
      </Row>

      {/* ========== 报告章节 ========== */}
      {reportData.sections && reportData.sections.length > 0 && (
        <Card
          className="!bg-gray-800/50 !border-gray-700/50 shadow-lg"
          title={
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
                <FileTextOutlined className="text-purple-400 text-lg" />
              </div>
              <span className="text-lg font-semibold">详细报告</span>
            </div>
          }
        >
          <Timeline
            items={reportData.sections.map((section, index) => ({
              color: index === 0 ? 'purple' : index === 1 ? 'blue' : index === 2 ? 'green' : 'gray',
              children: (
                <div className="mb-4">
                  <h3 className="text-white font-semibold text-base mb-3">{section.title}</h3>
                  <div className="bg-gray-800/30 rounded-xl p-5 border border-gray-700/20 text-gray-300 text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ node, ...props }) => <h1 className="text-white text-xl font-bold mb-3 mt-4 first:mt-0" {...props} />,
                        h2: ({ node, ...props }) => <h2 className="text-white text-lg font-semibold mb-2 mt-3 first:mt-0" {...props} />,
                        h3: ({ node, ...props }) => <h3 className="text-white text-base font-medium mb-2 mt-3 first:mt-0" {...props} />,
                        p: ({ node, ...props }) => <p className="text-gray-300 mb-3 leading-relaxed" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-3 space-y-1 text-gray-300" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-3 space-y-1 text-gray-300" {...props} />,
                        li: ({ node, ...props }) => <li className="text-gray-300" {...props} />,
                        strong: ({ node, ...props }) => <strong className="text-white font-semibold" {...props} />,
                        em: ({ node, ...props }) => <em className="text-gray-200 italic" {...props} />,
                        code: ({ node, inline, ...props }: any) => 
                          inline ? (
                            <code className="bg-gray-700/50 text-cyan-400 px-1.5 py-0.5 rounded text-xs font-mono" {...props} />
                          ) : (
                            <code className="block bg-gray-900/50 text-gray-300 p-3 rounded-lg text-xs font-mono overflow-x-auto mb-3" {...props} />
                          ),
                        pre: ({ node, ...props }) => <pre className="mb-3" {...props} />,
                        blockquote: ({ node, ...props }) => (
                          <blockquote className="border-l-4 border-cyan-500/50 pl-4 italic text-gray-400 my-3" {...props} />
                        ),
                        a: ({ node, ...props }) => (
                          <a className="text-cyan-400 hover:text-cyan-300 underline" target="_blank" rel="noopener noreferrer" {...props} />
                        ),
                        table: ({ node, ...props }) => (
                          <div className="overflow-x-auto mb-3">
                            <table className="min-w-full border-collapse border border-gray-700" {...props} />
                          </div>
                        ),
                        thead: ({ node, ...props }) => <thead className="bg-gray-700/50" {...props} />,
                        tbody: ({ node, ...props }) => <tbody {...props} />,
                        tr: ({ node, ...props }) => <tr className="border-b border-gray-700" {...props} />,
                        th: ({ node, ...props }) => (
                          <th className="border border-gray-700 px-4 py-2 text-left text-white font-semibold" {...props} />
                        ),
                        td: ({ node, ...props }) => (
                          <td className="border border-gray-700 px-4 py-2 text-gray-300" {...props} />
                        ),
                        hr: ({ node, ...props }) => <hr className="border-gray-700 my-4" {...props} />,
                      }}
                    >
                      {section.content}
                    </ReactMarkdown>
                  </div>
                </div>
              ),
            }))}
          />
        </Card>
      )}

      {/* ========== 改进建议 ========== */}
      {reportData.recommendations && reportData.recommendations.length > 0 && (
        <Card
          className="!bg-gray-800/50 !border-gray-700/50 shadow-lg"
          title={
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-yellow-500/20 flex items-center justify-center">
                <BulbOutlined className="text-amber-400 text-lg" />
              </div>
              <span className="text-lg font-semibold">改进建议</span>
              <Tag color="gold" className="ml-2 !bg-amber-500/10 !border-amber-500/30 !text-amber-400 font-semibold">
                {reportData.recommendations.length} 条
              </Tag>
            </div>
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {reportData.recommendations.map((item, index) => (
              <div
                key={index}
                className="flex items-start gap-4 p-5 bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-transparent rounded-xl border border-amber-500/20 hover:border-amber-500/40 hover:shadow-lg hover:shadow-amber-500/10 transition-all duration-300 backdrop-blur-sm group"
              >
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-500/30 to-yellow-500/20 flex items-center justify-center flex-shrink-0 mt-0.5 group-hover:scale-110 transition-transform">
                  <StarOutlined className="text-amber-400 text-base" />
                </div>
                <span className="text-gray-200 text-sm leading-relaxed font-medium flex-1">{item}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ========== 底部总结 ========== */}
      <Card className="!bg-gradient-to-br from-indigo-900/30 via-purple-900/20 to-pink-900/20 !border-indigo-500/30 shadow-xl overflow-hidden relative">
        {/* 背景装饰 */}
        <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-gradient-to-br from-purple-500/10 to-transparent -translate-y-1/2 translate-x-1/2 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-gradient-to-tr from-indigo-500/10 to-transparent translate-y-1/2 -translate-x-1/2 blur-3xl" />
        
        <div className="text-center py-6 relative z-10">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/30 to-yellow-500/20 flex items-center justify-center shadow-lg">
              <TrophyOutlined className="text-amber-400 text-2xl" />
            </div>
            <h3 className="text-2xl font-bold text-white">总结</h3>
          </div>
          <div className="max-w-3xl mx-auto">
            <p className="text-gray-200 text-base leading-relaxed mb-2">
              「<span className="font-semibold text-white">{reportData.solution_name}</span>」方案历时 
              <span className="font-bold text-blue-400 mx-1">{reportData.tracking_duration_days}</span> 天完成追踪，
              共采集 <span className="font-bold text-amber-400 mx-1">{reportData.snapshot_count}</span> 次快照，
              最终综合评分
              <span className="font-bold mx-1.5 text-2xl" style={{ color: scoreLevel.color }}>
                {score.toFixed(0)}
              </span>
              分（<span className="font-semibold" style={{ color: scoreLevel.color }}>{scoreLevel.label}</span>），
              <span className="font-bold text-emerald-400 mx-1">{improvedCount}</span>/
              <span className="font-bold text-gray-300">{metrics.length}</span> 项指标达标，
              任务完成率 <span className="font-bold text-cyan-400 mx-1">{execSummary.completion_rate?.toFixed(0) || 0}%</span>。
            </p>
            <div className="mt-6 pt-4 border-t border-gray-700/50">
              <div className="text-xs text-gray-500 flex items-center justify-center gap-2">
                <ClockCircleOutlined />
                报告生成时间：{dayjs(reportData.created_at).format('YYYY年MM月DD日 HH:mm:ss')}
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

