import { Suspense, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Button, Empty, Spin, Row, Col, App } from 'antd';
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
  useDiagnosisSelection,
  useDiagnosisReport,
  useSolutionList,
} from '@/lib/hooks';
import { DiagnosisHistorySelect } from '@/components/diagnosis-history-select';
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

  const { diagnosisItems, selectedDiagnosisId, setSelectedDiagnosisId, listLoading } =
    useDiagnosisSelection(enterpriseId);

  const selectedItem = useMemo(
    () => diagnosisItems.find((i) => i.diagnosis_id === selectedDiagnosisId),
    [diagnosisItems, selectedDiagnosisId],
  );
  const isCompleted = selectedItem?.status === 'completed';

  const { data: diagnosisReport, isLoading: reportLoading } = useDiagnosisReport(
    isCompleted && selectedDiagnosisId ? selectedDiagnosisId : null,
  );
  const { data: solutionData, isLoading: solutionsLoading } = useSolutionList(
    isCompleted && selectedDiagnosisId ? selectedDiagnosisId : null,
  );
  const anySolutionAdopted = solutionData?.solutions?.some((s) => s.status === 'adopted') ?? false;

  const isLoading = listLoading || (isCompleted && (reportLoading || solutionsLoading));

  const handleAdopt = (solutionId: string) => {
    if (!selectedDiagnosisId) return;
    navigate(
      `/solutions/${encodeURIComponent(selectedDiagnosisId)}?solution_id=${encodeURIComponent(solutionId)}&auto_adopt=1`,
    );
  };

  const handleViewDetail = (solutionId: string) => {
    if (selectedDiagnosisId) {
      navigate(`/solutions/${selectedDiagnosisId}?solution_id=${solutionId}`);
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
          rank === 1 ? 'bg-[#0A43FF] text-[#fff]' :
          rank === 2 ? 'bg-[#D5EAFB] text-[#0A43FF]' :
          rank === 3 ? 'bg-[#D5EAFB] text-[#0A43FF]' :
          'bg-[#D5EAFB] text-[#0A43FF]'
        }`}>
          {rank <= 3 ? rank : rank}
        </div>
      ),
    },
    {
      title: '方案名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <span className="font-medium text-primary">{name}</span>,
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
              <Tag key={a.id} style={{ backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', border: 'none' }} className="!m-0">{a.rule_name}</Tag>
            ))}
            {matched.length > 3 && <Tag style={{ backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', border: 'none' }} className="!m-0">+{matched.length - 3}</Tag>}
          </div>
        );
      },
    },
    {
      title: '优先级',
      dataIndex: 'score',
      key: 'score',
      width: 100,
      render: (score: number) => (
        <span className={`font-bold ${score >= 7 ? 'text-emerald-400' : score >= 5 ? 'text-amber-400' : 'text-rose-400'}`}>
          {score.toFixed(1)}
        </span>
      ),
    },
    {
      title: '步骤 / ROI',
      key: 'step_roi',
      width: 120,
      render: (_, record) => (
        <span className="text-secondary text-sm">
          <ClockCircleOutlined className="mr-1" />
          {record.step_count} 步 · ROI {record.expected_roi.toFixed(1)}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => {
        if (status === 'adopted') return <Tag style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: 'none' }}>已采纳</Tag>;
        if (status === 'rejected') return <Tag style={{ backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'none' }}>已拒绝</Tag>;
        return <Tag style={{ backgroundColor: 'rgba(107, 114, 128, 0.2)', color: '#6b7280', border: 'none' }}>待评估</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => {
        const isAdopted = record.status === 'adopted';
        const isRejected = record.status === 'rejected';
        const adoptDisabled = isRejected || isAdopted || anySolutionAdopted;
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
              disabled={adoptDisabled}
              title={anySolutionAdopted && !isAdopted ? '已有方案被采纳' : undefined}
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
    <div className="space-y-6 bg-[#F0F1F9] min-h-screen">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          {/* <h1 className="text-2xl font-bold text-[#303133] flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-lg shadow-lg shadow-amber-500/20 text-white">
              <BulbOutlined />
            </span>
            优化方案
          </h1> */}
          <p className="text-[#303133] mt-2 text-sm">
            诊断完成后自动生成的优化方案，按综合评分排序
          </p>
        </div>
        {enterpriseId && diagnosisItems.length > 0 && (
          <DiagnosisHistorySelect
            className="shrink-0 w-full sm:w-[min(100%,320px)]"
            diagnosisItems={diagnosisItems}
            value={selectedDiagnosisId}
            onChange={setSelectedDiagnosisId}
            loading={listLoading}
          />
        )}
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
        ) : !selectedDiagnosisId ? (
          <Empty description="请先完成诊断后查看方案" />
        ) : !isCompleted ? (
          <Empty description="该次诊断尚未完成，暂无方案" />
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
