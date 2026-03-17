

import { forwardRef, useEffect, useState } from 'react';
import { Card, Form, Select, InputNumber, Descriptions, Tag, Row, Col, Tooltip, Button, Progress, App } from 'antd';
import { InfoCircleOutlined, ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd';
import { enterpriseApi, type DataQualityReport } from '@/lib/api';

export type GeneralFormValues = {
  analysis_period_days?: number;
  auto_diagnosis_frequency?: string;
  // industry_benchmark?: string;  // 暂未实现，注释掉
  solution_sort_strategy?: string;
  max_solutions?: number;
};

export type ContextFormValues = {
  industry?: string;
  scale?: string;
  team_size?: number;
  budget_level?: string;
};

const INDUSTRY_OPTIONS = [
  { value: 'general', label: '通用' },
  { value: 'retail', label: '零售' },
  { value: 'finance', label: '金融' },
  { value: 'manufacturing', label: '制造业' },
  { value: '制造', label: '制造' },
  { value: 'internet', label: '互联网' },
  { value: 'other', label: '其他' },
];

function scoreColor(v: number) {
  if (v >= 0.8) return '#52c41a';
  if (v >= 0.6) return '#faad14';
  return '#ff4d4f';
}

function scoreLabel(v: number) {
  if (v >= 0.8) return '优';
  if (v >= 0.6) return '中';
  return '差';
}

interface GeneralTabProps {
  currentEnterprise: any;
  enabledCount: number;
  totalCount: number;
  config?: Record<string, unknown>;
  context?: Record<string, unknown>;
  formRef: React.RefObject<FormInstance>;
  contextFormRef: React.RefObject<FormInstance>;
}

const GeneralTab = forwardRef<unknown, GeneralTabProps>(
  ({ currentEnterprise, enabledCount, totalCount, config, context, formRef, contextFormRef }, _ref) => {
    const { message } = App.useApp();
    const c = config || {};
    const ctx = context || {};

    const [dqReport, setDqReport] = useState<DataQualityReport | null>(null);
    const [dqLoading, setDqLoading] = useState(false);

    const initialValues: GeneralFormValues = {
      analysis_period_days: (c.analysis_period_days as number) ?? 90,
      auto_diagnosis_frequency: (c.auto_diagnosis_frequency as string) ?? 'weekly',
      // industry_benchmark: (c.industry_benchmark as string) ?? 'general',  // 暂未实现，注释掉
      solution_sort_strategy: (c.solution_sort_strategy as string) ?? 'balanced',
      max_solutions: (c.max_solutions as number) ?? 5,
    };

    const contextInitialValues: ContextFormValues = {
      industry: (ctx.industry as string) ?? currentEnterprise?.industry ?? 'general',
      scale: (ctx.scale as string) ?? 'medium',
      team_size: (ctx.team_size as number) ?? 10,
      budget_level: (ctx.budget_level as string) ?? 'medium',
    };

    useEffect(() => {
      formRef.current?.setFieldsValue(initialValues);
    }, [config, formRef]);

    useEffect(() => {
      contextFormRef.current?.setFieldsValue(contextInitialValues);
    }, [context, contextFormRef]);

    const handleEvaluateDataQuality = async () => {
      if (!currentEnterprise?.id) return;
      setDqLoading(true);
      try {
        const report = await enterpriseApi.evaluateDataQuality(currentEnterprise.id);
        setDqReport(report);
        message.success(`数据质量评估完成：${(report.score * 100).toFixed(0)}%`);
      } catch {
        message.error('数据质量评估失败');
      } finally {
        setDqLoading(false);
      }
    };

    const dqScore = dqReport?.score ?? (ctx.data_quality as number) ?? 0.8;

    return (
      <div className="space-y-6">
        {/* 企业信息 */}
        <Form ref={contextFormRef} layout="vertical" initialValues={contextInitialValues}>
          <Card title="企业信息" size="small">
            <Descriptions column={2} size="small" className="mb-4">
              <Descriptions.Item label="企业ID">
                <span className="font-mono text-xs">{currentEnterprise?.id || '-'}</span>
              </Descriptions.Item>
              <Descriptions.Item label="企业名称">
                {currentEnterprise?.name || '-'}
              </Descriptions.Item>
            </Descriptions>
            <div className="border-t pt-4 mt-4">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="industry" label="行业">
                    <Select
                      placeholder="选择行业，影响行业基准取值"
                      options={INDUSTRY_OPTIONS}
                      allowClear
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="scale" label="企业规模">
                    <Select>
                      <Select.Option value="small">小型（成本×0.7, 工期×0.8）</Select.Option>
                      <Select.Option value="medium">中型（标准基准）</Select.Option>
                      <Select.Option value="large">大型（成本×1.5, 工期×1.3）</Select.Option>
                      <Select.Option value="enterprise">集团（成本×2.0, 工期×1.5）</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="team_size" label="团队人数">
                    <InputNumber min={1} max={100000} className="!w-full" placeholder="影响前置条件检查" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="budget_level" label="预算等级">
                    <Select>
                      <Select.Option value="low">低预算（成本×0.5）</Select.Option>
                      <Select.Option value="medium">中等预算（标准基准）</Select.Option>
                      <Select.Option value="high">高预算（成本×2.0）</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
            </div>
          </Card>
        </Form>

        {/* 数据质量评估 —— 自动计算，不可手动编辑 */}
        <Card
          title={
            <span className="flex items-center gap-2">
              数据质量评估
              <Tooltip title="系统自动探测各数据源，计算指标覆盖率、连通率、有效率和时效性，方案生成时也会自动刷新">
                <InfoCircleOutlined className="text-gray-400" />
              </Tooltip>
            </span>
          }
          size="small"
          extra={
            <Button
              icon={<ReloadOutlined />}
              loading={dqLoading}
              onClick={handleEvaluateDataQuality}
              size="small"
            >
              立即评估
            </Button>
          }
        >
          <Row gutter={16} align="middle">
            <Col span={4} className="text-center">
              <Progress
                type="circle"
                percent={Math.round(dqScore * 100)}
                size={80}
                strokeColor={scoreColor(dqScore)}
                format={(p) => <span style={{ color: scoreColor(dqScore), fontSize: 18, fontWeight: 700 }}>{p}%</span>}
              />
              <div className="mt-1 text-xs text-gray-400">
                综合评分 · <span style={{ color: scoreColor(dqScore) }}>{scoreLabel(dqScore)}</span>
              </div>
            </Col>
            <Col span={20}>
              {dqReport ? (
                <div className="space-y-3">
                  <Row gutter={16}>
                    {[
                      { label: '指标覆盖率', value: dqReport.metric_coverage, tip: '各维度能采集到多少比例的指标' },
                      { label: '数据源连通率', value: dqReport.connectivity, tip: '启用维度的连通比例' },
                      { label: '指标有效率', value: dqReport.validity, tip: '采集到的指标中非零值占比' },
                      { label: '数据时效性', value: dqReport.freshness, tip: '指标数据是否在近期更新' },
                    ].map((item) => (
                      <Col span={6} key={item.label}>
                        <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                          {item.label}
                          <Tooltip title={item.tip}><InfoCircleOutlined className="text-gray-500" style={{ fontSize: 10 }} /></Tooltip>
                        </div>
                        <Progress
                          percent={Math.round(item.value * 100)}
                          size="small"
                          strokeColor={scoreColor(item.value)}
                        />
                      </Col>
                    ))}
                  </Row>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">维度探测详情</div>
                    <div className="flex flex-wrap gap-2">
                      {dqReport.dimensions.map((d) => (
                        <Tag
                          key={d.dimension}
                          icon={d.connected ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                          color={d.connected ? 'success' : 'error'}
                        >
                          {d.dimension} {d.fetched_count}/{d.supported_count}
                        </Tag>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-sm py-4">
                  当前评分：<span className="text-white font-semibold">{(dqScore * 100).toFixed(0)}%</span>
                  <span className="ml-2 text-gray-600">（点击「立即评估」获取详细报告，方案生成时也会自动刷新）</span>
                </div>
              )}
            </Col>
          </Row>
        </Card>

        <Form ref={formRef} layout="vertical" initialValues={initialValues}>
          <Card title="诊断配置" size="small">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="auto_diagnosis_frequency" label="自动诊断频率">
                  <Select>
                    <Select.Option value="daily">每日</Select.Option>
                    <Select.Option value="weekly">每周</Select.Option>
                    <Select.Option value="monthly">每月</Select.Option>
                    <Select.Option value="manual">仅手动</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="analysis_period_days" label="数据分析周期">
                  <Select>
                    <Select.Option value={30}>近30天</Select.Option>
                    <Select.Option value={60}>近60天</Select.Option>
                    <Select.Option value={90}>近90天</Select.Option>
                    <Select.Option value={180}>近180天</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            {/* 行业基准选择 - 暂未实现，注释掉
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="industry_benchmark" label="行业基准">
                  <Select>
                    <Select.Option value="general">通用基准</Select.Option>
                    <Select.Option value="retail">零售行业</Select.Option>
                    <Select.Option value="finance">金融行业</Select.Option>
                    <Select.Option value="manufacturing">制造业</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            */}
          </Card>

          <Card title="方案配置" size="small" className="mt-6">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="solution_sort_strategy" label="方案排序策略">
                  <Select>
                    <Select.Option value="balanced">综合评分</Select.Option>
                    <Select.Option value="roi_first">投资回报率优先</Select.Option>
                    <Select.Option value="quick_win">快速见效优先</Select.Option>
                    <Select.Option value="risk_averse">风险规避</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="max_solutions" label="最大方案数">
                  <Select>
                    <Select.Option value={3}>3个</Select.Option>
                    <Select.Option value={5}>5个</Select.Option>
                    <Select.Option value={10}>10个</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
          </Card>
        </Form>
      </div>
    );
  }
);

GeneralTab.displayName = 'GeneralTab';
export default GeneralTab;

