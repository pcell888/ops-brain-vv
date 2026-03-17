

import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useState } from 'react';
import { 
  Card, Spin, Empty, Button, Tag, Select, 
  Table, Row, Col, Statistic 
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  ArrowLeftOutlined, 
  LoadingOutlined,
  LineChartOutlined,
  TableOutlined,
  ReloadOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import { useDrillDownData, useDiagnosisReport, useDimensionConfig } from '@/lib/hooks';
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
  
  const diagnosisId = params.diagnosisId as string;
  const metricName = decodeURIComponent(params.metricName as string);
  const dimension = searchParams.get('dimension') || 'crm';
  
  const enterpriseId = currentEnterprise?.id || null;
  
  const [days, setDays] = useState(90);
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table');
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  
  // 切换时间范围时重置到第一页
  const handleDaysChange = (newDays: number) => {
    setDays(newDays);
    setCurrentPage(1);
  };
  
  // 使用统一的维度配置 hook
  const { getDimensionDisplayName, getMetricDisplayName } = useDimensionConfig(enterpriseId);
  
  // 获取钻取数据
  const { data: rawDrillData, isLoading, refetch } = useDrillDownData(
    metricName,
    enterpriseId,
    dimension,
    days,
    currentPage,
    pageSize
  );
  const drillData = rawDrillData as DrillDownData | undefined;
  
  // 获取诊断报告以显示上下文
  const { data: reportData } = useDiagnosisReport(diagnosisId);
  const report = reportData as { anomalies?: Array<{ metric_name: string; current_value: number; benchmark_value?: number; severity: string; dimension?: string; unit?: string }>; health_score?: { dimension_scores?: Array<{ dimension: string; metrics_detail?: Array<{ name: string; unit?: string }> }> } } | undefined;
  
  // 找到对应的异常信息
  const anomaly = report?.anomalies?.find((a) => a.metric_name === metricName);
  // 从 metrics_detail 获取单位
  const _ds = report?.health_score?.dimension_scores?.find(ds => ds.dimension === dimension);
  const _md = _ds?.metrics_detail?.find(m => m.name === metricName);
  const unit = anomaly?.unit || _md?.unit || '%';
  
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
  
  // 加载中
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button 
            icon={<ArrowLeftOutlined />} 
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
          </div>
        </div>
        <div className="flex gap-3">
          <Select
            value={days}
            onChange={handleDaysChange}
            style={{ width: 120 }}
            options={[
              { value: 30, label: '近30天' },
              { value: 60, label: '近60天' },
              { value: 90, label: '近90天' },
              { value: 180, label: '近180天' },
            ]}
          />
          <Button 
            icon={viewMode === 'table' ? <LineChartOutlined /> : <TableOutlined />}
            onClick={() => setViewMode(viewMode === 'table' ? 'chart' : 'table')}
          >
            {viewMode === 'table' ? '图表视图' : '表格视图'}
          </Button>
          <Button 
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
          >
            刷新
          </Button>
        </div>
      </div>

      {/* 指标概览 */}
      <Card className="border-l-4 border-l-cyan-500">
        <Row gutter={24}>
          <Col span={6}>
            <Statistic 
              title="指标名称"
              value={getMetricDisplayName(metricName)}
              valueStyle={{ fontSize: 18, color: '#fff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="所属维度"
              value={getDimensionDisplayName(dimension)}
              valueStyle={{ fontSize: 18, color: '#fff' }}
            />
          </Col>
          {anomaly && (
            <>
              <Col span={6}>
                <Statistic 
                  title="当前值"
                  value={anomaly.current_value}
                  suffix={unit}
                  valueStyle={{ 
                    fontSize: 18, 
                    color: anomaly.severity === 'critical' || anomaly.severity === 'high' 
                      ? '#f43f5e' : '#f59e0b' 
                  }}
                  prefix={<FallOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic 
                  title="行业基准"
                  value={anomaly.benchmark_value || '-'}
                  suffix={unit}
                  valueStyle={{ fontSize: 18, color: '#10b981' }}
                  prefix={<RiseOutlined />}
                />
              </Col>
            </>
          )}
        </Row>
        {drillData?.time_range && (
          <div className="mt-4 text-sm text-gray-500">
            数据范围: {dayjs(drillData.time_range.start).format('YYYY-MM-DD')} ~ {dayjs(drillData.time_range.end).format('YYYY-MM-DD')}
          </div>
        )}
      </Card>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">{stats.total}</div>
              <div className="text-gray-400 text-sm mt-1">记录总数</div>
            </Card>
          </Col>
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
