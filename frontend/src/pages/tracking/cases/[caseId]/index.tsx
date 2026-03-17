

import { useParams, useNavigate } from 'react-router-dom';
import { Card, Spin, Empty, Button, Descriptions, Tag, Row, Col, Statistic, Timeline } from 'antd';
import { 
  ArrowLeftOutlined, 
  LoadingOutlined,
  BookOutlined,
  StarOutlined,
  CheckCircleOutlined,
  BulbOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { trackingApi } from '@/lib/api';
import dayjs from 'dayjs';

// 行业选项映射
const industryLabels: Record<string, string> = {
  retail: '零售',
  finance: '金融',
  manufacturing: '制造业',
  healthcare: '医疗健康',
  education: '教育',
  technology: '科技',
  general: '通用',
};

// 问题类型映射
const problemTypeLabels: Record<string, string> = {
  lead_conversion: '线索转化',
  customer_retention: '客户留存',
  marketing_roi: '营销ROI',
  operation_efficiency: '运营效率',
  data_integration: '数据整合',
  team_collaboration: '团队协作',
};

interface CaseDetail {
  id: string;
  title: string;
  industry: string;
  problem_type: string;
  solution_summary: string;
  improvement_score: number;
  created_at: string;
  // 扩展字段
  problem_description?: string;
  solution_details?: string;
  implementation_steps?: string[];
  key_metrics?: Array<{ name: string; before: number; after: number; unit: string }>;
  lessons_learned?: string[];
  recommendations?: string[];
  duration_days?: number;
  team_size?: number;
}

export default function CaseDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  
  const caseId = params.caseId as string;
  
  const { data: caseDetail, isLoading } = useQuery<CaseDetail>({
    queryKey: ['tracking', 'cases', caseId],
    queryFn: () => trackingApi.getCaseDetail(caseId) as Promise<CaseDetail>,
    enabled: !!caseId,
  });
  
  const handleBack = () => {
    navigate(-1);
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }
  
  if (!caseDetail) {
    return (
      <div className="space-y-6">
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={handleBack}
        >
          返回
        </Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty description="案例不存在或已被删除" />
        </div>
      </div>
    );
  }
  
  const scoreColor = caseDetail.improvement_score >= 80 
    ? 'text-emerald-400' 
    : caseDetail.improvement_score >= 60 
      ? 'text-amber-400' 
      : 'text-gray-400';
  
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={handleBack}
          />
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-indigo-500/20">
                <BookOutlined />
              </span>
              案例详情
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              {caseDetail.title}
            </p>
          </div>
        </div>
      </div>

      {/* 概览卡片 */}
      <Card className="border-l-4 border-l-indigo-500">
        <Row gutter={24}>
          <Col span={6}>
            <Statistic 
              title="提升效果"
              value={caseDetail.improvement_score}
              suffix="分"
              valueStyle={{ color: caseDetail.improvement_score >= 80 ? '#10b981' : '#f59e0b' }}
              prefix={<StarOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="所属行业"
              value={industryLabels[caseDetail.industry] || caseDetail.industry}
              valueStyle={{ fontSize: 18, color: '#fff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="问题类型"
              value={problemTypeLabels[caseDetail.problem_type] || caseDetail.problem_type}
              valueStyle={{ fontSize: 18, color: '#fff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="实施周期"
              value={caseDetail.duration_days || '-'}
              suffix="天"
              valueStyle={{ fontSize: 18, color: '#fff' }}
            />
          </Col>
        </Row>
      </Card>

      {/* 基本信息 */}
      <Card title={
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 text-sm">
            📋
          </span>
          基本信息
        </div>
      }>
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="案例标题" span={2}>
            <span className="font-medium">{caseDetail.title}</span>
          </Descriptions.Item>
          <Descriptions.Item label="行业">
            <Tag color="blue">{industryLabels[caseDetail.industry] || caseDetail.industry}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="问题类型">
            <Tag color="purple">{problemTypeLabels[caseDetail.problem_type] || caseDetail.problem_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="提升效果">
            <span className={`font-bold ${scoreColor}`}>
              {caseDetail.improvement_score}分
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {dayjs(caseDetail.created_at).format('YYYY-MM-DD')}
          </Descriptions.Item>
          {caseDetail.team_size && (
            <Descriptions.Item label="团队规模">
              {caseDetail.team_size}人
            </Descriptions.Item>
          )}
          {caseDetail.duration_days && (
            <Descriptions.Item label="实施周期">
              {caseDetail.duration_days}天
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Row gutter={16}>
        {/* 问题描述 */}
        <Col span={12}>
          <Card 
            title={
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400 text-sm">
                  ❓
                </span>
                问题描述
              </div>
            }
            className="h-full"
          >
            <p className="text-gray-300 leading-relaxed">
              {caseDetail.problem_description || caseDetail.solution_summary || '暂无问题描述'}
            </p>
          </Card>
        </Col>
        
        {/* 解决方案 */}
        <Col span={12}>
          <Card 
            title={
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 text-sm">
                  💡
                </span>
                解决方案
              </div>
            }
            className="h-full"
          >
            <p className="text-gray-300 leading-relaxed">
              {caseDetail.solution_details || caseDetail.solution_summary || '暂无解决方案'}
            </p>
          </Card>
        </Col>
      </Row>

      {/* 关键指标改善 */}
      {caseDetail.key_metrics && caseDetail.key_metrics.length > 0 && (
        <Card 
          title={
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400 text-sm">
                <RiseOutlined />
              </span>
              关键指标改善
            </div>
          }
        >
          <div className="grid grid-cols-4 gap-4">
            {caseDetail.key_metrics.map((metric, index) => {
              const improvement = ((metric.after - metric.before) / metric.before) * 100;
              return (
                <div 
                  key={index}
                  className="p-4 bg-gray-800/50 rounded-lg text-center"
                >
                  <div className="text-gray-400 text-sm mb-2">{metric.name}</div>
                  <div className="flex justify-center items-center gap-2">
                    <span className="text-gray-500">{metric.before}{metric.unit}</span>
                    <span className="text-gray-600">→</span>
                    <span className="text-emerald-400 font-bold">{metric.after}{metric.unit}</span>
                  </div>
                  <Tag color="green" className="!mt-2">
                    +{improvement.toFixed(1)}%
                  </Tag>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* 实施步骤 */}
      {caseDetail.implementation_steps && caseDetail.implementation_steps.length > 0 && (
        <Card 
          title={
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 text-sm">
                📝
              </span>
              实施步骤
            </div>
          }
        >
          <Timeline
            items={caseDetail.implementation_steps.map((step, index) => ({
              color: 'blue',
              children: (
                <div className="p-3 bg-gray-800/30 rounded-lg">
                  <span className="text-gray-300">{step}</span>
                </div>
              ),
            }))}
          />
        </Card>
      )}

      <Row gutter={16}>
        {/* 经验教训 */}
        {caseDetail.lessons_learned && caseDetail.lessons_learned.length > 0 && (
          <Col span={12}>
            <Card 
              title={
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 text-sm">
                    📚
                  </span>
                  经验教训
                </div>
              }
            >
              <ul className="space-y-2">
                {caseDetail.lessons_learned.map((lesson, index) => (
                  <li key={index} className="flex items-start gap-2 text-gray-300">
                    <span className="text-purple-400 mt-0.5">•</span>
                    {lesson}
                  </li>
                ))}
              </ul>
            </Card>
          </Col>
        )}

        {/* 建议 */}
        {caseDetail.recommendations && caseDetail.recommendations.length > 0 && (
          <Col span={12}>
            <Card 
              title={
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 text-sm">
                    <BulbOutlined />
                  </span>
                  改进建议
                </div>
              }
            >
              <ul className="space-y-2">
                {caseDetail.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start gap-2 text-gray-300">
                    <CheckCircleOutlined className="text-emerald-400 mt-0.5" />
                    {rec}
                  </li>
                ))}
              </ul>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  );
}

