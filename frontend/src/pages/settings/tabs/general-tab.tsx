import { forwardRef, useEffect } from 'react';
import { Card, Form, Select, Descriptions, Row, Col } from 'antd';
import type { FormInstance } from 'antd';
import type { EnterpriseStore } from '@/lib/api';

export type GeneralFormValues = {
  analysis_period_days?: number;
  auto_diagnosis_frequency?: 'auto' | 'manual';
  solution_sort_strategy?: string;
  max_solutions?: number;
};

function normalizeAutoDiagnosisMode(value?: string): 'auto' | 'manual' {
  return value === 'manual' ? 'manual' : value ? 'auto' : 'manual';
}

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
    const stores = (ctx.stores as EnterpriseStore[] | undefined) ?? [];
    const storeNames = stores
      .map((store) => store.store_name?.trim())
      .filter(Boolean)
      .join(', ');

    const initialValues: GeneralFormValues = {
      analysis_period_days: (c.analysis_period_days as number) ?? 90,
      auto_diagnosis_frequency: normalizeAutoDiagnosisMode(c.auto_diagnosis_frequency as string | undefined),
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
            <Descriptions.Item label="团队规模">
              {typeof ctx.team_size === 'number' ? `${ctx.team_size} 人` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="店铺" span={2}>
              {storeNames || '-'}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Form ref={formRef} layout="vertical" initialValues={initialValues}>
          <Card title="诊断配置" size="small">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="auto_diagnosis_frequency" label="诊断方式">
                  <Select>
                    <Select.Option value="manual">手动</Select.Option>
                    <Select.Option value="auto">自动</Select.Option>
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

        </Form>
      </div>
    );
  }
);

GeneralTab.displayName = 'GeneralTab';
export default GeneralTab;
