

import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useState } from 'react';
import { Card, Spin, Empty, Button, Tag, Table, Row, Col } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  ArrowLeftOutlined, 
  LoadingOutlined,
  LineChartOutlined,
  TableOutlined,
} from '@ant-design/icons';
import { useDrillDownData, useDimensionConfig, useEnterpriseDetail } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import dayjs from 'dayjs';
import { PieChart } from '@/components/diagnosis/pie-chart';

// 类型定义
interface DrillDownData {
  metric_name: string;
  dimension: string;
  time_range: { start: string; end: string };
  data: Array<Record<string, unknown>>;
  total: number;
  page: number;
  page_size: number;
  field_labels?: Record<string, string>;  // 后端返回的字段标签映射
}

// 状态颜色映射
const statusColorMap: Record<string, string> = {
  '已转化': 'green',
  '跟进中': 'blue', 
  '已流失': 'red',
  '活跃': 'green',
  '沉默': 'orange',
  '流失': 'red',
};

export default function DrillDownPage() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  
  const metricName = decodeURIComponent(params.metricName as string);
  const dimension = searchParams.get('dimension') || 'crm';
  
  const enterpriseId = currentEnterprise?.id || null;

  const { data: enterpriseDetail, isLoading: isEnterpriseLoading } = useEnterpriseDetail(enterpriseId);
  const analysisPeriodDays =
    (enterpriseDetail as { config?: { analysis_period_days?: number } } | undefined)?.config
      ?.analysis_period_days ?? 30;

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  
  // 使用统一的维度配置 hook
  const { getMetricDisplayName } = useDimensionConfig(enterpriseId);
  
  // 获取钻取数据
  const { data: rawDrillData, isLoading } = useDrillDownData(
    metricName,
    enterpriseId,
    dimension,
    analysisPeriodDays,
    currentPage,
    pageSize,
    { enabled: !isEnterpriseLoading }
  );
  const drillData = rawDrillData as DrillDownData | undefined;

  // 返回上一页
  const handleBack = () => {
    navigate(-1);
  };
  
  // 动态生成表格列
  const generateColumns = (): ColumnsType<Record<string, unknown>> => {
    if (!drillData?.data || drillData.data.length === 0) {
      return [];
    }
    
    const sampleRow = drillData.data[0] as Record<string, unknown>;
    const columns: ColumnsType<Record<string, unknown>> = [];
    
    Object.keys(sampleRow).forEach((key) => {
      const column: ColumnsType<Record<string, unknown>>[0] = {
        title: getColumnTitle(key),
        dataIndex: key,
        key: key,
      };
      
      // 特殊列处理
      if (key === 'status') {
        column.render = (status: string) => (
          <Tag color={statusColorMap[status] || 'default'}>{status}</Tag>
        );
        column.width = 100;
      } else if (key.includes('_at') || key.includes('date') || key.includes('time')) {
        column.render = (date: string) => (
          date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
        );
        column.width = 160;
      } else if (key.includes('rate') || key.includes('percentage')) {
        column.render = (value: number) => (
          typeof value === 'number' ? `${value.toFixed(1)}%` : value
        );
        column.width = 100;
      } else if (key.includes('_id') || key === 'id') {
        column.render = (id: string) => (
          <span className="font-mono text-xs text-gray-400">{id?.substring(0, 12)}...</span>
        );
        column.width = 140;
      }
      
      columns.push(column);
    });
    
    return columns;
  };
  
  // 获取列标题 - 优先使用后端返回的字段映射
  const getColumnTitle = (key: string): string => {
    // 优先使用后端返回的 field_labels
    if (drillData?.field_labels && drillData.field_labels[key]) {
      return drillData.field_labels[key];
    }
    
    // 后备：本地最小化映射（仅用于后端未提供的情况）
    const fallbackMapping: Record<string, string> = {
      id: 'ID',
      status: '状态',
      created_at: '创建时间',
      updated_at: '更新时间',
      value: '数值',
      date: '日期',
      name: '名称',
      type: '类型',
    };
    
    return fallbackMapping[key] || key;
  };
  
  // 计算统计数据（使用总数而不是当前页数据）
  const calculateStats = () => {
    if (!drillData || drillData.total === 0) {
      return null;
    }
    
    const total = drillData.total;
    const data = drillData.data as Array<Record<string, unknown>>;
    
    // 如果有status字段，统计分布
    const statusCounts: Record<string, number> = {};
    data.forEach((item) => {
      const status = item.status as string | undefined;
      if (status) {
        statusCounts[status] = (statusCounts[status] || 0) + 1;
      }
    });
    
    // 如果有source字段，统计来源分布
    const sourceCounts: Record<string, number> = {};
    data.forEach((item) => {
      const source = item.source as string | undefined;
      if (source) {
        sourceCounts[source] = (sourceCounts[source] || 0) + 1;
      }
    });
    
    return { total, statusCounts, sourceCounts };
  };
  
  const stats = calculateStats();
  
  // 加载中（先等企业配置，再钻取，保证 days 与「数据分析周期」一致）
  if (isEnterpriseLoading || isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-4">
        <Button 
          icon={<ArrowLeftOutlined />}
          style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }} 
          onClick={handleBack}
          className="!flex !items-center"
        />
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg shadow-cyan-500/20">
              <LineChartOutlined />
            </span>
            指标钻取分析
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            深入分析 <span className="text-cyan-400">{getMetricDisplayName(metricName)}</span> 的明细数据
          </p>
          {drillData?.time_range && (
            <div className="text-gray-500 text-sm mt-2">
              数据范围: {dayjs(drillData.time_range.start).format('YYYY-MM-DD')} ~{' '}
              {dayjs(drillData.time_range.end).format('YYYY-MM-DD')}
            </div>
          )}
        </div>
      </div>

      {/* 统计卡片（状态分布，有 status 列时展示） */}
      {stats && Object.keys(stats.statusCounts).length > 0 && (
        <Row gutter={16}>
          {Object.entries(stats.statusCounts).slice(0, 3).map(([status, count]) => (
            <Col span={6} key={status}>
              <Card className="text-center">
                <div className={`text-3xl font-bold ${
                  status === '已转化' || status === '活跃' ? 'text-emerald-400' :
                  status === '已流失' || status === '流失' ? 'text-rose-400' : 'text-amber-400'
                }`}>
                  {count}
                </div>
                <div className="text-gray-400 text-sm mt-1">{status}</div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 数据表格 */}
      <Card 
        title={
          <div className="flex items-center gap-2">
            <TableOutlined className="text-cyan-400" />
            <span>明细数据</span>
            {drillData && (
              <Tag color="blue">{drillData.total} 条</Tag>
            )}
          </div>
        }
      >
        {drillData?.data && drillData.data.length > 0 ? (
          <Table
            columns={generateColumns()}
            dataSource={drillData.data.map((item: Record<string, unknown>, index: number) => ({ ...item, key: index }))}
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: drillData.total,
              showTotal: (total) => `共 ${total} 条记录`,
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
            scroll={{ x: 'max-content' }}
            size="small"
          />
        ) : (
          <Empty description="暂无钻取数据" />
        )}
      </Card>

      {/* 来源分布（如果有） */}
      {stats?.sourceCounts && Object.keys(stats.sourceCounts).length > 0 && (
        <Card 
          title={
            <div className="flex items-center gap-2">
              <LineChartOutlined className="text-purple-400" />
              <span>来源渠道分布</span>
            </div>
          }
        >
          <PieChart
            data={Object.entries(stats.sourceCounts).map(([name, value]) => ({
              name,
              value: value as number,
            }))}
            height={350}
          />
        </Card>
      )}
    </div>
  );
}
