import { Card, Row, Col, Statistic, Badge, Tag, Table, Empty, Spin, Alert, Tooltip, Avatar } from 'antd';
import {
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  WarningOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { useEffect, useState, useCallback } from 'react';
import { useAppStore } from '@/stores/app-store';
import {
  useLeadList,
  useLeadStats,
  useCRMWebSocket,
  useAssignLead,
} from '@/lib/hooks';
import type { Lead, LeadEvent, AlertEvent } from '@/lib/crm-websocket';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

// 线索状态映射
const statusMap: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  created: { label: '新线索', color: 'blue', icon: <UserOutlined /> },
  assigned: { label: '已分配', color: 'cyan', icon: <TeamOutlined /> },
  contacted: { label: '已联系', color: 'orange', icon: <PhoneOutlined /> },
  qualified: { label: '已鉴别', color: 'purple', icon: <CheckCircleOutlined /> },
  negotiating: { label: '谈判中', color: 'gold', icon: <ClockCircleOutlined /> },
  converted: { label: '已转化', color: 'green', icon: <CheckCircleOutlined /> },
  lost: { label: '已流失', color: 'red', icon: <CloseCircleOutlined /> },
};

// 预警类型映射
const alertTypeMap: Record<string, { label: string; color: string }> = {
  response_timeout: { label: '响应超时', color: 'red' },
  follow_up_overdue: { label: '跟进逾期', color: 'orange' },
  roi_low: { label: 'ROI过低', color: 'yellow' },
  budget_exhausted: { label: '预算耗尽', color: 'red' },
  churn_risk_high: { label: '流失风险', color: 'red' },
  task_overdue: { label: '任务超期', color: 'orange' },
};

export default function CRMRealtimeDashboard() {
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;

  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [realtimeLeads, setRealtimeLeads] = useState<Lead[]>([]);

  // 获取线索列表和统计
  const { data: leadsData, isLoading: leadsLoading, refetch: refetchLeads } = useLeadList(enterpriseId, undefined, 0, 20);
  const { data: stats, isLoading: statsLoading } = useLeadStats(enterpriseId);

  // 分配线索 mutation
  const assignLead = useAssignLead();

  // WebSocket 事件处理
  const handleLeadCreated = useCallback((event: LeadEvent) => {
    // 新线索创建，添加到实时列表
    const newLead: Lead = {
      id: event.lead.id,
      crm_lead_id: event.lead.crm_lead_id,
      lead_name: event.lead.lead_name,
      status: event.lead.status,
      created_at: event.lead.created_at,
      updated_at: event.lead.created_at,
    };
    setRealtimeLeads(prev => [newLead, ...prev].slice(0, 10));
    refetchLeads();
  }, [refetchLeads]);

  const handleLeadAssigned = useCallback((event: LeadEvent) => {
    refetchLeads();
  }, [refetchLeads]);

  const handleAlert = useCallback((event: AlertEvent) => {
    setAlerts(prev => [event, ...prev].slice(0, 20));
  }, []);

  // WebSocket 连接
  const { connected } = useCRMWebSocket(enterpriseId, {
    onLeadCreated: handleLeadCreated,
    onLeadAssigned: handleLeadAssigned,
    onAlert: handleAlert,
  });

  // 初始化实时线索
  useEffect(() => {
    if (leadsData?.items) {
      setRealtimeLeads(leadsData.items.slice(0, 10));
    }
  }, [leadsData]);

  // 获取预警严重程度
  function getAlertSeverity(eventType: string): 'info' | 'warning' | 'critical' {
    if (eventType.includes('timeout') || eventType.includes('churn_risk')) {
      return 'critical';
    }
    if (eventType.includes('overdue')) {
      return 'warning';
    }
    return 'info';
  }

  // 表格列定义
  const columns = [
    {
      title: '客户',
      dataIndex: 'lead_name',
      key: 'lead_name',
      render: (name: string, record: Lead) => (
        <div className="flex items-center gap-2">
          <Avatar icon={<UserOutlined />} size="small" />
          <div>
            <div className="font-medium">{name}</div>
            <div className="text-xs text-gray-400">{record.company_name}</div>
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = statusMap[status] || statusMap.created;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.label}
          </Tag>
        );
      },
    },
    {
      title: '联系方式',
      key: 'contact',
      render: (_: unknown, record: Lead) => (
        <div className="space-y-1">
          {record.lead_phone && (
            <div className="text-sm flex items-center gap-1">
              <PhoneOutlined className="text-gray-400" />
              {record.lead_phone}
            </div>
          )}
          {record.lead_email && (
            <div className="text-sm flex items-center gap-1">
              <MailOutlined className="text-gray-400" />
              {record.lead_email}
            </div>
          )}
        </div>
      ),
    },
    {
      title: '分配',
      key: 'assigned',
      width: 120,
      render: (_: unknown, record: Lead) => (
        <div>
          {record.assigned_to ? (
            <div className="flex items-center gap-1">
              <TeamOutlined />
              <span>{record.assigned_to}</span>
            </div>
          ) : (
            <Tag color="default">未分配</Tag>
          )}
        </div>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          <span>{dayjs(date).fromNow()}</span>
        </Tooltip>
      ),
    },
  ];

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
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center text-lg shadow-lg shadow-blue-500/20">
              📊
            </span>
            CRM 线索实时看板
          </h1>
          <p className="text-gray-400 text-sm mt-2">
            实时监控线索流转、预警事件和转化情况
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            status={connected ? 'success' : 'error'}
            text={connected ? '实时连接' : '连接断开'}
          />
          {connected && (
            <SyncOutlined spin className="text-green-400" />
          )}
        </div>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16}>
        <Col span={4}>
          <Card>
            <Statistic
              title="总线索数"
              value={stats?.total || 0}
              loading={statsLoading}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="今日新增"
              value={stats?.today || 0}
              loading={statsLoading}
              valueStyle={{ color: '#52c41a' }}
              prefix={<Badge count="新" style={{ backgroundColor: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="待分配"
              value={stats?.created || 0}
              loading={statsLoading}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="跟进中"
              value={(stats?.assigned || 0) + (stats?.contacted || 0)}
              loading={statsLoading}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="已转化"
              value={stats?.converted || 0}
              loading={statsLoading}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="已流失"
              value={stats?.lost || 0}
              loading={statsLoading}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主要内容区 */}
      <Row gutter={16}>
        {/* 左侧：线索列表 */}
        <Col span={16}>
          <Card
            title={
              <div className="flex items-center justify-between">
                <span>最新线索</span>
                <Badge count={realtimeLeads.length} style={{ backgroundColor: '#1890ff' }} />
              </div>
            }
          >
            {leadsLoading ? (
              <div className="flex justify-center py-12">
                <Spin size="large" />
              </div>
            ) : realtimeLeads.length > 0 ? (
              <Table
                dataSource={realtimeLeads}
                columns={columns}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ y: 400 }}
              />
            ) : (
              <Empty description="暂无线索数据" />
            )}
          </Card>
        </Col>

        {/* 右侧：实时预警 */}
        <Col span={8}>
          <Card
            title={
              <div className="flex items-center gap-2">
                <BellOutlined />
                <span>实时预警</span>
                {alerts.length > 0 && (
                  <Badge count={alerts.length} style={{ backgroundColor: '#f5222d' }} />
                )}
              </div>
            }
          >
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {alerts.length === 0 ? (
                <Empty description="暂无预警事件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                alerts.map((alert) => {
                  const alertConfig = alertTypeMap[alert.event_type] || { label: '预警', color: 'blue' };
                  return (
                    <Alert
                      key={alert.id}
                      message={
                        <div className="flex items-center gap-2">
                          <Tag color={alertConfig.color}>{alertConfig.label}</Tag>
                          <span className="font-medium">{alert.lead_name}</span>
                        </div>
                      }
                      description={
                        <div>
                          <div className="text-sm">{alert.message}</div>
                          <div className="text-xs text-gray-400 mt-1">
                            {dayjs(alert.created_at).fromNow()}
                          </div>
                        </div>
                      }
                      type={alert.severity === 'critical' ? 'error' : alert.severity === 'warning' ? 'warning' : 'info'}
                      showIcon
                      icon={<WarningOutlined />}
                      className="mb-2"
                    />
                  );
                })
              )}
            </div>
          </Card>

          {/* 最近活动 */}
          <Card
            title="最近活动"
            className="mt-4"
          >
            <div className="space-y-2 text-sm">
              {realtimeLeads.slice(0, 5).map((lead, index) => (
                <div key={lead.id} className="flex items-center gap-2 text-gray-300">
                  <Badge status={index === 0 ? 'processing' : 'default'} />
                  <span className="flex-1 truncate">{lead.lead_name}</span>
                  <Tag style={{ backgroundColor: statusMap[lead.status]?.color ? `${statusMap[lead.status].color}20` : 'rgba(107, 114, 128, 0.2)', color: statusMap[lead.status]?.color || '#6b7280', border: 'none' }}>
                    {statusMap[lead.status]?.label || lead.status}
                  </Tag>
                </div>
              ))}
              {realtimeLeads.length === 0 && (
                <Empty description="暂无活动" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
