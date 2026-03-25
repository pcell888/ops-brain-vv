

import { useMemo, useState } from 'react';
import { Card, Table, Tag, Button, Empty, Spin, Progress, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  FileSearchOutlined, 
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  LoadingOutlined,
  WifiOutlined,
  DisconnectOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { 
  useDiagnosisList, 
  useWebSocket,
  useDiagnosisTaskStatus,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import type { DiagnosisListItem, DiagnosisListResponse } from '@/lib/types';

// 状态标签配置
const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '运行中' },
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' },
  failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
};

// 触发类型配置
const triggerTypeConfig: Record<string, { text: string; color: string }> = {
  manual: { text: '手动触发', color: 'blue' },
  scheduled: { text: '定时任务', color: 'cyan' },
  auto: { text: '自动触发', color: 'purple' },
};

export default function DiagnosisReportsPage() {
  const { currentEnterprise } = useAppStore();
  const navigate = useNavigate();
  const enterpriseId = currentEnterprise?.id || null;
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const skip = useMemo(() => (currentPage - 1) * pageSize, [currentPage, pageSize]);
  
  const { data, isLoading, refetch } = useDiagnosisList(enterpriseId, skip, pageSize);
  const typedData = data as DiagnosisListResponse | undefined;

  // WebSocket 连接
  const { connected } = useWebSocket(enterpriseId);
  
  // 诊断任务状态监听 - 状态和进度直接在列表中显示
  const { tasks } = useDiagnosisTaskStatus(enterpriseId, {
    onCompleted: () => {
      // 完成时刷新列表
      refetch();
    },
    onFailed: () => {
      // 失败时刷新列表
      refetch();
    },
  });

  // 合并 WebSocket 实时状态到列表数据
  const listDataWithRealtimeStatus = useMemo(() => {
    if (!typedData?.items) return [];
    
    return typedData.items.map(item => {
      // 查找对应的实时任务状态
      const realtimeTask = Object.values(tasks).find(
        t => t.task_id === item.diagnosis_id
      );
      
      if (realtimeTask) {
        return {
          ...item,
          status: realtimeTask.status,
          progress: realtimeTask.progress,
          message: realtimeTask.message || undefined,
        };
      }
      return item;
    });
  }, [typedData?.items, tasks]);

  // 查看报告详情 - 跳转到详情页
  const handleViewDetail = (diagnosisId: string) => {
    navigate(`/diagnosis/${diagnosisId}`);
  };

  const columns: ColumnsType<DiagnosisListItem> = [
    {
      title: '诊断ID',
      dataIndex: 'diagnosis_id',
      key: 'diagnosis_id',
      width: 140,
      render: (id: string) => (
        <span className="font-mono text-xs text-muted">
          {id.substring(0, 8)}...
        </span>
      ),
    },
    {
      title: '状态/进度',
      dataIndex: 'status',
      key: 'status',
      width: 200,
      render: (status: string, record: DiagnosisListItem) => {
        const config = statusConfig[status] || statusConfig.pending;
        const isRunning = status === 'running' || status === 'pending';
        const isFailed = status === 'failed';
        const errorMessage = record.error_message || record.message;
        
        return (
          <div className="space-y-1">
            <Tag icon={config.icon} style={{ backgroundColor: config.color === 'success' ? 'rgba(82, 196, 26, 0.2)' : config.color === 'processing' ? 'rgba(16, 142, 233, 0.2)' : config.color === 'error' ? 'rgba(245, 34, 45, 0.2)' : 'rgba(0, 0, 0, 0.2)', color: config.color === 'success' ? '#52c41a' : config.color === 'processing' ? '#108ee9' : config.color === 'error' ? '#f5222d' : '#000000', border: 'none' }}>
              {config.text}
            </Tag>
            {isRunning && (
              <div className="w-full">
                <Progress 
                  percent={record.progress || 0} 
                  size="small" 
                  status="active"
                  format={(percent) => `${percent}%`}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
                {record.message && (
                  <div className="text-xs text-muted truncate" title={record.message}>
                  {record.message}
                </div>
                )}
              </div>
            )}
            {isFailed && errorMessage && (
              <Tooltip title={errorMessage} placement="topLeft">
                <div className="text-xs text-accent-rose truncate max-w-[180px] cursor-help">
                  {errorMessage}
                </div>
              </Tooltip>
            )}
          </div>
        );
      },
    },
    {
      title: '健康度评分',
      dataIndex: 'health_score',
      key: 'health_score',
      width: 120,
      render: (score: number | null) => {
        if (score === null || score === undefined) {
          return <span className="text-muted">-</span>;
        }
        const color = score >= 80 ? 'text-accent-emerald' : score >= 60 ? 'text-accent-amber' : 'text-accent-rose';
        return (
          <span className={`font-bold text-lg ${color}`}>
            {score.toFixed(0)}
            <span className="text-xs text-muted ml-1">分</span>
          </span>
        );
      },
    },
    {
      title: '诊断结果',
      dataIndex: 'anomaly_count',
      key: 'anomaly_count',
      width: 120,
      render: (count: number | undefined, record: DiagnosisListItem) => {
        if (record.status !== 'completed') {
          return <span className="text-muted">-</span>;
        }
        if (count === 0) {
          return (
            <Tag icon={<CheckCircleOutlined />} style={{ backgroundColor: 'rgba(82, 196, 26, 0.2)', color: '#52c41a', border: 'none' }}>
              无异常
            </Tag>
          );
        }
        return (
          <Tag icon={<WarningOutlined />} style={{ backgroundColor: 'rgba(250, 173, 20, 0.2)', color: '#faad14', border: 'none' }}>
            {count} 个异常
          </Tag>
        );
      },
    },
    {
      title: '触发方式',
      dataIndex: 'trigger_type',
      key: 'trigger_type',
      width: 100,
      render: (type: string) => {
        const config = triggerTypeConfig[type] || { text: type, color: 'default' };
        const getBackgroundColor = (color: string) => {
          switch (color) {
            case 'blue': return 'rgba(24, 144, 255, 0.2)';
            case 'cyan': return 'rgba(0, 176, 255, 0.2)';
            case 'purple': return 'rgba(120, 69, 193, 0.2)';
            default: return 'rgba(0, 0, 0, 0.2)';
          }
        };
        const getTextColor = (color: string) => {
          switch (color) {
            case 'blue': return '#1890ff';
            case 'cyan': return '#00b0ff';
            case 'purple': return '#7845c1';
            default: return '#000000';
          }
        };
        return <Tag style={{ backgroundColor: getBackgroundColor(config.color), color: getTextColor(config.color), border: 'none' }}>{config.text}</Tag>;
      },
    },
    {
      title: '诊断时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => (
        <span className="text-secondary">
          {dayjs(date).format('YYYY-MM-DD HH:mm:ss')}
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
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record.diagnosis_id)}
          disabled={record.status !== 'completed'}
        >
          查看
        </Button>
      ),
    },
  ];

  // 未选择企业
  if (!enterpriseId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Empty description="请先选择企业" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          {/* <h1 className="text-2xl font-bold text-[#303133] flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-lg shadow-lg shadow-cyan-500/20 text-white">
              <FileSearchOutlined />
            </span>
            诊断历史
          </h1> */}
          <p className="text-[#303133] mt-2 text-sm">
            查看历史诊断报告，追踪企业运营健康度变化趋势
          </p>
        </div>
        <div className="flex gap-3 items-center">
          {/* WebSocket 连接状态指示器 */}
          <div className="flex items-center gap-1.5 text-xs">
            {connected ? (
              <>
                <WifiOutlined className="text-accent-emerald" />
                <span className="text-accent-emerald">实时连接</span>
              </>
            ) : (
              <>
                <DisconnectOutlined className="text-muted" />
                <span className="text-muted">离线</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 报告列表 */}
      <Card>
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={listDataWithRealtimeStatus}
            rowKey="diagnosis_id"
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: typedData?.total || 0,
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
            locale={{
              emptyText: <Empty description="暂无诊断记录" />,
            }}
          />
        )}
      </Card>

    </div>
  );
}

