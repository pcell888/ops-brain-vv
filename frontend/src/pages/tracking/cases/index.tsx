import { useMemo, useState } from 'react';
import { Card, Table, Tag, Button, Empty, Spin, Input, Row, Col } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  SearchOutlined,
  LoadingOutlined,
  EyeOutlined,
  StarOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import { useCaseSearch } from '@/lib/hooks';

interface CaseIndicatorChange {
  indicator_code: string;
  change_pct?: number;
  improved?: boolean;
}

interface BackendCaseItem {
  case_id: string;
  plan_name: string;
  industry: string;
  target_indicators: string[];
  achievement_rate: number;
  indicator_changes: CaseIndicatorChange[];
  created_at: string;
}

interface BackendCaseSearchResponse {
  items?: BackendCaseItem[];
  total?: number;
}

const industryOptions = [
  { value: 'retail', label: '零售' },
  { value: 'finance', label: '金融' },
  { value: 'manufacturing', label: '制造业' },
  { value: 'healthcare', label: '医疗健康' },
  { value: 'education', label: '教育' },
  { value: 'technology', label: '科技' },
  { value: 'internet', label: '互联网' },
  { value: 'general', label: '通用' },
  { value: 'other', label: '其他' },
];

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
  const direct = industryOptions.find((option) => option.value === industry)?.label;
  if (direct) return direct;

  const prefix = industry.split('_')[0];
  return industryOptions.find((option) => option.value === prefix)?.label || industry;
}

function getIndicatorLabel(code: string): string {
  return indicatorNameMap[code] || code;
}

function buildSummary(record: BackendCaseItem): string {
  const targetIndicators = record.target_indicators || [];
  const indicatorChanges = record.indicator_changes || [];
  const labels = targetIndicators.slice(0, 3).map(getIndicatorLabel);
  const parts: string[] = [];

  if (labels.length > 0) {
    parts.push(`目标指标：${labels.join('、')}${targetIndicators.length > 3 ? ' 等' : ''}`);
  }
  if (indicatorChanges.length > 0) {
    parts.push(`共跟踪 ${indicatorChanges.length} 项指标`);
    const improvedCount = indicatorChanges.filter((item) => item.improved).length;
    if (improvedCount > 0) {
      parts.push(`${improvedCount} 项指标改善`);
    }
  } else if (targetIndicators.length > 0) {
    parts.push(`覆盖 ${targetIndicators.length} 项核心指标`);
  }

  return parts.join('，') || '案例已沉淀到效果追踪知识库';
}

export default function CasesPage() {
  const navigate = useNavigate();
  const [planNameDraft, setPlanNameDraft] = useState('');
  const [planNameApplied, setPlanNameApplied] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const skip = useMemo(() => (currentPage - 1) * pageSize, [currentPage, pageSize]);

  const searchParams = useMemo(
    () => ({
      plan_name: planNameApplied || undefined,
      skip,
      limit: pageSize,
    }),
    [planNameApplied, skip, pageSize],
  );

  const { data, isLoading, refetch } = useCaseSearch(searchParams);
  const response = (data ?? {}) as BackendCaseSearchResponse;
  const cases = response.items || [];
  const total = response.total || 0;

  const handleViewDetail = (caseId: string) => {
    navigate(`/tracking/cases/${caseId}`);
  };

  const handleSearch = () => {
    const next = planNameDraft.trim();
    setCurrentPage(1);
    if (next === planNameApplied) {
      void refetch();
    } else {
      setPlanNameApplied(next);
    }
  };

  const columns: ColumnsType<BackendCaseItem> = [
    {
      title: '方案名称',
      dataIndex: 'plan_name',
      key: 'plan_name',
      render: (planName: string) => <span className='font-medium text-[#303133]'>{planName || '未命名方案'}</span>,
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 110,
      render: (industry: string) => {
        const getBackgroundColor = () => 'rgba(24, 144, 255, 0.2)';
        const getTextColor = () => '#1890ff';
        return (
          <Tag style={{ backgroundColor: getBackgroundColor(), color: getTextColor(), border: 'none' }}>
            {getIndustryLabel(industry || 'general')}
          </Tag>
        );
      },
    },
    {
      title: '目标指标',
      dataIndex: 'target_indicators',
      key: 'target_indicators',
      width: 260,
      render: (targetIndicators: string[]) => {
        const indicators = targetIndicators || [];
        if (!indicators.length) {
          return <span className='text-gray-500 text-sm'>未记录</span>;
        }
        const getBackgroundColor = (color: string) => {
          switch (color) {
            case 'purple': return 'rgba(120, 69, 193, 0.2)';
            case 'default': return 'rgba(0, 0, 0, 0.2)';
            default: return 'rgba(120, 69, 193, 0.2)';
          }
        };
        const getTextColor = (color: string) => {
          switch (color) {
            case 'purple': return '#7845c1';
            case 'default': return '#000000';
            default: return '#7845c1';
          }
        };
        return (
          <div className='flex flex-wrap gap-1'>
            {indicators.slice(0, 3).map((code) => (
              <Tag key={code} style={{ backgroundColor: getBackgroundColor('purple'), color: getTextColor('purple'), border: 'none' }}>
                {getIndicatorLabel(code)}
              </Tag>
            ))}
            {indicators.length > 3 && (
              <Tag style={{ backgroundColor: getBackgroundColor('default'), color: getTextColor('default'), border: 'none' }}>
                +{indicators.length - 3}
              </Tag>
            )}
          </div>
        );
      },
    },
    {
      title: '达成率',
      dataIndex: 'achievement_rate',
      key: 'achievement_rate',
      width: 120,
      render: (score: number) => {
        const color = score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-gray-300';
        return (
          <span className={`font-bold ${color}`}>
            <StarOutlined className='mr-1' />
            {score.toFixed(1)}%
          </span>
        );
      },
    },
    {
      title: '案例概览',
      key: 'summary',
      ellipsis: true,
      render: (_, record) => <span className='text-gray-400 text-sm'>{buildSummary(record)}</span>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => <span className='text-gray-500 text-sm'>{dayjs(date).format('YYYY-MM-DD')}</span>,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type='link' size='small' icon={<EyeOutlined />} onClick={() => handleViewDetail(record.case_id)}>
          查看
        </Button>
      ),
    },
  ];

  const stats = cases.length > 0
    ? {
        total,
        avgScore: Math.round(cases.reduce((sum, item) => sum + item.achievement_rate, 0) / cases.length),
        highScore: cases.filter((item) => item.achievement_rate >= 80).length,
      }
    : null;

  return (
    <div className='space-y-6'>
      <div>
        <p className='text-[#303133] mt-2 text-sm'>
          浏览效果追踪沉淀下来的真实案例与指标结果
        </p>
      </div>

      <Card size='small'>
        <Row gutter={16} align='middle' wrap={false}>
          <Col flex='auto' style={{ minWidth: 200 }}>
            <Input
              placeholder='输入关键词，模糊匹配方案名称'
              value={planNameDraft}
              onChange={(e) => setPlanNameDraft(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
            />
          </Col>
          <Col>
            <Button type='primary' icon={<SearchOutlined />} onClick={handleSearch}>
              搜索
            </Button>
          </Col>
        </Row>
      </Card>

      {stats && (
        <Row gutter={16}>
          <Col span={8}>
            <Card className='text-center'>
              <div className='text-3xl font-bold text-blue-400'>{stats.total}</div>
              <div className='text-gray-400 text-sm mt-1'>案例总数</div>
            </Card>
          </Col>
          <Col span={8}>
            <Card className='text-center'>
              <div className='text-3xl font-bold text-emerald-400'>{stats.highScore}</div>
              <div className='text-gray-400 text-sm mt-1'>高达成案例</div>
            </Card>
          </Col>
          <Col span={8}>
            <Card className='text-center'>
              <div className='text-3xl font-bold text-amber-400'>{stats.avgScore}</div>
              <div className='text-gray-400 text-sm mt-1'>平均达成率</div>
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        {isLoading ? (
          <div className='flex items-center justify-center py-20'>
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={cases}
            rowKey='case_id'
            pagination={{
              current: currentPage,
              pageSize,
              total,
              showTotal: (value) => `共 ${value} 个案例`,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (page, size) => {
                setCurrentPage(page);
                if (size !== pageSize) {
                  setPageSize(size);
                  setCurrentPage(1);
                }
              },
              onShowSizeChange: (_, size) => {
                setPageSize(size);
                setCurrentPage(1);
              },
            }}
            locale={{
              emptyText: <Empty description='暂无案例数据' />,
            }}
          />
        )}
      </Card>
    </div>
  );
}
