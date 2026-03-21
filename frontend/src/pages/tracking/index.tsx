

import { useState, useMemo, useEffect } from 'react';
import { 
  Card, Table, Tag, Button, Empty, Spin, Progress, Row, Col, 
  Modal, Descriptions, App, Statistic
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  LineChartOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  LoadingOutlined,
  EyeOutlined,
  FileTextOutlined,
  RiseOutlined,
  FallOutlined,
  BookOutlined,
  BarChartOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { 
  useDiagnosisSelection,
  useTrackingList, 
  useTakeSnapshot,
  useCompleteTracking,
  useCancelTracking,
} from '@/lib/hooks';
import { DiagnosisHistorySelect } from '@/components/diagnosis-history-select';
import { useAppStore } from '@/stores/app-store';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import type { TrackingSummary } from '@/lib/types';

// 状态配置
const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  active: { color: 'processing', icon: <SyncOutlined spin />, text: '追踪中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  cancelled: { color: 'default', icon: <StopOutlined />, text: '已取消' },
  paused: { color: 'warning', icon: <ClockCircleOutlined />, text: '已暂停' },
};

export default function TrackingPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  const { diagnosisItems, selectedDiagnosisId, setSelectedDiagnosisId, listLoading } =
    useDiagnosisSelection(enterpriseId);
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  
  // 计算 skip，使用 useMemo 确保依赖正确
  const skip = useMemo(() => (currentPage - 1) * pageSize, [currentPage, pageSize]);

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedDiagnosisId]);
  
  // 获取追踪列表
  const { data: trackingsData, isLoading, refetch } = useTrackingList(
    enterpriseId,
    undefined,
    skip,
    pageSize,
    selectedDiagnosisId,
  );
  const pageLoading = listLoading || isLoading;
  
  // 操作 hooks
  const takeSnapshot = useTakeSnapshot();
  const completeTracking = useCompleteTracking();
  const cancelTracking = useCancelTracking();

  // 处理取消追踪
  const handleCancelTracking = async (trackingId: string) => {
    Modal.confirm({
      title: '确认停止追踪',
      content: '停止后将无法继续采集数据，是否确认？',
      okText: '确认停止',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await cancelTracking.mutateAsync(trackingId);
          message.success('追踪已停止');
          refetch();
        } catch {
          message.error('停止追踪失败');
        }
      },
    });
  };

  // 处理采集快照
  const handleTakeSnapshot = async (trackingId: string) => {
    try {
      await takeSnapshot.mutateAsync(trackingId);
      message.success('快照已采集');
      refetch();
    } catch {
      message.error('快照采集失败');
    }
  };

  // 处理完成追踪
  const handleCompleteTracking = async (trackingId: string) => {
    try {
      await completeTracking.mutateAsync(trackingId);
      message.success('追踪已完成，复盘报告已生成');
      refetch();
    } catch {
      message.error('完成追踪失败');
    }
  };

  // 查看详情 - 跳转到详情页
  const handleViewDetail = (trackingId: string) => {
    navigate(`/tracking/${trackingId}`);
  };

  // 跳转案例库
  const handleViewCases = () => {
    navigate('/tracking/cases');
  };

  const columns: ColumnsType<TrackingSummary> = [
    {
      title: '方案名称',
      dataIndex: 'solution_name',
      key: 'solution_name',
      render: (name: string, record) => (
        <a 
          className="font-medium text-white hover:text-blue-400 cursor-pointer"
          onClick={() => handleViewDetail(record.tracking_id)}
        >
          {name}
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const config = statusConfig[status] || statusConfig.active;
        return (
          <Tag icon={config.icon} color={config.color}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '当前评分',
      dataIndex: 'current_score',
      key: 'current_score',
      width: 120,
      render: (score: number | null) => {
        if (score === null || score === undefined) {
          return <span className="text-gray-500">-</span>;
        }
        const color = score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-rose-400';
        return (
          <span className={`font-bold text-lg ${color}`}>
            {score.toFixed(0)}
            <span className="text-xs text-gray-500 ml-1">分</span>
          </span>
        );
      },
    },
    {
      title: '快照数',
      dataIndex: 'snapshot_count',
      key: 'snapshot_count',
      width: 100,
      render: (count: number) => (
        <Tag color="blue">{count}个</Tag>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 140,
      render: (date: string) => (
        <span className="text-gray-400 text-sm">
          {dayjs(date).format('MM-DD HH:mm')}
        </span>
      ),
    },
    {
      title: '最近快照',
      dataIndex: 'last_snapshot_at',
      key: 'last_snapshot_at',
      width: 140,
      render: (date: string | null) => (
        <span className="text-gray-400 text-sm">
          {date ? dayjs(date).format('MM-DD HH:mm') : '-'}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 320,
      render: (_, record) => (
        <div className="flex gap-1">
          <Button 
            type="link" 
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record.tracking_id)}
          >
            详情
          </Button>
          {record.status === 'active' && (
            <>
              <Button 
                type="link" 
                size="small"
                icon={<CameraOutlined />}
                onClick={() => handleTakeSnapshot(record.tracking_id)}
                loading={takeSnapshot.isPending}
              >
                快照
              </Button>
              <Button 
                type="link" 
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handleCompleteTracking(record.tracking_id)}
              >
                完成
              </Button>
              <Button 
                type="link" 
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => handleCancelTracking(record.tracking_id)}
                loading={cancelTracking.isPending}
              >
                停止
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  // 统计数据
  const stats = trackingsData?.items ? {
    total: trackingsData.total,
    active: trackingsData.items.filter((t: TrackingSummary) => t.status === 'active').length,
    completed: trackingsData.items.filter((t: TrackingSummary) => t.status === 'completed').length,
    avgScore: Math.round(
      trackingsData.items
        .filter((t: TrackingSummary) => t.current_score !== null)
        .reduce((sum: number, t: TrackingSummary) => sum + (t.current_score || 0), 0) / 
      trackingsData.items.filter((t: TrackingSummary) => t.current_score !== null).length
    ) || 0,
  } : null;

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
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-lg shadow-lg shadow-purple-500/20">
              <LineChartOutlined />
            </span>
            效果追踪
          </h1>
          <p className="text-gray-400 mt-2 text-sm">
            追踪方案执行效果（按所选诊断筛选）</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:flex-wrap sm:justify-end">
          {diagnosisItems.length > 0 && (
            <DiagnosisHistorySelect
              className="w-full sm:w-[min(100%,320px)]"
              diagnosisItems={diagnosisItems}
              value={selectedDiagnosisId}
              onChange={setSelectedDiagnosisId}
              loading={listLoading}
            />
          )}
          <div className="flex gap-3 shrink-0">
            <Button icon={<BookOutlined />} onClick={handleViewCases}>
              案例库
            </Button>
            <Button icon={<SyncOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">{stats.total}</div>
              <div className="text-gray-400 text-sm mt-1">追踪总数</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-amber-400">{stats.active}</div>
              <div className="text-gray-400 text-sm mt-1">追踪中</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-emerald-400">{stats.completed}</div>
              <div className="text-gray-400 text-sm mt-1">已完成</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-purple-400">{stats.avgScore}</div>
              <div className="text-gray-400 text-sm mt-1">平均评分</div>
            </Card>
          </Col>
        </Row>
      )}

      {/* 追踪列表 */}
      <Card>
        {pageLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : !selectedDiagnosisId ? (
          <Empty description="请先完成诊断" />
        ) : (
          <Table
            columns={columns}
            dataSource={trackingsData?.items || []}
            rowKey="tracking_id"
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: trackingsData?.total || 0,
              showTotal: (total) => `共 ${total} 条记录`,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: (page, size) => {
                setCurrentPage(page);
                if (size !== pageSize) {
                  setPageSize(size);
                  setCurrentPage(1); // 改变每页条数时重置到第一页
                }
              },
              onShowSizeChange: (current, size) => {
                setPageSize(size);
                setCurrentPage(1); // 改变每页条数时重置到第一页
              },
            }}
            locale={{
              emptyText: <Empty description="该次诊断下暂无追踪记录" />,
            }}
          />
        )}
      </Card>
    </div>
  );
}
