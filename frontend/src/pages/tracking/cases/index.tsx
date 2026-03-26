import { useMemo, useState } from 'react';
import { Card, Table, Tag, Button, Empty, Spin, Select, Row, Col, Slider } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  BookOutlined,
  SearchOutlined,
  LoadingOutlined,
  EyeOutlined,
  StarOutlined,
  FilterOutlined,
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
  const [filters, setFilters] = useState<{
    industry?: string;
    min_score?: number;
    limit: number;
  }>({
    limit: 10,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const skip = useMemo(() => (currentPage - 1) * filters.limit, [currentPage, filters.limit]);

  const { data, isLoading, refetch } = useCaseSearch({ ...filters, skip });
  const response = (data ?? {}) as BackendCaseSearchResponse;
  const cases = response.items || [];
  const total = response.total || 0;

  const handleViewDetail = (caseId: string) => {
    navigate(`/tracking/cases/${caseId}`);
  };

  const updateFilter = (key: 'industry' | 'min_score' | 'limit', value: string | number | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
    }));
    setCurrentPage(1);
  };

  const resetFilters = () => {
    setFilters({ limit: 10 });
    setCurrentPage(1);
  };

  const columns: ColumnsType<BackendCaseItem> = [
    {
      title: '方案名称',
      dataIndex: 'plan_name',
      key: 'plan_name',
      render: (planName: string) => <span className='font-medium text-white'>{planName || '未命名方案'}</span>,
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 110,
      render: (industry: string) => <Tag color='blue'>{getIndustryLabel(industry || 'general')}</Tag>,
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
        return (
          <div className='flex flex-wrap gap-1'>
            {indicators.slice(0, 3).map((code) => (
              <Tag key={code} color='purple'>
                {getIndicatorLabel(code)}
              </Tag>
            ))}
            {indicators.length > 3 && <Tag color='default'>+{indicators.length - 3}</Tag>}
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
      <div className='flex justify-between items-center'>
        <div>
          <h1 className='text-2xl font-bold text-white flex items-center gap-3'>
            <span className='w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-indigo-500/20'>
              <BookOutlined />
            </span>
            案例库
          </h1>
          <p className='text-gray-400 mt-2 text-sm'>
            浏览效果追踪沉淀下来的真实案例与指标结果
          </p>
        </div>
        <div className='flex gap-3'>
          <Button icon={<FilterOutlined />} onClick={() => setShowFilters(!showFilters)}>
            {showFilters ? '收起筛选' : '展开筛选'}
          </Button>
        </div>
      </div>

      {showFilters && (
        <Card size='small'>
          <Row gutter={16} align='middle'>
            <Col span={7}>
              <div className='text-gray-400 text-xs mb-1'>行业</div>
              <Select
                placeholder='选择行业'
                allowClear
                style={{ width: '100%' }}
                value={filters.industry}
                onChange={(value) => updateFilter('industry', value)}
                options={industryOptions}
              />
            </Col>
            <Col span={8}>
              <div className='text-gray-400 text-xs mb-1'>最低达成率: {filters.min_score || 0}%</div>
              <Slider
                min={0}
                max={100}
                value={filters.min_score || 0}
                onChange={(value) => updateFilter('min_score', value > 0 ? value : undefined)}
              />
            </Col>
            <Col span={5}>
              <div className='text-gray-400 text-xs mb-1'>显示数量</div>
              <Select
                style={{ width: '100%' }}
                value={filters.limit}
                onChange={(value) => updateFilter('limit', value)}
                options={[
                  { value: 10, label: '10条' },
                  { value: 20, label: '20条' },
                  { value: 50, label: '50条' },
                ]}
              />
            </Col>
            <Col span={4} className='flex gap-2'>
              <Button onClick={resetFilters}>重置</Button>
              <Button type='primary' icon={<SearchOutlined />} onClick={() => refetch()}>
                搜索
              </Button>
            </Col>
          </Row>
        </Card>
      )}

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
              pageSize: filters.limit,
              total,
              showTotal: (value) => `共 ${value} 个案例`,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (page, size) => {
                setCurrentPage(page);
                if (size !== filters.limit) {
                  setFilters((prev) => ({ ...prev, limit: size }));
                  setCurrentPage(1);
                }
              },
              onShowSizeChange: (_, size) => {
                setFilters((prev) => ({ ...prev, limit: size }));
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
