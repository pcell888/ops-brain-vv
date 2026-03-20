import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card, Row, Col, Tag, Button, Empty, Spin,
  Timeline, App, Statistic, Divider, Alert
} from 'antd';
import {
  ArrowLeftOutlined, BulbOutlined, CheckCircleOutlined, ThunderboltOutlined,
  TrophyOutlined, ClockCircleOutlined, RocketOutlined, CloseCircleOutlined,
  WarningOutlined, StarOutlined, SwapOutlined, AimOutlined,
} from '@ant-design/icons';
import {
  useSolutionList, useAdoptSolution, useDiagnosisReport,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import clsx from 'clsx';
import type { SolutionSummary, SolutionGenerateResponse, DiagnosisReport, AIRecommendation } from '@/lib/types';

export default function SolutionDetailPage() {
  const { message } = App.useApp();
  const params = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const diagnosisId = params.diagnosisId as string;

  const solutionIdFromUrl = searchParams.get('solution_id');
  const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(solutionIdFromUrl);

  const { currentEnterprise } = useAppStore();
  const { data: solutionData, isLoading: solutionsLoading, refetch } = useSolutionList(diagnosisId);
  const typedSolutionData = solutionData as SolutionGenerateResponse | undefined;
  const { data: diagnosisReport } = useDiagnosisReport(diagnosisId);
  const adoptSolution = useAdoptSolution();

  const solutions = typedSolutionData?.solutions || [];
  const aiRecommendation: AIRecommendation | null = typedSolutionData?.ai_recommendation ?? null;

  useEffect(() => {
    if (solutions.length > 0 && !selectedSolutionId) {
      if (solutionIdFromUrl) {
        const exists = solutions.some(s => s.solution_id === solutionIdFromUrl);
        if (exists) { setSelectedSolutionId(solutionIdFromUrl); return; }
      }
      setSelectedSolutionId(solutions[0].solution_id);
    }
  }, [solutions, selectedSolutionId, solutionIdFromUrl]);

  const selectedSolution = solutions.find(s => s.solution_id === selectedSolutionId);

  const handleAdopt = async (solutionId: string) => {
    try {
      await adoptSolution.mutateAsync(solutionId);
      message.success('方案已采纳');
      await refetch();
    } catch {
      message.error('采纳失败');
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-rose-400';
  };

  if (solutionsLoading) {
    return <div className="flex items-center justify-center h-[60vh]"><Spin size="large" /></div>;
  }

  if (solutions.length === 0) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty description="暂无优化方案">
            <Button type="primary" onClick={() => navigate('/solutions')}>返回方案列表</Button>
          </Empty>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-lg shadow-lg shadow-amber-500/20">
              <BulbOutlined />
            </span>
            方案详情
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            共 {solutions.length} 个方案 · 诊断ID: {diagnosisId.slice(0, 8)}...
          </p>
        </div>
      </div>

      {aiRecommendation && (
        <Card className="!bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10 !border-cyan-500/30">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xl shadow-lg">
              <StarOutlined />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg font-bold text-white">AI 智能建议</span>
                <Tag color="cyan">自动分析</Tag>
              </div>
              <p className="text-gray-300 mb-3">{aiRecommendation.reason}</p>
              <p className="text-gray-400 text-sm mb-3">{aiRecommendation.comparison_summary}</p>
              {aiRecommendation.risk_warning && (
                <Alert type="warning" showIcon icon={<WarningOutlined />} message={aiRecommendation.risk_warning} className="!bg-amber-500/10 !border-amber-500/30" />
              )}
              <div className="mt-4 flex gap-3">
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleAdopt(aiRecommendation.recommended_solution_id)}
                  loading={adoptSolution.isPending}
                  disabled={solutions.find(s => s.solution_id === aiRecommendation.recommended_solution_id)?.status === 'adopted'}
                >
                  {solutions.find(s => s.solution_id === aiRecommendation.recommended_solution_id)?.status === 'adopted' ? '已采纳' : '采纳推荐方案'}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {solutions.length > 1 && (
        <Card title={
          <div className="flex items-center gap-2">
            <SwapOutlined className="text-purple-400" />
            <span>方案对比</span>
            <Tag color="purple">{solutions.length}个方案</Tag>
          </div>
        }>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">方案</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">评分</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">周期</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">成功率</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {solutions.map((solution, index) => {
                  const isRecommended = solution.solution_id === aiRecommendation?.recommended_solution_id;
                  return (
                    <tr
                      key={solution.solution_id}
                      className={clsx(
                        'border-b border-gray-800 transition-colors cursor-pointer',
                        isRecommended ? 'bg-cyan-500/10' : 'hover:bg-gray-800/50',
                        selectedSolutionId === solution.solution_id && 'bg-blue-500/10'
                      )}
                      onClick={() => setSelectedSolutionId(solution.solution_id)}
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                          <div className={clsx(
                            'w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm',
                            index === 0 ? 'bg-amber-500/20 text-amber-400' : 'bg-gray-700/50 text-gray-400'
                          )}>
                            {index === 0 ? <TrophyOutlined /> : index + 1}
                          </div>
                          <div>
                            <div className="font-medium text-white flex items-center gap-2">
                              {solution.name}
                              {isRecommended && <Tag color="cyan" className="!m-0">推荐</Tag>}
                              {solution.status === 'adopted' && <Tag color="green" className="!m-0">已采纳</Tag>}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={clsx('font-bold text-lg', getScoreColor(solution.score))}>
                          {solution.score.toFixed(1)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center text-gray-300">{solution.estimated_duration}天</td>
                      <td className="py-4 px-4 text-center">
                        <Tag color={solution.success_rate >= 0.8 ? 'green' : solution.success_rate >= 0.6 ? 'gold' : 'red'}>
                          {(solution.success_rate * 100).toFixed(0)}%
                        </Tag>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <Button
                          type="link"
                          size="small"
                          icon={<CheckCircleOutlined />}
                          onClick={(e) => { e.stopPropagation(); handleAdopt(solution.solution_id); }}
                          disabled={solution.status === 'adopted'}
                          loading={adoptSolution.isPending}
                        >
                          {solution.status === 'adopted' ? '已采纳' : '采纳'}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {selectedSolution && (
        <Row gutter={16}>
          <Col span={16}>
            <Card
              title={
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BulbOutlined className="text-amber-400" />
                    <span>{selectedSolution.name}</span>
                    {selectedSolution.status === 'adopted' && <Tag color="green">已采纳</Tag>}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleAdopt(selectedSolution.solution_id)}
                      loading={adoptSolution.isPending}
                      disabled={selectedSolution.status === 'adopted'}
                    >
                      {selectedSolution.status === 'adopted' ? '已采纳' : '采纳方案'}
                    </Button>
                  </div>
                </div>
              }
            >
              <div className="space-y-6">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="推荐评分"
                      value={selectedSolution.score}
                      suffix="分"
                      valueStyle={{ color: selectedSolution.score >= 70 ? '#10b981' : '#f59e0b' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic title="实施周期" value={selectedSolution.estimated_duration} suffix="天" />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="预估成功率"
                      value={(selectedSolution.success_rate * 100).toFixed(0)}
                      suffix="%"
                      valueStyle={{
                        color: selectedSolution.success_rate >= 0.8 ? '#10b981' :
                               selectedSolution.success_rate >= 0.6 ? '#f59e0b' : '#ef4444'
                      }}
                    />
                  </Col>
                </Row>

                <Divider />

                {selectedSolution.recommendation_reason && (
                  <div>
                    <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                      <AimOutlined className="text-blue-400" />方案概述
                    </h4>
                    <div className="bg-gray-800/30 rounded-lg p-4 text-gray-300 leading-relaxed">
                      {selectedSolution.recommendation_reason}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </Col>

          <Col span={8}>
            <Card
              title={
                <div className="flex items-center gap-2">
                  <ThunderboltOutlined className="text-amber-400" />
                  <span>针对异常</span>
                </div>
              }
              className="h-full"
            >
              {selectedSolution.anomaly_ids && selectedSolution.anomaly_ids.length > 0 ? (
                <div className="space-y-3">
                  {selectedSolution.anomaly_ids.map((aid) => {
                    const anomaly = (diagnosisReport as DiagnosisReport | undefined)?.anomalies?.find(
                      (a) => a.id === aid || a.metric_name === aid
                    );
                    if (!anomaly) return (
                      <div key={aid} className="bg-gray-800/30 rounded-lg p-3 text-gray-500 text-sm">{aid}</div>
                    );
                    return (
                      <div key={aid} className="bg-gradient-to-r from-rose-500/10 to-transparent rounded-lg p-3 border border-rose-500/20">
                        <div className="flex justify-between items-start mb-1">
                          <span className="text-white font-medium text-sm">{anomaly.rule_name}</span>
                          <Tag color={anomaly.severity === 'critical' ? 'red' : anomaly.severity === 'high' ? 'orange' : 'gold'} className="!m-0">
                            {anomaly.severity === 'critical' ? '严重' : anomaly.severity === 'high' ? '高' : '中'}
                          </Tag>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-400">
                          <span>当前: <span className="text-rose-400 font-medium">{anomaly.current_value?.toFixed(1)}{anomaly.unit || '%'}</span></span>
                          {anomaly.benchmark_value && (
                            <span>基准: <span className="text-emerald-400">{anomaly.benchmark_value?.toFixed(1)}{anomaly.unit || '%'}</span></span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <Empty description="无关联异常" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}
