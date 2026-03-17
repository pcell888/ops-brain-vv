

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Button, Empty, Spin, Select, Row, Col, Progress } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  AppstoreOutlined, 
  DollarOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useSolutionTemplates } from '@/lib/hooks';
import type { SolutionTemplate } from '@/lib/types';

// 分类配置
const categoryConfig: Record<string, { label: string; color: string }> = {
  sales_process: { label: '销售流程', color: 'blue' },
  marketing_optimization: { label: '营销优化', color: 'purple' },
  customer_retention: { label: '客户留存', color: 'green' },
  efficiency_improvement: { label: '效率提升', color: 'orange' },
};

export default function SolutionLibraryPage() {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const skip = useMemo(() => (currentPage - 1) * pageSize, [currentPage, pageSize]);
  
  // 空字符串表示全部，传给 hook 时转为 undefined
  const { data: rawData, isLoading } = useSolutionTemplates(
    selectedCategory || undefined,
    skip,
    pageSize
  );
  const data = rawData as { templates: SolutionTemplate[]; total: number } | undefined;

  const handleViewDetail = (template: SolutionTemplate) => {
    navigate(`/solutions/library/${template.template_id}`);
  };

  const columns: ColumnsType<SolutionTemplate> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: SolutionTemplate) => (
        <span 
          className="font-medium text-white hover:text-indigo-400 cursor-pointer transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            handleViewDetail(record);
          }}
        >
          {name}
        </span>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => {
        const config = categoryConfig[category] || { label: category, color: 'default' };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      width: 140,
      render: (rate: number) => (
        <div className="flex items-center gap-2">
          <Progress 
            percent={Math.round(rate * 100)} 
            size="small" 
            strokeColor={rate >= 0.8 ? '#10b981' : rate >= 0.6 ? '#f59e0b' : '#ef4444'}
            showInfo={false}
            className="w-16"
          />
          <span className={`font-medium ${
            rate >= 0.8 ? 'text-emerald-400' : rate >= 0.6 ? 'text-amber-400' : 'text-rose-400'
          }`}>
            {(rate * 100).toFixed(0)}%
          </span>
        </div>
      ),
    },
    {
      title: '预估成本',
      dataIndex: 'estimated_cost',
      key: 'estimated_cost',
      width: 120,
      render: (cost: number) => (
        <span className="text-gray-300">
          <DollarOutlined className="mr-1" />
          {cost >= 10000 ? `${(cost / 10000).toFixed(1)}万` : `${cost}`}
        </span>
      ),
    },
    {
      title: '预计周期',
      dataIndex: 'estimated_duration_days',
      key: 'estimated_duration_days',
      width: 100,
      render: (days: number) => (
        <span className="text-gray-300">
          <ClockCircleOutlined className="mr-1" />
          {days}天
        </span>
      ),
    },
    {
      title: '任务数',
      dataIndex: 'task_count',
      key: 'task_count',
      width: 80,
      render: (count: number) => (
        <Tag color="blue">{count}个</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button 
          type="link" 
          icon={<EyeOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            handleViewDetail(record);
          }}
        >
          查看
        </Button>
      ),
    },
  ];

  // 统计数据
  const stats = data?.templates ? {
    total: data.total,
    highSuccess: data.templates.filter(t => t.success_rate >= 0.8).length,
    avgDuration: Math.round(data.templates.reduce((sum, t) => sum + t.estimated_duration_days, 0) / data.templates.length) || 0,
    avgCost: Math.round(data.templates.reduce((sum, t) => sum + t.estimated_cost, 0) / data.templates.length) || 0,
  } : null;

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-lg shadow-lg shadow-indigo-500/20">
              <AppstoreOutlined />
            </span>
            方案库
          </h1>
          <p className="text-gray-400 mt-2 text-sm">
            浏览和管理标准化方案模板，支持按分类筛选
          </p>
        </div>
        <Select
          placeholder="选择分类"
          style={{ width: 160 }}
          value={selectedCategory}
          onChange={(v) => {
            setSelectedCategory(v);
            setCurrentPage(1); // 切换分类时重置到第一页
          }}
          options={[
            { value: '', label: '全部分类' },
            { value: 'sales_process', label: '销售流程' },
            { value: 'marketing_optimization', label: '营销优化' },
            { value: 'customer_retention', label: '客户留存' },
            { value: 'efficiency_improvement', label: '效率提升' },
          ]}
        />
      </div>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">{stats.total}</div>
              <div className="text-gray-400 text-sm mt-1">模板总数</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-emerald-400">{stats.highSuccess}</div>
              <div className="text-gray-400 text-sm mt-1">高成功率模板</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-amber-400">{stats.avgDuration}天</div>
              <div className="text-gray-400 text-sm mt-1">平均周期</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-purple-400">
                {stats.avgCost >= 10000 ? `${(stats.avgCost / 10000).toFixed(1)}万` : stats.avgCost}
              </div>
              <div className="text-gray-400 text-sm mt-1">平均成本</div>
            </Card>
          </Col>
        </Row>
      )}

      {/* 模板列表 */}
      <Card>
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={data?.templates || []}
            rowKey="template_id"
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: data?.total || 0,
              showTotal: (total) => `共 ${total} 个模板`,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (page, size) => {
                setCurrentPage(page);
                if (size !== pageSize) {
                  setPageSize(size);
                  setCurrentPage(1);
                }
              },
              onShowSizeChange: (current, size) => {
                setPageSize(size);
                setCurrentPage(1);
              },
            }}
            locale={{
              emptyText: <Empty description="暂无方案模板" />,
            }}
            onRow={(record) => ({
              onClick: () => handleViewDetail(record),
              className: 'cursor-pointer hover:bg-gray-800/30 transition-colors',
            })}
          />
        )}
      </Card>

    </div>
  );
}

