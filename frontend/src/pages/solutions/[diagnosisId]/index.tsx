

import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Card, Row, Col, Tag, Button, Empty, Spin, 
  Timeline, App, Statistic, Divider, Alert 
} from 'antd';
import { 
  ArrowLeftOutlined,
  BulbOutlined, 
  CheckCircleOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  StarOutlined,
  SwapOutlined,
  SafetyCertificateOutlined,
  AimOutlined,
} from '@ant-design/icons';
import { 
  useSolutionList, 
  useSolutionDetail,
  useAdoptSolution,
  useRejectSolution,
  useCreateExecutionPlan,
  useDiagnosisReport,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { useQuery } from '@tanstack/react-query';
import { enterpriseApi } from '@/lib/api';
import dayjs from 'dayjs';
import clsx from 'clsx';
import type { SolutionSummary, SolutionGenerateResponse, DiagnosisReport, SolutionDetail, AIRecommendation } from '@/lib/types';

// 排序策略名称映射
const getStrategyName = (strategy: string): string => {
  const strategyMap: Record<string, string> = {
    'balanced': '综合评分',
    'roi_first': '投资回报率优先',
    'quick_win': '快速见效优先',
    'risk_averse': '风险规避',
  };
  return strategyMap[strategy] || strategy;
};

export default function SolutionDetailPage() {
  const { message } = App.useApp();
  const params = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const diagnosisId = params.diagnosisId as string;
  
  // 从 URL 参数读取方案ID和异常ID
  const solutionIdFromUrl = searchParams.get('solution_id');
  const anomalyIdFromUrl = searchParams.get('anomaly_id');
  
  const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(solutionIdFromUrl);
  
  // 获取企业配置
  const { currentEnterprise } = useAppStore();
  const enterpriseId = currentEnterprise?.id || null;
  const { data: enterpriseDetail } = useQuery({
    queryKey: ['enterprise', enterpriseId],
    queryFn: () => enterpriseApi.get(enterpriseId!),
    enabled: !!enterpriseId,
  });
  const rankingStrategy = (enterpriseDetail as { config?: { solution_sort_strategy?: string } } | undefined)?.config?.solution_sort_strategy || 'balanced';
  
  // 获取方案列表
  const { data: solutionData, isLoading: solutionsLoading, isFetching: solutionsFetching, refetch } = useSolutionList(diagnosisId);
  const typedSolutionData = solutionData as SolutionGenerateResponse | undefined;
  
  // 获取诊断报告
  const { data: diagnosisReport } = useDiagnosisReport(diagnosisId);
  const typedDiagnosisReport = diagnosisReport as DiagnosisReport | undefined;
  
  // 采纳方案
  const adoptSolution = useAdoptSolution();
  
  // 拒绝方案
  const rejectSolution = useRejectSolution();
  
  // 创建执行计划
  const createPlan = useCreateExecutionPlan();
  
  const solutions = typedSolutionData?.solutions || [];
  
  // 获取选中方案的详情
  const { data: solutionDetail, isLoading: detailLoading, refetch: refetchDetail } = useSolutionDetail(selectedSolutionId);
  const typedDetail = solutionDetail as SolutionDetail | undefined;
  
  // 自动选择方案：优先使用 URL 参数，其次根据 anomaly_id 匹配，否则选择第一个
  useEffect(() => {
    if (solutions.length > 0 && !selectedSolutionId) {
      // 如果 URL 中有方案ID，验证是否存在
      if (solutionIdFromUrl) {
        const exists = solutions.some(s => s.solution_id === solutionIdFromUrl);
        if (exists) {
          setSelectedSolutionId(solutionIdFromUrl);
          return;
        }
      }
      
      // 如果 URL 中有异常ID，查找匹配的方案
      if (anomalyIdFromUrl) {
        const matchingSolution = solutions.find(s => 
          s.anomaly_ids && s.anomaly_ids.includes(anomalyIdFromUrl)
        );
        if (matchingSolution) {
          setSelectedSolutionId(matchingSolution.solution_id);
          return;
        }
      }
      
      // 否则选择第一个
      setSelectedSolutionId(solutions[0].solution_id);
    }
  }, [solutions, selectedSolutionId, solutionIdFromUrl, anomalyIdFromUrl]);

  // 使用后端返回的 AI 智能建议（红框文案）
  const aiRecommendation: AIRecommendation | null = typedSolutionData?.ai_recommendation ?? null;

  // 获取当前选中的方案
  const selectedSolution = solutions.find(s => s.solution_id === selectedSolutionId);

  // 处理采纳方案
  const handleAdopt = async (solutionId: string) => {
    try {
      await adoptSolution.mutateAsync(solutionId);
      message.success('方案已采纳');
      // 刷新方案列表以获取最新状态
      await refetch();
    } catch {
      message.error('采纳失败');
    }
  };

  // 处理拒绝方案
  const handleReject = async (solutionId: string) => {
    try {
      await rejectSolution.mutateAsync({ solutionId });
      message.success('方案已拒绝');
      refetch();
    } catch {
      message.error('拒绝失败');
    }
  };

  // 处理创建执行计划
  const handleCreatePlan = async (solutionId: string) => {
    // 防止重复点击
    if (createPlan.isPending) {
      return;
    }
    
    if (!typedDiagnosisReport?.enterprise_id) {
      message.error('缺少企业ID');
      return;
    }
    
    try {
      const result = await createPlan.mutateAsync({
        enterprise_id: typedDiagnosisReport.enterprise_id,
        solution_id: solutionId,
        start_date: dayjs().format('YYYY-MM-DD'),
      });
      
      // 检查返回状态
      if (result.status === 'failed') {
        message.error(result.message || '创建执行计划失败');
        return;
      }
      
      // 刷新方案列表和详情，更新执行计划信息
      await Promise.all([refetch(), refetchDetail()]);
      
      // 立即跳转到执行计划详情页
      if ((result as { plan_id?: string } | undefined)?.plan_id) {
        navigate(`/execution/${(result as { plan_id: string }).plan_id}`);
      } else {
        // 如果没有返回 plan_id，跳转到执行计划列表页
        message.warning('执行计划已创建，但未获取到计划ID');
        navigate('/execution');
      }
    } catch (error) {
      console.error('创建执行计划失败:', error);
      message.error('创建执行计划失败');
    }
  };

  // 获取评分颜色
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-rose-400';
  };

  if (solutionsLoading || (solutionsFetching && solutions.length === 0)) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin size="large" />
      </div>
    );
  }

  if (solutions.length === 0) {
    return (
      <div className="space-y-6">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          返回
        </Button>
        <div className="flex items-center justify-center h-[50vh]">
          <Empty 
            description="暂无优化方案" 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button type="primary" onClick={() => navigate('/solutions')}>
              返回方案列表
            </Button>
          </Empty>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-lg shadow-lg shadow-amber-500/20">
                <BulbOutlined />
              </span>
              优化方案详情
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              共 {solutions.length} 个方案 · 诊断ID: {diagnosisId.slice(0, 8)}...
            </p>
          </div>
        </div>
      </div>

      {/* AI 智能建议 */}
      {aiRecommendation && (
        <Card 
          className="!bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10 !border-cyan-500/30"
        >
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
                <Alert
                  type="warning"
                  showIcon
                  icon={<WarningOutlined />}
                  message={aiRecommendation.risk_warning}
                  className="!bg-amber-500/10 !border-amber-500/30"
                />
              )}
              <div className="mt-4 flex gap-3">
                {(() => {
                  const recommendedSolution = solutions.find(s => s.solution_id === aiRecommendation.recommended_solution_id);
                  const isAdopted = recommendedSolution?.status === 'adopted';
                  const isRejected = recommendedSolution?.status === 'rejected';
                  
                  return (
                    <>
                      <Button 
                        type="primary" 
                        icon={<CheckCircleOutlined />}
                        onClick={() => handleAdopt(aiRecommendation.recommended_solution_id)}
                        loading={adoptSolution.isPending}
                        disabled={isAdopted || isRejected}
                      >
                        {isAdopted ? '已采纳' : '采纳推荐方案'}
                      </Button>
                      {recommendedSolution?.execution_plan ? (
                        <Button 
                          icon={<RocketOutlined />}
                          onClick={() => navigate(`/execution/${recommendedSolution.execution_plan!.plan_id}`)}
                        >
                          查看执行
                        </Button>
                      ) : (
                        <Button 
                          icon={<RocketOutlined />}
                          onClick={() => handleCreatePlan(aiRecommendation.recommended_solution_id)}
                          loading={createPlan.isPending}
                          disabled={isRejected || createPlan.isPending}
                        >
                          直接执行
                        </Button>
                      )}
                    </>
                  );
                })()}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 方案对比概览 */}
      {solutions.length > 1 && (
        <Card title={
          <div className="flex items-center gap-2">
            <SwapOutlined className="text-purple-400" />
            <span>方案对比</span>
            <Tag color="purple">{solutions.length}个方案</Tag>
            <Tag color="blue" className="ml-2">排序策略: {getStrategyName(rankingStrategy)}</Tag>
          </div>
        }>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">方案</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">评分</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">成本</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">周期</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">成功率</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {solutions.map((solution, index) => {
                  const isRecommended = solution.solution_id === aiRecommendation?.recommended_solution_id;
                  const isBestScore = solution.score === Math.max(...solutions.map(s => s.score));
                  const isCheapest = solution.estimated_cost === Math.min(...solutions.map(s => s.estimated_cost));
                  const isQuickest = solution.estimated_duration === Math.min(...solutions.map(s => s.estimated_duration));
                  const isSafest = solution.success_rate === Math.max(...solutions.map(s => s.success_rate));
                  
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
                            index === 0 ? 'bg-amber-500/20 text-amber-400' :
                            index === 1 ? 'bg-gray-400/20 text-gray-300' :
                            'bg-gray-700/50 text-gray-400'
                          )}>
                            {index === 0 ? <TrophyOutlined /> : index + 1}
                          </div>
                          <div>
                            <div className="font-medium text-white flex items-center gap-2">
                              {solution.name}
                              {isRecommended && <Tag color="cyan" className="!m-0">推荐</Tag>}
                              {solution.status === 'adopted' && (
                                <Tag color="green" className="!m-0">已采纳</Tag>
                              )}
                              {solution.status === 'rejected' && (
                                <Tag color="red" className="!m-0">已拒绝</Tag>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={clsx('font-bold text-lg', getScoreColor(solution.score))}>
                          {solution.score.toFixed(1)}
                        </span>
                        {isBestScore && <span className="text-emerald-400 ml-1">✓</span>}
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={clsx('text-gray-300', isCheapest && 'text-emerald-400 font-medium')}>
                          ¥{solution.estimated_cost >= 10000 
                            ? `${(solution.estimated_cost / 10000).toFixed(1)}万` 
                            : solution.estimated_cost.toLocaleString()}
                        </span>
                        {isCheapest && <span className="text-emerald-400 ml-1">✓</span>}
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={clsx('text-gray-300', isQuickest && 'text-emerald-400 font-medium')}>
                          {solution.estimated_duration}天
                        </span>
                        {isQuickest && <span className="text-emerald-400 ml-1">✓</span>}
                      </td>
                      <td className="py-4 px-4 text-center">
                        <Tag color={solution.success_rate >= 0.8 ? 'green' : solution.success_rate >= 0.6 ? 'gold' : 'red'}>
                          {(solution.success_rate * 100).toFixed(0)}%
                        </Tag>
                        {isSafest && <span className="text-emerald-400 ml-1">✓</span>}
                      </td>
                      <td className="py-4 px-4 text-center">
                        <div className="flex justify-center gap-1">
                          <Button 
                            type="link" 
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleAdopt(solution.solution_id);
                            }}
                            disabled={solution.status === 'adopted' || solution.status === 'rejected'}
                            loading={adoptSolution.isPending}
                          >
                            {solution.status === 'adopted' ? '已采纳' : '采纳'}
                          </Button>
                          <Button 
                            type="link" 
                            size="small"
                            danger
                            icon={<CloseCircleOutlined />}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleReject(solution.solution_id);
                            }}
                            disabled={solution.status === 'adopted' || solution.status === 'rejected'}
                            loading={rejectSolution.isPending}
                          >
                            {solution.status === 'rejected' ? '已拒绝' : '拒绝'}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-4 text-xs text-gray-500 flex items-center gap-4">
            <span><span className="text-emerald-400">✓</span> 表示该维度最优</span>
          </div>
        </Card>
      )}

      {/* 方案详情 */}
      {selectedSolution && (
        <Row gutter={16}>
          <Col span={16}>
            <Card 
              title={
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BulbOutlined className="text-amber-400" />
                    <span>{selectedSolution.name}</span>
                    {selectedSolution.solution_id === aiRecommendation?.recommended_solution_id && (
                      <Tag color="cyan">AI 推荐</Tag>
                    )}
                    {selectedSolution.status === 'adopted' && (
                      <Tag color="green">已采纳</Tag>
                    )}
                    {selectedSolution.status === 'rejected' && (
                      <Tag color="red">已拒绝</Tag>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleAdopt(selectedSolution.solution_id)}
                      loading={adoptSolution.isPending}
                      disabled={selectedSolution.status === 'adopted' || selectedSolution.status === 'rejected'}
                    >
                      {selectedSolution.status === 'adopted' ? '已采纳' : '采纳方案'}
                    </Button>
                    {typedDetail?.execution_plan ? (
                      <Button 
                        icon={<RocketOutlined />}
                        onClick={() => navigate(`/execution/${typedDetail.execution_plan!.plan_id}`)}
                      >
                        查看执行
                      </Button>
                    ) : (
                      <Button 
                        icon={<RocketOutlined />}
                        onClick={() => handleCreatePlan(selectedSolution.solution_id)}
                        loading={createPlan.isPending}
                        disabled={selectedSolution.status === 'rejected' || createPlan.isPending}
                      >
                        执行
                      </Button>
                    )}
                  </div>
                </div>
              }
            >
              <div className="space-y-6">
                {/* 核心指标 */}
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic 
                      title="推荐评分" 
                      value={selectedSolution.score}
                      suffix="分"
                      valueStyle={{ color: selectedSolution.score >= 70 ? '#10b981' : '#f59e0b' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="预估成本" 
                      value={selectedSolution.estimated_cost}
                      prefix="¥"
                      formatter={(value) => 
                        Number(value) >= 10000 
                          ? `${(Number(value) / 10000).toFixed(1)}万` 
                          : Number(value).toLocaleString()
                      }
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="实施周期" 
                      value={selectedSolution.estimated_duration}
                      suffix="天"
                    />
                  </Col>
                  <Col span={6}>
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

                {/* 排序策略提示 */}
                <Alert
                  message={
                    <div className="flex items-center gap-2">
                      <SwapOutlined />
                      <span>当前排序策略：<strong>{getStrategyName(rankingStrategy)}</strong></span>
                    </div>
                  }
                  description="方案排序基于系统设置中的排序策略。可在系统设置中修改排序策略。"
                  type="info"
                  showIcon
                  closable
                  className="mb-4"
                />

                <Divider />

                {/* 方案说明 */}
                {detailLoading ? (
                  <div className="flex justify-center py-8"><Spin /></div>
                ) : typedDetail ? (
                  <div className="space-y-4">
                    {/* 执行摘要 */}
                    <div>
                      <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                        <AimOutlined className="text-blue-400" />
                        执行摘要
                      </h4>
                      <div className="bg-gray-800/30 rounded-lg p-4 text-gray-300 leading-relaxed">
                        {typedDetail.executive_summary}
                      </div>
                    </div>

                    {/* 问题分析 */}
                    <div>
                      <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                        <WarningOutlined className="text-rose-400" />
                        问题分析
                      </h4>
                      <div className="bg-rose-500/5 border border-rose-500/20 rounded-lg p-4 text-gray-300 leading-relaxed">
                        {typedDetail.problem_statement}
                      </div>
                    </div>

                    {/* 方案概述 */}
                    <div>
                      <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                        <BulbOutlined className="text-amber-400" />
                        方案概述
                      </h4>
                      <div className="bg-gray-800/30 rounded-lg p-4 text-gray-300 leading-relaxed">
                        {typedDetail.solution_overview}
                      </div>
                    </div>

                    {/* 实施路线图 */}
                    {typedDetail.implementation_roadmap && (
                      <div>
                        <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                          <RocketOutlined className="text-cyan-400" />
                          实施路线图
                        </h4>
                        <div className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-4 text-gray-300 leading-relaxed whitespace-pre-line">
                          {typedDetail.implementation_roadmap}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                      <AimOutlined className="text-blue-400" />
                      方案概述
                    </h4>
                    <div className="bg-gray-800/30 rounded-lg p-4 text-gray-300 leading-relaxed">
                      该方案针对诊断发现的异常问题，预计可在 {selectedSolution.estimated_duration} 天内见效。
                    </div>
                  </div>
                )}

                {/* 预期效果 */}
                <div>
                  <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                    <ThunderboltOutlined className="text-amber-400" />
                    预期效果
                  </h4>
                  {typedDetail?.expected_outcomes && (
                    <div className="bg-gray-800/30 rounded-lg p-4 text-gray-300 leading-relaxed whitespace-pre-line mb-3">
                      {typedDetail.expected_outcomes}
                    </div>
                  )}
                  {typedDetail?.estimated_impact && Object.keys(typedDetail.estimated_impact).length > 0 ? (
                    <div className="grid grid-cols-2 gap-3">
                      {Object.entries(typedDetail.estimated_impact).map(([metric, value]) => {
                        const isPositive = value > 0;
                        return (
                          <div
                            key={metric}
                            className={clsx(
                              'rounded-lg p-3 border',
                              isPositive
                                ? 'bg-emerald-500/10 border-emerald-500/20'
                                : 'bg-blue-500/10 border-blue-500/20'
                            )}
                          >
                            <div className={clsx('font-medium', isPositive ? 'text-emerald-400' : 'text-blue-400')}>
                              {metric.replace(/_/g, ' ')}
                            </div>
                            <div className="text-2xl font-bold text-white mt-1">
                              {isPositive ? '+' : ''}{value.toFixed(1)}%
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-gray-500 text-sm">暂无预期效果数据</div>
                  )}
                </div>
              </div>
            </Card>
          </Col>

          <Col span={8}>
            {/* 执行步骤 */}
            <Card 
              title={
                <div className="flex items-center gap-2">
                  <ClockCircleOutlined className="text-cyan-400" />
                  <span>执行步骤</span>
                </div>
              }
              className="h-full"
            >
              {detailLoading ? (
                <div className="flex justify-center py-8"><Spin /></div>
              ) : typedDetail?.tasks && typedDetail.tasks.length > 0 ? (
                <Timeline
                  items={typedDetail.tasks.map((task, index) => {
                    const execTypeMap: Record<string, { label: string; color: string }> = {
                      auto: { label: '自动执行', color: 'green' },
                      semi_auto: { label: '半自动', color: 'blue' },
                      manual: { label: '人工执行', color: 'orange' },
                      custom_api: { label: 'API 调用', color: 'cyan' },
                      custom_script: { label: '脚本执行', color: 'purple' },
                    };
                    const execInfo = execTypeMap[task.execution_type] || { label: task.execution_type, color: 'blue' };
                    const isLast = index === typedDetail.tasks.length - 1;

                    return {
                      color: isLast ? 'gray' : execInfo.color,
                      children: (
                        <div>
                          <div className={clsx('font-medium', isLast ? 'text-gray-400' : 'text-white')}>
                            {task.name}
                          </div>
                          <div className="text-gray-500 text-xs mt-1">
                            第{task.start_offset + 1}-{task.end_offset}天 · {task.duration_days}天 · {execInfo.label}
                          </div>
                          {task.description && (
                            <div className="text-gray-500 text-xs mt-1">{task.description}</div>
                          )}
                        </div>
                      ),
                    };
                  })}
                />
              ) : (
                <Timeline
                  items={[
                    { color: 'gray', children: <div className="text-gray-500">暂无执行步骤数据</div> },
                  ]}
                />
              )}

              <Divider />

              {/* 风险评估 */}
              <div>
                <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                  <SafetyCertificateOutlined className="text-amber-400" />
                  风险评估
                </h4>
                {typedDetail?.risk_assessment ? (
                  <div className="text-sm text-gray-400 whitespace-pre-line leading-relaxed">
                    {typedDetail.risk_assessment}
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">暂无风险评估数据</div>
                )}
              </div>

              {/* 成功标准 */}
              {typedDetail?.success_criteria && (
                <>
                  <Divider />
                  <div>
                    <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
                      <CheckCircleOutlined className="text-emerald-400" />
                      成功标准
                    </h4>
                    <div className="text-sm text-gray-400 whitespace-pre-line leading-relaxed">
                      {typedDetail.success_criteria}
                    </div>
                  </div>
                </>
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}

