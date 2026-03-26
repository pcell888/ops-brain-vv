import { useParams, useNavigate } from 'react-router-dom';
import { Card, Spin, Empty, Button, Descriptions, Tag, Row, Col, Statistic, Timeline } from 'antd';
import {
  ArrowLeftOutlined,
  LoadingOutlined,
  BookOutlined,
  StarOutlined,
  RiseOutlined,
  CheckCircleOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { trackingApi } from '@/lib/api';

interface IndicatorChange {
  indicator_code: string;
  before_value?: number;
  after_value?: number;
  change_pct?: number;
  improved?: boolean;
}

interface PlanStep {
  step?: number;
  action?: string;
  owner_dept?: string;
  timeline?: string;
  implementation_steps?: string[];
}

interface AutoAction {
  type?: string;
}

interface PlanDetail {
  description?: string;
  steps?: PlanStep[];
  expected_improvement?: Record<string, number>;
  auto_actions?: AutoAction[];
}

interface BackendCaseDetail {
  case_id: string;
  tenant_id: string;
  thread_id: string;
  plan_id: string;
  plan_name: string;
  industry: string;
  target_indicators: string[];
  achievement_rate: number;
  indicator_changes?: IndicatorChange[];
  plan_detail?: PlanDetail;
  lessons_learned?: string[];
  created_at: string;
}

const industryLabels: Record<string, string> = {
  retail: '零售',
  finance: '金融',
  manufacturing: '制造业',
  healthcare: '医疗健康',
  education: '教育',
  technology: '科技',
  internet: '互联网',
  general: '通用',
  other: '其他',
};

const indicatorNameMap: Record<string, string> = {
  lead_conversion_rate: '线索转化率',
  conversion_rate: '线索转化率',
  order_conversion_rate: '订单转化率',
  browse_to_order_rate: '浏览-下单转化率',
  seckill_conversion_rate: '秒杀转化率',
  coupon_redemption_rate: '优惠券核销率',
  response_time_avg: '平均响应时间',
  avg_response_time: '平均响应时间',
  follow_up_count: '跟进次数',
  repurchase_rate: '复购率',
  refund_rate: '退款率',
  churn_rate: '流失率',
  positive_review_rate: '好评率',
  avg_customer_lifetime_value: '客户终身价值',
  service_completion_rate: '服务完成率',
  avg_shipping_hours: '平均发货时长',
  task_on_time_rate: '任务按时完成率',
};

function getIndustryLabel(industry: string): string {
  const direct = industryLabels[industry];
  if (direct) return direct;

  const prefix = industry.split('_')[0];
  return industryLabels[prefix] || industry;
}

function getIndicatorLabel(code: string): string {
  return indicatorNameMap[code] || code;
}

function getActionLabel(type: string | undefined): string {
  const actionMap: Record<string, string> = {
    coupon_campaign: '优惠券活动',
    message: '消息提醒',
    seckill_activity: '秒杀活动',
  };
  return actionMap[type || ''] || (type || '未记录');
}

export default function CaseDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const caseId = params.caseId as string;

  const { data: caseDetail, isLoading } = useQuery<BackendCaseDetail>({
    queryKey: ['tracking', 'cases', caseId],
    queryFn: () => trackingApi.getCaseDetail(caseId) as Promise<BackendCaseDetail>,
    enabled: !!caseId,
  });

  const handleBack = () => {
    navigate(-1);
  };

  if (isLoading) {
    return (
      <div className='flex items-center justify-center h-[60vh]'>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }

  if (!caseDetail) {
    return (
      <div className='space-y-6'>
        <Button icon={<ArrowLeftOutlined />} style={{ backgroundColor: '#ffffff', color: '#000000', border: '1px solid #d9d9d9' }} onClick={handleBack}>
          返回
        </Button>
        <div className='flex items-center justify-center h-[50vh]'>
          <Empty description={<span className='text-[#303133]'>案例不存在或已被删除</span>} />
        </div>
      </div>
    );
  }

  const planDetail = caseDetail.plan_detail || {};
  const targetIndicators = caseDetail.target_indicators || [];
  const indicatorChanges = caseDetail.indicator_changes || [];
  const lessons = caseDetail.lessons_learned || [];
  const planSteps = planDetail.steps || [];
  const expectedImprovements = Object.entries(planDetail.expected_improvement || {});
  const autoActions = (planDetail.auto_actions || []).map((item) => getActionLabel(item.type));
  const solutionSummary = planDetail.description
    || (targetIndicators.length > 0
      ? `目标指标：${targetIndicators.map(getIndicatorLabel).join('、')}`
      : '暂无方案说明');
  const scoreColor = caseDetail.achievement_rate >= 80
    ? 'text-emerald-400'
    : caseDetail.achievement_rate >= 60
      ? 'text-amber-400'
      : 'text-gray-300';

  const keyMetrics = indicatorChanges.filter((item) => (
    typeof item.before_value === 'number' && typeof item.after_value === 'number'
  ));

  const getTagStyle = (color: string) => {
    const getBackgroundColor = (color: string) => {
      switch (color) {
        case 'blue': return 'rgba(24, 144, 255, 0.2)';
        case 'purple': return 'rgba(120, 69, 193, 0.2)';
        case 'cyan': return 'rgba(0, 176, 255, 0.2)';
        case 'green': return 'rgba(82, 196, 26, 0.2)';
        case 'red': return 'rgba(245, 34, 45, 0.2)';
        case 'gold': return 'rgba(250, 173, 20, 0.2)';
        case 'geekblue': return 'rgba(51, 102, 255, 0.2)';
        default: return 'rgba(0, 0, 0, 0.2)';
      }
    };
    const getTextColor = (color: string) => {
      switch (color) {
        case 'blue': return '#1890ff';
        case 'purple': return '#7845c1';
        case 'cyan': return '#00b0ff';
        case 'green': return '#52c41a';
        case 'red': return '#f5222d';
        case 'gold': return '#faad14';
        case 'geekblue': return '#3366ff';
        default: return '#000000';
      }
    };
    return {
      backgroundColor: getBackgroundColor(color),
      color: getTextColor(color),
      border: 'none'
    };
  };

  return (
    <div className='space-y-6'>
      <div className='flex justify-between items-center'>
        <div className='flex items-center gap-4'>
          <Button icon={<ArrowLeftOutlined />} style={{ backgroundColor: '#ffffff', color: '#000000', border: '1px solid #d9d9d9' }} onClick={handleBack} />
          <div>
            <h1 className='text-2xl font-bold text-[#303133] flex items-center gap-3'>
              <span className='w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-indigo-500/20 text-white'>
                <BookOutlined />
              </span>
              案例详情
            </h1>
            <p className='text-[#303133] mt-1 text-sm'>{caseDetail.plan_name || '未命名方案'}</p>
          </div>
        </div>
      </div>

      <Card className='border-l-4 border-l-indigo-500'>
        <Row gutter={24}>
          <Col span={6}>
            <Statistic
              title='达成率'
              value={caseDetail.achievement_rate}
              precision={1}
              suffix='%'
              valueStyle={{ color: caseDetail.achievement_rate >= 80 ? '#10b981' : '#f59e0b' }}
              prefix={<StarOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title='所属行业'
              value={getIndustryLabel(caseDetail.industry || 'general')}
              valueStyle={{ fontSize: 18, color: '#303133' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title='目标指标数'
              value={targetIndicators.length}
              suffix='项'
              valueStyle={{ fontSize: 18, color: '#303133' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title='方案步骤数'
              value={planSteps.length || '-'}
              valueStyle={{ fontSize: 18, color: '#303133' }}
            />
          </Col>
        </Row>
      </Card>

      <Card
        title={( 
            <div className='flex items-center gap-2'>
              <span className='w-6 h-6 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 text-sm'>
                基
              </span>
              <span className='text-[#303133]'>基本信息</span>
            </div>
          )}
      >
        <Descriptions bordered column={2} size='small'>
          <Descriptions.Item label='方案名称' span={2}>
            <span className='font-medium'>{caseDetail.plan_name || '未命名方案'}</span>
          </Descriptions.Item>
          <Descriptions.Item label='案例ID'>{caseDetail.case_id}</Descriptions.Item>
          <Descriptions.Item label='创建时间'>{dayjs(caseDetail.created_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
          <Descriptions.Item label='行业'>
            <Tag style={getTagStyle('blue')}>{getIndustryLabel(caseDetail.industry || 'general')}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label='方案ID'>{caseDetail.plan_id || '-'}</Descriptions.Item>
          <Descriptions.Item label='达成率'>
            <span className={`font-bold ${scoreColor}`}>{caseDetail.achievement_rate.toFixed(1)}%</span>
          </Descriptions.Item>
          <Descriptions.Item label='追踪线程'>{caseDetail.thread_id || '-'}</Descriptions.Item>
          <Descriptions.Item label='目标指标' span={2}>
            <div className='flex flex-wrap gap-2'>
              {targetIndicators.length > 0
                ? targetIndicators.map((code) => (
                    <Tag key={code} style={getTagStyle('purple')}>
                      {getIndicatorLabel(code)}
                    </Tag>
                  ))
                : <span className='text-gray-500'>未记录</span>}
            </div>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Row gutter={16}>
        <Col span={12}>
          <Card
            title={( 
            <div className='flex items-center gap-2'>
              <span className='w-6 h-6 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400 text-sm'>
                述
              </span>
              <span className='text-[#303133]'>方案说明</span>
            </div>
          )}
            className='h-full'
          >
            <p className='text-[#303133] leading-relaxed'>{solutionSummary}</p>
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title={( 
            <div className='flex items-center gap-2'>
              <span className='w-6 h-6 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 text-sm'>
                执
              </span>
              <span className='text-[#303133]'>执行信息</span>
            </div>
          )}
            className='h-full'
          >
            <div className='space-y-3 text-[#303133]'>
              <div>
                <div className='text-gray-400 text-xs mb-1'>实施步骤</div>
                <div className='text-[#303133]'>{planSteps.length > 0 ? `${planSteps.length} 个步骤` : '暂无步骤信息'}</div>
              </div>
              <div>
                <div className='text-gray-400 text-xs mb-1'>自动动作</div>
                <div className='flex flex-wrap gap-2'>
                  {autoActions.length > 0
                    ? autoActions.map((action) => (
                        <Tag key={action} style={getTagStyle('cyan')}>
                          {action}
                        </Tag>
                      ))
                    : <span className='text-gray-500'>未配置</span>}
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {keyMetrics.length > 0 && (
        <Card
          title={( 
            <div className='flex items-center gap-2'>
              <span className='w-6 h-6 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400 text-sm'>
                <RiseOutlined />
              </span>
              <span className='text-[#303133]'>关键指标改善</span>
            </div>
          )}
        >
          <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4'>
            {keyMetrics.map((metric) => {
              const changePct = metric.change_pct ?? 0;
              const isImproved = !!metric.improved;
              const deltaText = `${changePct > 0 ? '+' : ''}${changePct.toFixed(1)}%`;
              return (
                <div key={metric.indicator_code} className='p-4 bg-gray-800/50 rounded-lg text-center'>
                  <div className='text-[#303133] text-sm mb-2'>{getIndicatorLabel(metric.indicator_code)}</div>
                  <div className='flex justify-center items-center gap-2'>
                    <span className='text-[#303133]'>{metric.before_value}</span>
                    <span className='text-[#303133]'>→</span>
                    <span className='text-[#303133] font-bold'>{metric.after_value}</span>
                  </div>
                  <Tag style={getTagStyle(isImproved ? 'green' : changePct === 0 ? 'default' : 'red')} className='!mt-2'>
                    {deltaText}
                  </Tag>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {planSteps.length > 0 && (
        <Card
          title={( 
            <div className='flex items-center gap-2'>
              <span className='w-6 h-6 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 text-sm'>
                步
              </span>
              <span className='text-[#303133]'>实施步骤</span>
            </div>
          )}
        >
          <Timeline
            items={planSteps.map((step, index) => ({
              color: 'blue',
              children: (
                <div className='p-3 rounded-lg space-y-3'>
                  <div className='flex flex-wrap gap-2 items-center'>
                    <span className='text-[#303133] font-medium'>步骤 {step.step || index + 1}</span>
                    {step.owner_dept && <Tag style={getTagStyle('gold')}>{step.owner_dept}</Tag>}
                    {step.timeline && <Tag style={getTagStyle('geekblue')}>{step.timeline}</Tag>}
                  </div>
                  {step.action && <div className='text-[#303133] leading-relaxed'>{step.action}</div>}
                  {step.implementation_steps && step.implementation_steps.length > 0 && (
                    <ul className='space-y-2'>
                      {step.implementation_steps.map((item) => (
                        <li key={item} className='flex items-start gap-2 text-[#303133]'>
                          <CheckCircleOutlined className='text-emerald-400 mt-0.5' />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ),
            }))}
          />
        </Card>
      )}

      {expectedImprovements.length > 0 && (
        <Card
          title={( 
            <div className='flex items-center gap-2'>
              <span className='w-6 h-6 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 text-sm'>
                <BulbOutlined />
              </span>
              <span className='text-[#303133]'>预期改善</span>
            </div>
          )}
        >
          <div className='flex flex-wrap gap-2'>
            {expectedImprovements.map(([code, value]) => (
              <Tag key={code} style={getTagStyle(value >= 0 ? 'green' : 'red')}>
                {getIndicatorLabel(code)}: {value > 0 ? '+' : ''}{value}
              </Tag>
            ))}
          </div>
        </Card>
      )}

      {lessons.length > 0 && (
        <Card
          title={( 
            <div className='flex items-center gap-2'>
              <span className='w-6 h-6 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 text-sm'>
                复
              </span>
              <span className='text-[#303133]'>经验教训</span>
            </div>
          )}
        >
          <ul className='space-y-2'>
            {lessons.map((lesson) => (
              <li key={lesson} className='flex items-start gap-2 text-[#303133]'>
                <span className='text-purple-400 mt-0.5'>•</span>
                <span>{lesson}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
