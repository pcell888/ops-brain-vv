import { Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Button, Empty, Spin, Row, Col, App, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  BulbOutlined,
  CheckCircleOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import {
  useLatestDiagnosisReport,
  useSolutionList,
  useAdoptSolution,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import type { SolutionSummary, Anomaly } from '@/lib/types';

export default function SolutionsPageWrapper() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-[60vh]"><Spin size="large" /></div>}>
      <SolutionsPage />
    </Suspense>
  );
}

function SolutionsPage() {
  const { message } = App.useApp();
  const { currentEnterprise } = useAppStore();
  const navigate = useNavigate();
  const enterpriseId = currentEnterprise?.id || null;

  const { latestDiagnosisId, data: diagnosisReport, isLoading: diagnosisLoading } = useLatestDiagnosisReport(enterpriseId);
  const { data: solutionData, isLoading: solutionsLoading, refetch } = useSolutionList(latestDiagnosisId || null);
  const adoptSolution = useAdoptSolution();

  const isLoading = diagnosisLoading || solutionsLoading;

  const handleAdopt = async (solutionId: string) => {
    try {
      await adoptSolution.mutateAsync(solutionId);
      message.success('方案已采纳');
      refetch();
    } catch {
      message.error('采纳失败');
    }
  };

  const handleViewDetail = (solutionId: string) => {
    if (latestDiagnosisId) {
      navigate(`/solutions/${latestDiagnosisId}?solution_id=${solutionId}`);
    }
  };

  const columns: ColumnsType<SolutionSummary> = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 70,
      render: (rank: number) => (
        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
          rank === 1 ? 'bg-amber-500/20 text-amber-400' :
          rank === 2 ? 'bg-gray-400/20 text-gray-300' :
          rank === 3 ? 'bg-orange-600/20 text-orange-400' :
          'bg-gray-700/50 text-gray-400'
        }`}>
          {rank <= 3 ? <TrophyOutlined /> : rank}
        </div>
      ),
    },
    {
      title: '方案名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <span className="font-medium text-white">{name}</span>,
    },
    {
      title: '针对异常',
      dataIndex: 'anomaly_ids',
      key: 'anomaly_ids',
      width: 200,
      render: (anomalyIds: string[] | undefined) => {
        if (!anomalyIds || anomalyIds.length === 0) return <span className="text-gray-500">-</span>;
        const anomalies = diagnosisReport?.anomalies || [];
        const matched = anomalyIds
          .map(id => anomalies.find((a: Anomaly) => a.id === id || a.metric_name === id))
          .filter(Boolean) as Anomaly[];
        if (matched.length === 0) {
          return <span className="text-gray-500">{anomalyIds.length}个异常</span>;
        }
        return (
          <div className="flex flex-wrap gap-1">
            {matched.slice(0, 3).map((a) => (
              <Tag key={a.id} color="orange" className="!m-0">{a.rule_name}</Tag>
            ))}
            {matched.length > 3 && <Tag color="orange" className="!m-0">+{matched.length - 3}</Tag>}
          </div>
        );
      },
    },
    {
      title: '推荐评分',
      dataIndex: 'score',
      key: 'score',
      width: 100,
      render: (score: number) => (
        <span className={`font-bold ${score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-rose-400'}`}>
          {score.toFixed(1)}
        </span>
      ),
    },
    {
      title: '预计周期',
      dataIndex: 'estimated_duration',
      key: 'estimated_duration',
      width: 90,
      render: (days: number) => (
        <span className="text-gray-300"><ClockCircleOutlined className="mr-1" />{days}天</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => {
        if (status === 'adopted') return <Tag color="green">已采纳</Tag>;
        if (status === 'rejected') return <Tag color="red">已拒绝</Tag>;
        return <Tag color="default">待评估</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => {
        const isAdopted = record.status === 'adopted';
        const isRejected = record.status === 'rejected';
        return (
          <div className="flex gap-1">
            <Button type="link" size="small" onClick={() => handleViewDetail(record.solution_id)}>
              详情
            </Button>
            <Button
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleAdopt(record.solution_id)}
              disabled={isAdopted || isRejected}
              loading={adoptSolution.isPending}
            >
              {isAdopted ? '已采纳' : '采纳'}
            </Button>
            {isAdopted && (
              <Button
                type="link"
                size="small"
                icon={<RocketOutlined />}
                onClick={() => navigate('/execution')}
              >
                查看执行
              </Button>
            )}
          </div>
        );
      },
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
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-lg shadow-lg shadow-amber-500/20">
            <BulbOutlined />
          </span>
          优化方案
        </h1>
        <p className="text-gray-400 mt-2 text-sm">
          诊断完成后自动生成的优化方案，按综合评分排序
        </p>
      </div>

      {solutionData && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">
                {solutionData.total || solutionData.solutions?.length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">方案总数</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-emerald-400">
                {solutionData.solutions?.filter((s: SolutionSummary) => s.status === 'adopted').length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">已采纳</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-amber-400">
                {solutionData.solutions?.[0]?.score?.toFixed(1) || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">最高评分</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-purple-400">
                {diagnosisReport?.anomalies?.length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">异常指标数</div>
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
          </div>
        ) : !latestDiagnosisId ? (
          <Empty description="请先完成诊断后查看方案" />
        ) : (
          <Table
            columns={columns}
            dataSource={solutionData?.solutions || []}
            rowKey="solution_id"
            pagination={false}
            locale={{ emptyText: <Empty description="暂无方案，请先在仪表盘完成诊断" /> }}
          />
        )}
      </Card>
    </div>
  );
}
