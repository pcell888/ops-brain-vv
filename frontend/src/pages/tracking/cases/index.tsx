

import { useState, useMemo } from 'react';
import { 
  Card, Table, Tag, Button, Empty, Spin, Input, Select, Row, Col, Slider, App 
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  BookOutlined, 
  SearchOutlined,
  LoadingOutlined,
  EyeOutlined,
  StarOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useCaseSearch } from '@/lib/hooks';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

interface CaseItem {
  id: string;
  title: string;
  industry: string;
  problem_type: string;
  solution_summary: string;
  improvement_score: number;
  created_at: string;
}

// 行业选项
const industryOptions = [
  { value: 'retail', label: '零售' },
  { value: 'finance', label: '金融' },
  { value: 'manufacturing', label: '制造业' },
  { value: 'healthcare', label: '医疗健康' },
  { value: 'education', label: '教育' },
  { value: 'technology', label: '科技' },
  { value: 'general', label: '通用' },
];

// 问题类型选项
const problemTypeOptions = [
  { value: 'lead_conversion', label: '线索转化' },
  { value: 'customer_retention', label: '客户留存' },
  { value: 'marketing_roi', label: '营销ROI' },
  { value: 'operation_efficiency', label: '运营效率' },
  { value: 'data_integration', label: '数据整合' },
  { value: 'team_collaboration', label: '团队协作' },
];

export default function CasesPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<{
    industry?: string;
    problem_type?: string;
    min_score?: number;
    limit: number;
  }>({
    limit: 10,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const skip = useMemo(() => (currentPage - 1) * filters.limit, [currentPage, filters.limit]);
  
  const { data, isLoading, refetch } = useCaseSearch({ ...filters, skip });
  const cases = (data as { cases?: CaseItem[]; total?: number })?.cases || [];
  const total = (data as { cases?: CaseItem[]; total?: number })?.total || 0;

  // 查看案例详情
  const handleViewDetail = (caseId: string) => {
    navigate(`/tracking/cases/${caseId}`);
  };

  // 更新筛选条件
  const updateFilter = (key: string, value: unknown) => {
    setFilters(prev => ({
      ...prev,
      [key]: value || undefined,
    }));
    setCurrentPage(1); // 筛选条件改变时重置到第一页
  };

  // 重置筛选
  const resetFilters = () => {
    setFilters({ limit: 10 });
    setCurrentPage(1);
  };

  const columns: ColumnsType<CaseItem> = [
    {
      title: '案例标题',
      dataIndex: 'title',
      key: 'title',
      render: (title: string) => (
        <span className="font-medium text-white">{title}</span>
      ),
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 100,
      render: (industry: string) => (
        <Tag color="blue">
          {industryOptions.find(o => o.value === industry)?.label || industry}
        </Tag>
      ),
    },
    {
      title: '问题类型',
      dataIndex: 'problem_type',
      key: 'problem_type',
      width: 120,
      render: (type: string) => (
        <Tag color="purple">
          {problemTypeOptions.find(o => o.value === type)?.label || type}
        </Tag>
      ),
    },
    {
      title: '提升效果',
      dataIndex: 'improvement_score',
      key: 'improvement_score',
      width: 120,
      render: (score: number) => {
        const color = score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-gray-400';
        return (
          <span className={`font-bold ${color}`}>
            <StarOutlined className="mr-1" />
            {score}分
          </span>
        );
      },
    },
    {
      title: '方案摘要',
      dataIndex: 'solution_summary',
      key: 'solution_summary',
      ellipsis: true,
      render: (summary: string) => (
        <span className="text-gray-400 text-sm">{summary}</span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => (
        <span className="text-gray-500 text-sm">
          {dayjs(date).format('YYYY-MM-DD')}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button 
          type="link" 
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record.id)}
        >
          查看
        </Button>
      ),
    },
  ];

  // 统计数据
  const stats = cases.length > 0 ? {
    total: total,
    avgScore: Math.round(cases.reduce((sum, c) => sum + c.improvement_score, 0) / cases.length),
    highScore: cases.filter(c => c.improvement_score >= 80).length,
  } : null;

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-indigo-500/20">
              <BookOutlined />
            </span>
            案例库
          </h1>
          <p className="text-gray-400 mt-2 text-sm">
            浏览成功案例，借鉴优秀实践经验
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            icon={<FilterOutlined />}
            onClick={() => setShowFilters(!showFilters)}
          >
            {showFilters ? '收起筛选' : '展开筛选'}
          </Button>
        </div>
      </div>

      {/* 筛选区域 */}
      {showFilters && (
        <Card size="small">
          <Row gutter={16} align="middle">
            <Col span={5}>
              <div className="text-gray-400 text-xs mb-1">行业</div>
              <Select
                placeholder="选择行业"
                allowClear
                style={{ width: '100%' }}
                value={filters.industry}
                onChange={(v) => updateFilter('industry', v)}
                options={industryOptions}
              />
            </Col>
            <Col span={5}>
              <div className="text-gray-400 text-xs mb-1">问题类型</div>
              <Select
                placeholder="选择问题类型"
                allowClear
                style={{ width: '100%' }}
                value={filters.problem_type}
                onChange={(v) => updateFilter('problem_type', v)}
                options={problemTypeOptions}
              />
            </Col>
            <Col span={6}>
              <div className="text-gray-400 text-xs mb-1">
                最低提升分数: {filters.min_score || 0}
              </div>
              <Slider
                min={0}
                max={100}
                value={filters.min_score || 0}
                onChange={(v) => updateFilter('min_score', v > 0 ? v : undefined)}
              />
            </Col>
            <Col span={4}>
              <div className="text-gray-400 text-xs mb-1">显示数量</div>
              <Select
                style={{ width: '100%' }}
                value={filters.limit}
                onChange={(v) => updateFilter('limit', v)}
                options={[
                  { value: 10, label: '10条' },
                  { value: 20, label: '20条' },
                  { value: 50, label: '50条' },
                ]}
              />
            </Col>
            <Col span={4} className="flex gap-2">
              <Button onClick={resetFilters}>重置</Button>
              <Button type="primary" icon={<SearchOutlined />} onClick={() => refetch()}>
                搜索
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16}>
          <Col span={8}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">{stats.total}</div>
              <div className="text-gray-400 text-sm mt-1">案例总数</div>
            </Card>
          </Col>
          <Col span={8}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-emerald-400">{stats.highScore}</div>
              <div className="text-gray-400 text-sm mt-1">高分案例</div>
            </Card>
          </Col>
          <Col span={8}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-amber-400">{stats.avgScore}</div>
              <div className="text-gray-400 text-sm mt-1">平均提升分</div>
            </Card>
          </Col>
        </Row>
      )}

      {/* 案例列表 */}
      <Card>
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={cases}
            rowKey="id"
            pagination={{
              current: currentPage,
              pageSize: filters.limit,
              total: total,
              showTotal: (t) => `共 ${t} 个案例`,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (page, size) => {
                setCurrentPage(page);
                if (size !== filters.limit) {
                  setFilters(prev => ({ ...prev, limit: size }));
                  setCurrentPage(1);
                }
              },
              onShowSizeChange: (current, size) => {
                setFilters(prev => ({ ...prev, limit: size }));
                setCurrentPage(1);
              },
            }}
            locale={{
              emptyText: <Empty description="暂无案例数据" />,
            }}
          />
        )}
      </Card>
    </div>
  );
}

