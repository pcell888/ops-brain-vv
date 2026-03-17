

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Button, Empty, Spin, Modal, Descriptions, Progress, Row, Col, App, Checkbox, Input, Tooltip, Alert } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { 
  BulbOutlined, 
  CheckCircleOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  RocketOutlined,
  SwapOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  TagsOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { 
  useLatestDiagnosisReport, 
  useSolutionList, 
  useSolutionDetail,
  useGenerateSolutions,
  useGenerationTask,
  useAdoptSolution,
  useRejectSolution,
  useCompareSolutions,
  useCreateExecutionPlan,
  type SolutionComparisonResponse,
} from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import dayjs from 'dayjs';
import type { SolutionSummary, Anomaly } from '@/lib/types';
import { SolutionFlowChart, type AnomalyFlowItem, type SolutionFlowItem } from '@/components/diagnosis/solution-flow-chart';
import { getTagLabel } from '@/lib/tag-labels';


// 标签到模板的映射
const templateTagMapping: Record<string, string[]> = {
  'tpl_lead_conversion_optimization': ['lead_conversion', 'crm_optimization', 'sales_process'],
  'tpl_marketing_roi_optimization': ['marketing_roi', 'audience_targeting'],
  'tpl_churn_prevention': ['churn_prevention', 'customer_retention'],
  'tpl_task_efficiency': ['task_management', 'workload_optimization'],
};

// 根据方案类别获取适用标签
const getCategoryTags = (category: string): string[] => {
  const categoryTagMap: Record<string, string[]> = {
    'sales_process': ['lead_conversion', 'crm_optimization', 'sales_process'],
    'marketing_optimization': ['marketing_roi', 'audience_targeting'],
    'customer_retention': ['churn_prevention', 'customer_retention'],
    'efficiency_improvement': ['task_management', 'workload_optimization'],
  };
  return categoryTagMap[category] || [];
};

// 根据方案名称推断类别
const inferCategoryFromName = (name: string): string => {
  if (name.includes('线索') || name.includes('转化')) return 'sales_process';
  if (name.includes('营销') || name.includes('ROI')) return 'marketing_optimization';
  if (name.includes('流失') || name.includes('留存')) return 'customer_retention';
  if (name.includes('效率') || name.includes('任务')) return 'efficiency_improvement';
  return 'sales_process';
};

// 检查方案是否匹配异常标签
const isSolutionMatchingAnomalyTags = (solutionName: string, anomalyTags: string[]): boolean => {
  const category = inferCategoryFromName(solutionName);
  const solutionTags = getCategoryTags(category);
  return anomalyTags.some(tag => solutionTags.includes(tag));
};

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
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const enterpriseId = currentEnterprise?.id || null;
  const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectingSolutionId, setRejectingSolutionId] = useState<string | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<SolutionComparisonResponse | null>(null);
  
  
  // 从 URL 读取 anomaly_id
  const highlightAnomalyId = searchParams.get('anomaly_id');
  
  // 获取最新诊断
  const { latestDiagnosisId, data: diagnosisReport, isLoading: diagnosisLoading } = useLatestDiagnosisReport(enterpriseId);
  
  // 获取方案列表
  const { data: solutionData, isLoading: solutionsLoading, refetch } = useSolutionList(latestDiagnosisId || null);
  
  // 从诊断报告中获取指标单位
  const getMetricUnit = (metricName: string, dimension?: string) => {
    const ds = diagnosisReport?.health_score?.dimension_scores?.find(
      (d: { dimension: string }) => d.dimension === dimension
    );
    const md = ds?.metrics_detail?.find((m: { name: string }) => m.name === metricName);
    return md?.unit || '%';
  };

  // 是否显示流程图
  const [showFlowChart, setShowFlowChart] = useState(false);
  
  // 获取方案详情
  const { data: solutionDetail, isLoading: detailLoading } = useSolutionDetail(selectedSolutionId);
  
  // 生成方案
  const generateSolutions = useGenerateSolutions();
  // 检测活跃的后台生成任务（页面刷新/重入时恢复状态）
  const { isGenerating: isBackgroundGenerating } = useGenerationTask(latestDiagnosisId || null);
  const isGenerating = generateSolutions.isPending || isBackgroundGenerating;
  
  // 采纳方案
  const adoptSolution = useAdoptSolution();
  
  // 拒绝方案
  const rejectSolution = useRejectSolution();
  
  // 对比方案
  const compareSolutions = useCompareSolutions();
  
  // 创建执行计划
  const createPlan = useCreateExecutionPlan();

  const isLoading = diagnosisLoading || solutionsLoading || isGenerating;
  
  // 获取高亮异常的信息
  const highlightAnomaly = highlightAnomalyId ? diagnosisReport?.anomalies?.find(
    (a: Anomaly) => a.id === highlightAnomalyId
  ) : undefined;
  
  // 获取关联的方案 ID 列表（根据标签匹配）
  const relatedSolutionIds = new Set(
    highlightAnomaly?.solution_tags && solutionData?.solutions
      ? solutionData.solutions
          .filter((s: { name: string; solution_id: string }) => isSolutionMatchingAnomalyTags(s.name, highlightAnomaly.solution_tags || []))
          .map((s: { name: string; solution_id: string }) => s.solution_id)
      : []
  );

  // 处理生成方案
  const handleGenerateSolutions = async () => {
    if (!enterpriseId || !latestDiagnosisId) {
      message.warning('请先完成诊断');
      return;
    }
    
    try {
      await generateSolutions.mutateAsync({
        enterprise_id: enterpriseId,
        diagnosis_id: latestDiagnosisId,
        ranking_strategy: 'balanced',
      });
      message.success('方案生成成功，正在跳转到详情页...');
      setTimeout(() => {
        navigate(`/solutions/${latestDiagnosisId}`);
      }, 500);
    } catch {
      message.error('方案生成失败');
    }
  };

  // 处理采纳方案
  const handleAdopt = async (solutionId: string) => {
    try {
      await adoptSolution.mutateAsync(solutionId);
      message.success('方案已采纳');
      refetch();
    } catch {
      message.error('采纳失败');
    }
  };

  // 处理拒绝方案
  const handleReject = async () => {
    if (!rejectingSolutionId) return;
    try {
      await rejectSolution.mutateAsync({ 
        solutionId: rejectingSolutionId, 
        reason: rejectReason || undefined 
      });
      message.success('方案已拒绝');
      setRejectModalOpen(false);
      setRejectReason('');
      setRejectingSolutionId(null);
      refetch();
    } catch {
      message.error('拒绝失败');
    }
  };

  // 打开拒绝弹窗
  const openRejectModal = (solutionId: string) => {
    setRejectingSolutionId(solutionId);
    setRejectModalOpen(true);
  };

  // 处理对比方案
  const handleCompare = async () => {
    if (selectedForCompare.length < 2) {
      message.warning('请至少选择2个方案进行对比');
      return;
    }
    
    try {
      const result = await compareSolutions.mutateAsync(selectedForCompare);
      setComparisonData(result);
      setCompareModalOpen(true);
    } catch {
      message.error('对比失败');
    }
  };

  // 切换选择对比
  const toggleCompareSelection = (solutionId: string) => {
    setSelectedForCompare(prev => {
      if (prev.includes(solutionId)) {
        return prev.filter(id => id !== solutionId);
      }
      if (prev.length >= 4) {
        message.warning('最多选择4个方案进行对比');
        return prev;
      }
      return [...prev, solutionId];
    });
  };

  // 处理创建执行计划
  const handleCreatePlan = async (solutionId: string) => {
    // 防止重复点击
    if (createPlan.isPending) {
      return;
    }
    
    if (!enterpriseId) {
      message.error('缺少企业ID');
      return;
    }
    
    try {
      const result = await createPlan.mutateAsync({
        enterprise_id: enterpriseId,
        solution_id: solutionId,
        start_date: dayjs().format('YYYY-MM-DD'),
      });
      
      // 检查返回状态
      if (result.status === 'failed') {
        message.error(result.message || '创建执行计划失败');
        return;
      }
      
      // 立即跳转到执行计划详情页
      if (result?.plan_id) {
        navigate(`/execution/${result.plan_id}`);
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

  // 查看方案详情
  const handleViewDetail = (solutionId: string) => {
    if (latestDiagnosisId) {
      // 跳转到方案详情页，并传递方案ID
      navigate(`/solutions/${latestDiagnosisId}?solution_id=${solutionId}`);
    } else {
      // 如果没有诊断ID，使用弹窗方式（兼容旧逻辑）
      setSelectedSolutionId(solutionId);
      setDetailModalOpen(true);
    }
  };

  const columns: ColumnsType<SolutionSummary> = [
    {
      title: (
        <Tooltip title="勾选后点击「对比方案」">
          对比
        </Tooltip>
      ),
      dataIndex: 'compare',
      key: 'compare',
      width: 60,
      render: (_, record) => (
        <Checkbox
          checked={selectedForCompare.includes(record.solution_id)}
          onChange={() => toggleCompareSelection(record.solution_id)}
        />
      ),
    },
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
      render: (name: string) => (
        <span className="font-medium text-white">{name}</span>
      ),
    },
    {
      title: '针对异常',
      dataIndex: 'anomaly_ids',
      key: 'anomaly_ids',
      width: 200,
      render: (anomalyIds: string[] | undefined, record) => {
        if (!anomalyIds || anomalyIds.length === 0) {
          return <span className="text-gray-500">-</span>;
        }
        // 从诊断报告中查找异常名称
        const anomalies = diagnosisReport?.anomalies || [];
        const matchedAnomalies = anomalyIds
          .map(id => anomalies.find((a: Anomaly) => a.id === id))
          .filter(Boolean) as Anomaly[];
        
        if (matchedAnomalies.length === 0) {
          return (
            <Tooltip title={`异常ID: ${anomalyIds.join(', ')}`}>
              <span className="text-gray-500">{anomalyIds.length}个异常</span>
            </Tooltip>
          );
        }
        
        // 显示异常名称，最多显示3个
        const displayAnomalies = matchedAnomalies.slice(0, 3);
        const remainingAnomalies = matchedAnomalies.slice(3);
        const remainingCount = remainingAnomalies.length;
        
        const content = (
          <div className="flex flex-wrap gap-1">
            {displayAnomalies.map((anomaly) => (
              <Tag key={anomaly.id} color="orange" className="!m-0">
                {anomaly.rule_name}
              </Tag>
            ))}
            {remainingCount > 0 && (
              <Tooltip 
                title={
                  <div className="space-y-1">
                    {remainingAnomalies.map((anomaly) => (
                      <div key={anomaly.id} className="text-xs">{anomaly.rule_name}</div>
                    ))}
                  </div>
                }
              >
                <Tag color="orange" className="!m-0 cursor-help">
                  +{remainingCount}个
                </Tag>
              </Tooltip>
            )}
          </div>
        );
        
        // 如果有未匹配的异常ID，在Tooltip中显示
        const unmatchedIds = anomalyIds.filter(id => !matchedAnomalies.some(a => a.id === id));
        if (unmatchedIds.length > 0) {
          return (
            <Tooltip 
              title={
                <div>
                  <div className="mb-1">已显示异常：</div>
                  {matchedAnomalies.map(a => (
                    <div key={a.id} className="text-xs">• {a.rule_name}</div>
                  ))}
                  <div className="mt-2 mb-1">未匹配的异常ID：</div>
                  {unmatchedIds.map(id => (
                    <div key={id} className="text-xs text-gray-400">• {id}</div>
                  ))}
                </div>
              }
            >
              {content}
            </Tooltip>
          );
        }
        
        return content;
      },
    },
    {
      title: '推荐评分',
      dataIndex: 'score',
      key: 'score',
      width: 140,
      render: (score: number) => (
        <div className="flex items-center gap-2">
          <Progress 
            percent={score} 
            size="small" 
            strokeColor={score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444'}
            showInfo={false}
            className="w-20"
          />
          <span className={`font-bold ${
            score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-rose-400'
          }`}>
            {score}
          </span>
        </div>
      ),
    },
    {
      title: '预估成本',
      dataIndex: 'estimated_cost',
      key: 'estimated_cost',
      width: 110,
      render: (cost: number) => (
        <span className="text-gray-300">
          <DollarOutlined className="mr-1" />
          {cost >= 10000 ? `${(cost / 10000).toFixed(1)}万` : cost}
        </span>
      ),
    },
    {
      title: '预计周期',
      dataIndex: 'estimated_duration',
      key: 'estimated_duration',
      width: 90,
      render: (days: number) => (
        <span className="text-gray-300">
          <ClockCircleOutlined className="mr-1" />
          {days}天
        </span>
      ),
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      width: 90,
      render: (rate: number) => (
        <Tag color={rate >= 0.8 ? 'green' : rate >= 0.6 ? 'gold' : 'red'}>
          {(rate * 100).toFixed(0)}%
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_, record) => {
        const isAdopted = record.status === 'adopted';
        const isRejected = record.status === 'rejected';
        const hasExecutionPlan = !!record.execution_plan;
        
        return (
          <div className="flex gap-1">
            <Button 
              type="link" 
              size="small"
              onClick={() => handleViewDetail(record.solution_id)}
            >
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
            <Button 
              type="link" 
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => openRejectModal(record.solution_id)}
              disabled={isAdopted || isRejected}
              loading={rejectSolution.isPending}
            >
              {isRejected ? '已拒绝' : '拒绝'}
            </Button>
            {hasExecutionPlan ? (
              <Button 
                type="link" 
                size="small"
                icon={<RocketOutlined />}
                onClick={() => navigate(`/execution/${record.execution_plan!.plan_id}`)}
              >
                查看执行
              </Button>
            ) : (
              <Button 
                type="link" 
                size="small"
                icon={<RocketOutlined />}
                onClick={() => handleCreatePlan(record.solution_id)}
                loading={createPlan.isPending}
                disabled={isRejected || createPlan.isPending}
              >
                执行
              </Button>
            )}
          </div>
        );
      },
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
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-lg shadow-lg shadow-amber-500/20">
              <BulbOutlined />
            </span>
            推荐方案
          </h1>
          <p className="text-gray-400 mt-2 text-sm">
            基于诊断结果，AI智能推荐优化方案，按综合评分排序
          </p>
        </div>
        <div className="flex items-center gap-3">
          {selectedForCompare.length >= 2 && (
            <Button 
              icon={<SwapOutlined />}
              onClick={handleCompare}
              loading={compareSolutions.isPending}
            >
              对比方案 ({selectedForCompare.length})
            </Button>
          )}
        </div>
      </div>

      {/* 方案统计卡片 */}
      {solutionData && (
        <Row gutter={16}>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-blue-400">
                {solutionData.solution_count || solutionData.total || solutionData.solutions?.length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">方案总数</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-emerald-400">
                {solutionData.solutions?.filter((s: SolutionSummary) => s.score >= 70).length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">高分方案 (≥70分)</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center">
              <div className="text-3xl font-bold text-amber-400">
                {solutionData.solutions?.[0]?.score ? solutionData.solutions[0].score.toFixed(2) : 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">最高评分</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card className="text-center cursor-pointer hover:border-cyan-500/50 transition-colors" onClick={() => setShowFlowChart(!showFlowChart)}>
              <div className="text-3xl font-bold text-purple-400">
                {diagnosisReport?.anomalies?.length || 0}
              </div>
              <div className="text-gray-400 text-sm mt-1">
                {showFlowChart ? '隐藏流程图' : '查看关联流程'}
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {/* 方案生成关联流程图 */}
      {showFlowChart && diagnosisReport && (
        <SolutionFlowChart
          anomalies={(diagnosisReport.anomalies || []).map((a: Anomaly) => ({
            id: a.id,
            name: a.rule_name,
            severity: a.severity === 'critical' || a.severity === 'high' ? 'severe' : 'moderate',
            currentValue: a.current_value ? `${a.current_value.toFixed(1)}${getMetricUnit(a.metric_name, a.dimension)}` : undefined,
            solutionTags: a.solution_tags || [],
          } as AnomalyFlowItem))}
          solutions={(solutionData?.solutions || []).map((s) => ({
            id: s.solution_id,
            name: s.name,
            category: 'sales_process', // 从名称推断类别
            applicableTags: getCategoryTags(
              s.name.includes('线索') || s.name.includes('转化') ? 'sales_process' :
              s.name.includes('营销') || s.name.includes('ROI') ? 'marketing_optimization' :
              s.name.includes('流失') || s.name.includes('留存') ? 'customer_retention' :
              s.name.includes('效率') || s.name.includes('任务') ? 'efficiency_improvement' : 'sales_process'
            ),
            score: s.score,
          } as SolutionFlowItem))}
        />
      )}

      {/* 高亮异常提示 */}
      {highlightAnomaly && (
        <Alert
          type="info"
          showIcon
          icon={<ArrowRightOutlined />}
          message={
            <span>
              正在查看针对异常「<span className="font-semibold text-cyan-400">{highlightAnomaly.rule_name}</span>」的关联方案
              {relatedSolutionIds.size > 0 && (
                <Tag color="cyan" className="!ml-2">{relatedSolutionIds.size} 个关联方案已高亮</Tag>
              )}
            </span>
          }
          className="!bg-cyan-500/10 !border-cyan-500/30"
        />
      )}

      {/* 方案列表 */}
      <Card>
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
            {isGenerating && (
              <p className="text-gray-400 mt-4 text-base">正在生成方案，请稍候...</p>
            )}
          </div>
        ) : !latestDiagnosisId ? (
          <Empty description="请先完成诊断后再生成方案" />
        ) : (
          <Table
            columns={columns}
            dataSource={solutionData?.solutions || []}
            rowKey="solution_id"
            pagination={false}
            rowClassName={(record) => 
              relatedSolutionIds.has(record.solution_id) 
                ? '!bg-cyan-500/10 border-l-2 !border-l-cyan-400' 
                : ''
            }
            locale={{
              emptyText: <Empty description="暂无方案，请点击「生成方案」" />,
            }}
          />
        )}
      </Card>

      {/* 方案详情弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <BulbOutlined className="text-amber-400" />
            <span>方案详情</span>
          </div>
        }
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedSolutionId(null);
        }}
        footer={null}
        width={800}
      >
        {detailLoading ? (
          <div className="flex items-center justify-center py-10">
            <Spin />
          </div>
        ) : solutionDetail ? (
          <div className="space-y-4">
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="方案名称" span={2}>
                <span className="font-medium">{solutionDetail.name}</span>
              </Descriptions.Item>
              <Descriptions.Item label="方案类别">
                <Tag color="blue">{solutionDetail.category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={solutionDetail.status === 'adopted' ? 'green' : solutionDetail.status === 'rejected' ? 'red' : 'default'}>
                  {solutionDetail.status === 'adopted' ? '已采纳' : solutionDetail.status === 'rejected' ? '已拒绝' : '待评估'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="预估成本">
                ¥{solutionDetail.estimated_cost.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="预计周期">
                {solutionDetail.estimated_duration}天
              </Descriptions.Item>
              <Descriptions.Item label="成功率">
                {(solutionDetail.success_rate * 100).toFixed(0)}%
              </Descriptions.Item>
              <Descriptions.Item label="评分">
                {solutionDetail.ranking_score}分
              </Descriptions.Item>
            </Descriptions>

            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">执行摘要</h4>
              <div className="bg-gray-800/50 rounded-lg p-3 text-gray-300 text-sm">
                {solutionDetail.executive_summary || '暂无摘要'}
              </div>
            </div>

            {/* 关联的异常指标 - 新增 */}
            {solutionDetail.related_anomalies && solutionDetail.related_anomalies.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
                  <WarningOutlined className="text-amber-400" />
                  针对的异常指标
                  <Tag color="red" className="!ml-1">{solutionDetail.related_anomalies.length}</Tag>
                </h4>
                <div className="space-y-2 max-h-36 overflow-y-auto">
                  {solutionDetail.related_anomalies.map((anomaly) => (
                    <div 
                      key={anomaly.id}
                      className="bg-gradient-to-r from-rose-500/10 to-transparent rounded-lg p-3 border border-rose-500/20"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-white font-medium text-sm">{anomaly.rule_name}</span>
                        <Tag color={
                          anomaly.severity === 'critical' ? 'red' :
                          anomaly.severity === 'high' ? 'orange' :
                          anomaly.severity === 'medium' ? 'gold' : 'blue'
                        } className="!m-0">
                          {anomaly.severity === 'critical' ? '严重' :
                           anomaly.severity === 'high' ? '高' :
                           anomaly.severity === 'medium' ? '中' : '低'}
                        </Tag>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        <span>当前值: <span className="text-rose-400 font-medium">{anomaly.current_value?.toFixed(1)}{getMetricUnit(anomaly.metric_name, anomaly.dimension)}</span></span>
                        {anomaly.benchmark_value && (
                          <span>基准: <span className="text-emerald-400">{anomaly.benchmark_value?.toFixed(1)}{getMetricUnit(anomaly.metric_name, anomaly.dimension)}</span></span>
                        )}
                        {anomaly.gap_percentage && (
                          <span>差距: <span className="text-amber-400">↓{anomaly.gap_percentage?.toFixed(1)}%</span></span>
                        )}
                      </div>
                      {anomaly.solution_tags && anomaly.solution_tags.length > 0 && (
                        <div className="flex items-center gap-1 mt-2">
                          <TagsOutlined className="text-cyan-400/70 text-xs" />
                          {anomaly.solution_tags.slice(0, 3).map((tag) => (
                            <Tag key={tag} className="!m-0 !text-xs !bg-cyan-500/10 !border-cyan-500/30 !text-cyan-400">
                              {getTagLabel(tag)}
                            </Tag>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">问题描述</h4>
              <div className="bg-gray-800/50 rounded-lg p-3 text-gray-300 text-sm">
                {solutionDetail.problem_statement || '暂无描述'}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">方案概述</h4>
              <div className="bg-gray-800/50 rounded-lg p-3 text-gray-300 text-sm">
                {solutionDetail.solution_overview || '暂无概述'}
              </div>
            </div>

            {solutionDetail.tasks && solutionDetail.tasks.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">
                  执行任务 
                  <Tag className="ml-2">{solutionDetail.tasks.length}</Tag>
                </h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {solutionDetail.tasks.map((task, index) => (
                    <div 
                      key={task.id}
                      className="bg-gray-800/50 rounded-lg p-3 flex justify-between items-center"
                    >
                      <div>
                        <span className="text-gray-500 mr-2">{index + 1}.</span>
                        <span className="text-white">{task.name}</span>
                        <span className="text-gray-500 text-xs ml-2">
                          ({task.duration_days}天)
                        </span>
                      </div>
                      <Tag color="blue">{task.execution_type}</Tag>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <Empty description="无法加载方案详情" />
        )}
      </Modal>

      {/* 方案对比弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <SwapOutlined className="text-cyan-400" />
            <span>方案对比</span>
          </div>
        }
        open={compareModalOpen}
        onCancel={() => {
          setCompareModalOpen(false);
          setComparisonData(null);
        }}
        footer={null}
        width={900}
      >
        {comparisonData ? (
          <div className="space-y-4">
            {/* 方案卡片对比 */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {comparisonData.solutions.map((solution, index) => (
                <Card 
                  key={solution.id} 
                  size="small"
                  className={`${index === 0 ? 'border-amber-500 border-2' : ''}`}
                >
                  <div className="text-center">
                    {index === 0 && (
                      <Tag color="gold" className="!mb-2">推荐</Tag>
                    )}
                    <div className="font-medium text-white mb-2 truncate" title={solution.name}>
                      {solution.name}
                    </div>
                    <div className="text-2xl font-bold text-cyan-400 mb-1">
                      {solution.ranking_score}分
                    </div>
                    <Tag color="blue">{solution.category}</Tag>
                  </div>
                </Card>
              ))}
            </div>

            {/* 详细对比表格 */}
            <Card title="对比维度" size="small">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 text-gray-400">维度</th>
                    {comparisonData.solutions.map((s) => (
                      <th key={s.id} className="text-center py-2 text-gray-300">
                        {s.name.length > 10 ? s.name.substring(0, 10) + '...' : s.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-gray-800">
                    <td className="py-3 text-gray-400">评分</td>
                    {comparisonData.solutions.map((s) => {
                      const max = Math.max(...comparisonData.solutions.map(x => x.ranking_score));
                      const isMax = s.ranking_score === max;
                      return (
                        <td key={s.id} className={`text-center py-3 ${isMax ? 'text-emerald-400 font-bold' : 'text-gray-300'}`}>
                          {s.ranking_score}分 {isMax && '✓'}
                        </td>
                      );
                    })}
                  </tr>
                  <tr className="border-b border-gray-800">
                    <td className="py-3 text-gray-400">预估成本</td>
                    {comparisonData.solutions.map((s) => {
                      const min = Math.min(...comparisonData.solutions.map(x => x.estimated_cost));
                      const isMin = s.estimated_cost === min;
                      return (
                        <td key={s.id} className={`text-center py-3 ${isMin ? 'text-emerald-400 font-bold' : 'text-gray-300'}`}>
                          ¥{s.estimated_cost >= 10000 ? `${(s.estimated_cost / 10000).toFixed(1)}万` : s.estimated_cost} {isMin && '✓'}
                        </td>
                      );
                    })}
                  </tr>
                  <tr className="border-b border-gray-800">
                    <td className="py-3 text-gray-400">预计周期</td>
                    {comparisonData.solutions.map((s) => {
                      const min = Math.min(...comparisonData.solutions.map(x => x.estimated_duration));
                      const isMin = s.estimated_duration === min;
                      return (
                        <td key={s.id} className={`text-center py-3 ${isMin ? 'text-emerald-400 font-bold' : 'text-gray-300'}`}>
                          {s.estimated_duration}天 {isMin && '✓'}
                        </td>
                      );
                    })}
                  </tr>
                  <tr className="border-b border-gray-800">
                    <td className="py-3 text-gray-400">成功率</td>
                    {comparisonData.solutions.map((s) => {
                      const max = Math.max(...comparisonData.solutions.map(x => x.success_rate));
                      const isMax = s.success_rate === max;
                      return (
                        <td key={s.id} className={`text-center py-3 ${isMax ? 'text-emerald-400 font-bold' : 'text-gray-300'}`}>
                          {(s.success_rate * 100).toFixed(0)}% {isMax && '✓'}
                        </td>
                      );
                    })}
                  </tr>
                  <tr>
                    <td className="py-3 text-gray-400">任务数</td>
                    {comparisonData.solutions.map((s) => (
                      <td key={s.id} className="text-center py-3 text-gray-300">
                        {s.task_count}个
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </Card>
          </div>
        ) : (
          <div className="flex items-center justify-center py-10">
            <Spin />
          </div>
        )}
      </Modal>

      {/* 拒绝方案弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <CloseCircleOutlined className="text-rose-400" />
            <span>拒绝方案</span>
          </div>
        }
        open={rejectModalOpen}
        onCancel={() => {
          setRejectModalOpen(false);
          setRejectReason('');
          setRejectingSolutionId(null);
        }}
        onOk={handleReject}
        okText="确认拒绝"
        okButtonProps={{ danger: true, loading: rejectSolution.isPending }}
        cancelText="取消"
      >
        <div className="py-4">
          <p className="text-gray-400 mb-3">请输入拒绝原因（可选）：</p>
          <Input.TextArea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="例如：成本过高、周期太长、不符合业务需求等"
            rows={3}
          />
        </div>
      </Modal>
    </div>
  );
}
