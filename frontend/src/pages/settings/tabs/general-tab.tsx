import { forwardRef, useEffect } from 'react';
import { Card, Form, Select, Descriptions, Row, Col } from 'antd';
import type { FormInstance } from 'antd';

export type GeneralFormValues = {
  analysis_period_days?: number;
  auto_diagnosis_frequency?: string;
  solution_sort_strategy?: string;
  max_solutions?: number;
};

interface GeneralTabProps {
  currentEnterprise: any;
  config?: Record<string, unknown>;
  context?: Record<string, unknown>;
  formRef: React.RefObject<FormInstance>;
}

const GeneralTab = forwardRef<unknown, GeneralTabProps>(
  ({ currentEnterprise, config, context, formRef }, _ref) => {
    const c = config || {};
    const ctx = context || {};

    const initialValues: GeneralFormValues = {
      analysis_period_days: (c.analysis_period_days as number) ?? 90,
      auto_diagnosis_frequency: (c.auto_diagnosis_frequency as string) ?? 'weekly',
      solution_sort_strategy: (c.solution_sort_strategy as string) ?? 'balanced',
      max_solutions: (c.max_solutions as number) ?? 5,
    };

    useEffect(() => {
      formRef.current?.setFieldsValue(initialValues);
    }, [config, formRef]);

    return (
      <div className="space-y-6">
        <Card title="企业信息" size="small">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="企业ID">
              <span className="font-mono text-xs">{currentEnterprise?.id || '-'}</span>
            </Descriptions.Item>
            <Descriptions.Item label="企业名称">
              {(ctx.name as string) || currentEnterprise?.name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="行业">
              {(ctx.industry as string) || currentEnterprise?.industry || '-'}
            </Descriptions.Item>
          </Descriptions>
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
