

import { useState } from 'react';
import {
  Card, Form, Input, Select, Switch, Button, App, Tag, Divider, Space,
  Row, Col, Table, Tooltip, Badge, Modal, InputNumber, Popconfirm, ColorPicker, Alert,
} from 'antd';
import { Descriptions } from 'antd';
import type { Color } from 'antd/es/color-picker';
import type { ColumnsType } from 'antd/es/table';
import {
  EditOutlined, CheckCircleOutlined, CloseCircleOutlined,
  PlusOutlined, DeleteOutlined, PlayCircleOutlined, CodeOutlined,
} from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { customDimensionApi } from '@/lib/api';

interface DimensionOption {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  icon?: string;
  color?: string;
  weight: number;
  is_system: boolean;
  enabled: boolean;
  metrics_config?: { metrics: Array<{ name: string; display_name: string; unit?: string; data_source?: string; benchmark?: { avg?: number; excellent?: number; median?: number } }> };
  rules_config?: { rules: Array<{ id: string; name: string; metric?: string; operator?: string; threshold?: number; severity?: string; solution_tags?: string[]; root_cause_chain?: string[] }> };
  tasks_config?: { tasks: Array<{ task_id: string; name: string; description?: string; execution_type?: string; duration_days?: number; dependencies?: string[]; trigger_rules?: string[]; config?: any }> };
  data_source_config?: { type?: string; api_config?: any; database_config?: any };
}

interface DimensionsTabProps {
  allDimensions: DimensionOption[];
  dimensionsLoading: boolean;
  loadDimensions: () => void;
  currentEnterprise: any;
}

export default function DimensionsTab({ allDimensions, dimensionsLoading, loadDimensions, currentEnterprise }: DimensionsTabProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingDimension, setEditingDimension] = useState<DimensionOption | null>(null);
  const [editForm] = Form.useForm();
  const [editSaving, setEditSaving] = useState(false);
  const [generatingRules, setGeneratingRules] = useState(false);

  const handleToggleDimension = async (dimension: DimensionOption) => {
    try {
      await customDimensionApi.toggle(dimension.id);
      message.success(`维度 "${dimension.display_name}" 已${dimension.enabled ? '禁用' : '启用'}`);
      loadDimensions();
      queryClient.invalidateQueries({ queryKey: ['dimensions'] });
    } catch (error) {
      console.error('Toggle failed:', error);
      message.error('更新状态失败');
    }
  };

  const handleDeleteDimension = async (dimension: DimensionOption) => {
    if (dimension.is_system) {
      message.warning('系统预设维度不可删除');
      return;
    }
    try {
      await customDimensionApi.delete(dimension.id);
      message.success(`维度 "${dimension.display_name}" 已删除`);
      loadDimensions();
      queryClient.invalidateQueries({ queryKey: ['dimensions'] });
    } catch (error) {
      console.error('Delete failed:', error);
      message.error('删除失败');
    }
  };

  const openEditModal = (dimension?: DimensionOption) => {
    if (dimension) {
      setEditingDimension(dimension);
      const dimData = dimension as any;
      const processedTasks = (dimData.tasks_config?.tasks || []).map((task: any) => {
        const processedTask = { ...task };
        if (processedTask.config) {
          if (processedTask.config.headers && typeof processedTask.config.headers === 'object') {
            processedTask.config = { ...processedTask.config, headers: JSON.stringify(processedTask.config.headers, null, 2) };
          }
          if (processedTask.config.body && typeof processedTask.config.body === 'object') {
            processedTask.config = { ...processedTask.config, body: JSON.stringify(processedTask.config.body, null, 2) };
          }
          if (processedTask.config.env && typeof processedTask.config.env === 'object') {
            processedTask.config = { ...processedTask.config, env: JSON.stringify(processedTask.config.env, null, 2) };
          }
        }
        return processedTask;
      });
      editForm.setFieldsValue({
        name: dimension.name,
        display_name: dimension.display_name,
        description: dimension.description,
        icon: dimension.icon,
        color: dimension.color,
        weight: dimension.weight,
        metrics: dimension.metrics_config?.metrics || [],
        rules: dimension.rules_config?.rules || [],
        tasks: processedTasks,
        data_source: dimData.data_source_config || { type: 'manual' },
      });
    } else {
      setEditingDimension(null);
      editForm.resetFields();
      editForm.setFieldsValue({
        weight: 0.2,
        metrics: [{ name: '', display_name: '', unit: '%', data_source: 'manual', benchmark: { avg: 50, excellent: 80, median: 60 } }],
        rules: [],
        tasks: [],
        data_source: { type: 'manual' },
      });
    }
    setEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    try {
      const values = await editForm.validateFields();
      setEditSaving(true);
      const processedTasks = (values.tasks || []).map((task: any) => {
        if (!task?.task_id || !task?.name) return null;
        const processedTask: any = {
          task_id: task.task_id, name: task.name, description: task.description,
          execution_type: task.execution_type, duration_days: task.duration_days,
          dependencies: task.dependencies || [],
          trigger_rules: task.trigger_rules?.length > 0 ? task.trigger_rules : undefined,
          config: {},
        };
        if (task.config) {
          if (task.config.headers) {
            try { processedTask.config.headers = typeof task.config.headers === 'string' ? JSON.parse(task.config.headers) : task.config.headers; } catch { processedTask.config.headers = {}; }
          }
          if (task.config.body) {
            try { processedTask.config.body = typeof task.config.body === 'string' ? JSON.parse(task.config.body) : task.config.body; } catch { processedTask.config.body = task.config.body; }
          }
          if (task.config.env) {
            try { processedTask.config.env = typeof task.config.env === 'string' ? JSON.parse(task.config.env) : task.config.env; } catch { processedTask.config.env = {}; }
          }
          Object.keys(task.config).forEach(key => {
            if (!['headers', 'body', 'env'].includes(key)) {
              processedTask.config[key] = task.config[key];
            }
          });
        }
        return processedTask;
      }).filter(Boolean);

      const data = {
        name: values.name, display_name: values.display_name, description: values.description,
        icon: values.icon || 'BarChartOutlined',
        color: typeof values.color === 'string' ? values.color : (values.color as Color)?.toHexString?.() || '#1890ff',
        weight: values.weight, metrics: values.metrics,
        rules: values.rules?.filter((r: any) => r?.id && r?.metric) || [],
        tasks: processedTasks,
        data_source: values.data_source?.type ? values.data_source : undefined,
        enabled: true,
      };
      if (editingDimension) {
        await customDimensionApi.update(editingDimension.id, data);
        message.success('维度更新成功');
      } else {
        await customDimensionApi.create(currentEnterprise!.id, data);
        message.success('维度创建成功');
      }
      setEditModalOpen(false);
      loadDimensions();
      queryClient.invalidateQueries({ queryKey: ['dimensions'] });
    } catch (error) {
      console.error('Save failed:', error);
      message.error('保存失败');
    } finally {
      setEditSaving(false);
    }
  };

  const operatorOptions = [
    { label: '小于 (<)', value: 'lt' }, { label: '大于 (>)', value: 'gt' },
    { label: '等于 (=)', value: 'eq' }, { label: '小于等于 (≤)', value: 'le' }, { label: '大于等于 (≥)', value: 'ge' },
  ];
  const severityOptions = [
    { label: '严重', value: 'critical', color: 'red' },
    { label: '警告', value: 'warning', color: 'orange' },
    { label: '提示', value: 'info', color: 'blue' },
  ];

  const handleGenerateRules = async () => {
    const metrics = editForm.getFieldValue('metrics');
    const dimensionName = editForm.getFieldValue('name');
    const dimensionDisplayName = editForm.getFieldValue('display_name');
    if (!metrics || metrics.length === 0) { message.warning('请先配置至少一个指标（含基准值），才能自动生成规则'); return; }
    const hasValidBenchmark = metrics.some((m: any) => m?.benchmark?.avg);
    if (!hasValidBenchmark) { message.warning('请为指标设置行业基准值（至少填写均值），系统将据此推算阈值'); return; }
    setGeneratingRules(true);
    try {
      const res = await customDimensionApi.generateRules({ dimension_name: dimensionName || 'custom', dimension_display_name: dimensionDisplayName || '', metrics });
      const rules = (res?.data as any)?.rules || (res as any)?.rules || [];
      if (rules.length > 0) { editForm.setFieldValue('rules', rules); message.success(`已基于 ${rules.length} 个指标自动生成诊断规则`); }
      else { message.info('未能生成规则，请检查指标是否配置了基准值'); }
    } catch (e) { message.error('规则生成失败，请稍后重试'); }
    finally { setGeneratingRules(false); }
  };

  const dimensionColumns: ColumnsType<DimensionOption> = [
    {
      title: '维度', key: 'dimension',
      render: (_, record) => (
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-lg flex items-center justify-center text-base shrink-0 shadow-sm"
            style={{ backgroundColor: (record.color || '#1890ff') + '20', color: record.color || '#1890ff' }}>
            {record.is_system ? '📊' : '🔧'}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-white">{record.display_name}</span>
              {record.is_system ? (
                <Tag color="blue" className="text-xs m-0">系统预设</Tag>
              ) : (
                <Tag color="purple" className="text-xs m-0">自定义</Tag>
              )}
            </div>
            <div className="text-xs text-gray-500 font-mono">{record.name}</div>
          </div>
        </div>
      ),
    },
    { 
      title: '描述', 
      dataIndex: 'description', 
      key: 'description', 
      ellipsis: { showTitle: false },
      render: (text: string) => (
        <Tooltip title={text || '-'}>
          <span className="text-gray-400">{text || '-'}</span>
        </Tooltip>
      )
    },
    { 
      title: '权重', 
      dataIndex: 'weight', 
      key: 'weight', 
      width: 100, 
      align: 'center', 
      render: (val: number) => (
        <Tag color="cyan" className="font-medium">{(val * 100).toFixed(0)}%</Tag>
      )
    },
    { 
      title: '指标', 
      key: 'metrics', 
      width: 90, 
      align: 'center', 
      render: (_, record) => (
        <Tooltip title={record.metrics_config?.metrics?.map(m => m.display_name).join('、') || '无'}>
          <Tag className="cursor-help">{record.metrics_config?.metrics?.length || 0}</Tag>
        </Tooltip>
      )
    },
    { 
      title: '规则', 
      key: 'rules', 
      width: 90, 
      align: 'center', 
      render: (_, record) => (
        <Tooltip title={record.rules_config?.rules?.map(r => r.name).join('、') || '无'}>
          <Tag className="cursor-help">{record.rules_config?.rules?.length || 0}</Tag>
        </Tooltip>
      )
    },
    { 
      title: '任务', 
      key: 'tasks', 
      width: 90, 
      align: 'center', 
      render: (_, record) => (
        <Tooltip title={record.tasks_config?.tasks?.map(t => t.name).join('、') || '无'}>
          <Tag color="purple" className="cursor-help">{record.tasks_config?.tasks?.length || 0}</Tag>
        </Tooltip>
      )
    },
    {
      title: '状态', 
      dataIndex: 'enabled', 
      key: 'enabled', 
      width: 100, 
      align: 'center',
      render: (enabled: boolean, record) => (
        <Switch 
          checked={enabled} 
          onChange={() => handleToggleDimension(record)}
          checkedChildren={<CheckCircleOutlined />} 
          unCheckedChildren={<CloseCircleOutlined />}
          size="small"
        />
      ),
    },
    {
      title: '操作', 
      key: 'actions', 
      width: 120, 
      align: 'center',
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑维度">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => openEditModal(record)}
              className="hover:bg-blue-500/20"
            />
          </Tooltip>
          {!record.is_system && (
            <Popconfirm 
              title="确定删除此维度？" 
              description="删除后不可恢复，相关诊断数据也将丢失"
              onConfirm={() => handleDeleteDimension(record)} 
              okText="删除" 
              cancelText="取消" 
              okButtonProps={{ danger: true }}
            >
              <Tooltip title="删除维度">
                <Button 
                  type="text" 
                  danger 
                  icon={<DeleteOutlined />}
                  className="hover:bg-red-500/20"
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" className="bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/15 transition-colors">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400 mb-1">{allDimensions.filter(d => d.is_system).length}</div>
              <div className="text-sm text-gray-400">系统预设</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" className="bg-purple-500/10 border-purple-500/30 hover:bg-purple-500/15 transition-colors">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-400 mb-1">{allDimensions.filter(d => !d.is_system).length}</div>
              <div className="text-sm text-gray-400">自定义维度</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" className="bg-green-500/10 border-green-500/30 hover:bg-green-500/15 transition-colors">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400 mb-1">{allDimensions.filter(d => d.enabled).length}</div>
              <div className="text-sm text-gray-400">已启用</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" className="bg-gray-500/10 border-gray-500/30 hover:bg-gray-500/15 transition-colors">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-400 mb-1">{allDimensions.filter(d => !d.enabled).length}</div>
              <div className="text-sm text-gray-400">已禁用</div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card 
        title={<span className="text-base font-semibold">维度列表</span>} 
        size="small" 
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openEditModal()}>
            新建维度
          </Button>
        }
        className="shadow-sm"
      >
        <Table 
          columns={dimensionColumns} 
          dataSource={allDimensions} 
          rowKey="id" 
          loading={dimensionsLoading} 
          pagination={false} 
          size="small"
          rowClassName={(record) => record.enabled ? '' : 'opacity-60'} 
          className="dimensions-table"
        />
      </Card>

      {/* 编辑维度弹窗 */}
      <Modal title={editingDimension ? '编辑维度' : '新建维度'} open={editModalOpen}
        onCancel={() => setEditModalOpen(false)} onOk={handleSaveEdit}
        confirmLoading={editSaving} width={800} okText="保存" cancelText="取消">
        <Form form={editForm} layout="vertical" className="mt-4 max-h-[65vh] overflow-y-auto pr-2">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="维度标识" rules={[{ required: true, message: '请输入维度标识' }, { pattern: /^[a-z][a-z0-9_]*$/, message: '只能使用小写字母、数字和下划线，且以字母开头' }]} tooltip="唯一标识，用于系统内部识别">
                <Input placeholder="如: finance, supply_chain" disabled={!!editingDimension} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="display_name" label="显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
                <Input placeholder="如: 财务指标" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述"><Input.TextArea placeholder="维度的详细说明" rows={2} /></Form.Item>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="color" label="主题色"><ColorPicker showText /></Form.Item></Col>
            <Col span={12}><Form.Item name="weight" label="权重" tooltip="在健康度计算中的权重占比"><InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>

          <Divider>指标配置</Divider>
          <Form.List name="metrics">
            {(fields, { add, remove }) => (
              <div className="space-y-4">
                {fields.map((field, index) => (
                  <Card key={field.key} size="small" title={`指标 ${index + 1}`}
                    extra={fields.length > 1 && <Button type="text" danger size="small" onClick={() => remove(field.name)}>删除</Button>}>
                    <Row gutter={16}>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'name']} label="指标标识" rules={[{ required: true, message: '必填' }]}><Input placeholder="如: profit_margin" /></Form.Item></Col>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'display_name']} label="显示名称" rules={[{ required: true, message: '必填' }]}><Input placeholder="如: 利润率" /></Form.Item></Col>
                      <Col span={4}><Form.Item {...field} name={[field.name, 'unit']} label="单位"><Input placeholder="%" /></Form.Item></Col>
                      <Col span={4}>
                        <Form.Item {...field} name={[field.name, 'data_source']} label="数据来源">
                          <Select>
                            <Select.Option value="manual">手动录入</Select.Option>
                            <Select.Option value="api">API接口</Select.Option>
                            <Select.Option value="formula">公式计算</Select.Option>
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item noStyle shouldUpdate={(prev, cur) => prev?.metrics?.[field.name]?.data_source !== cur?.metrics?.[field.name]?.data_source}>
                      {({ getFieldValue }) => {
                        const dataSource = getFieldValue(['metrics', field.name, 'data_source']);
                        return dataSource === 'api' ? (
                          <Row gutter={16}><Col span={24}><Form.Item {...field} name={[field.name, 'api_endpoint']} label="API 端点" tooltip="数据获取的 API 路径"><Input placeholder="如: /api/erp/metrics/profit" addonBefore="GET" /></Form.Item></Col></Row>
                        ) : dataSource === 'formula' ? (
                          <Row gutter={16}><Col span={24}><Form.Item {...field} name={[field.name, 'formula']} label="计算公式" tooltip="使用其他指标计算"><Input placeholder="如: metric_a / metric_b * 100" /></Form.Item></Col></Row>
                        ) : null;
                      }}
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'benchmark', 'avg']} label="行业平均"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'benchmark', 'excellent']} label="优秀值"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'benchmark', 'median']} label="中位数"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
                    </Row>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add({ name: '', display_name: '', unit: '%', data_source: 'manual', benchmark: { avg: 50, excellent: 80, median: 60 } })} block icon={<PlusOutlined />}>添加指标</Button>
              </div>
            )}
          </Form.List>

          <Divider>诊断规则（可选）</Divider>
          <Alert message="系统可根据上方指标的行业基准值自动推算阈值，并通过 AI 生成根因链和方案标签。建议先配置好指标及基准值，再点击「智能生成」。" type="info" showIcon style={{ marginBottom: 16 }} />
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlayCircleOutlined />} loading={generatingRules} onClick={handleGenerateRules}>智能生成规则</Button>
            <span style={{ marginLeft: 8, color: '#888', fontSize: 12 }}>基于指标基准值自动推算阈值，AI 生成根因链和方案标签</span>
          </div>
          <Form.List name="rules">
            {(fields, { add, remove }) => (
              <div className="space-y-4">
                {fields.map((field, index) => (
                  <Card key={field.key} size="small" title={`规则 ${index + 1}`} extra={<Button type="text" danger size="small" onClick={() => remove(field.name)}>删除</Button>}>
                    <Row gutter={16}>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'id']} label={<span>规则ID <Tooltip title="系统自动生成，一般无需修改"><span style={{color:'#888',fontSize:12}}>（自动）</span></Tooltip></span>} rules={[{ required: true }]}><Input placeholder="如: finance_profit_low" /></Form.Item></Col>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'name']} label="规则名称" rules={[{ required: true }]}><Input placeholder="如: 利润率异常" /></Form.Item></Col>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'metric']} label="关联指标" rules={[{ required: true }]}><Input placeholder="指标标识" /></Form.Item></Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={6}><Form.Item {...field} name={[field.name, 'operator']} label="比较方式"><Select options={operatorOptions} /></Form.Item></Col>
                      <Col span={6}><Form.Item {...field} name={[field.name, 'threshold']} label="阈值" tooltip="基于行业基准值自动推算。越高越好的指标取均值×0.7，越低越好的指标取均值×1.5。可手动调整。"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
                      <Col span={6}><Form.Item {...field} name={[field.name, 'severity']} label="严重程度"><Select>{severityOptions.map(opt => <Select.Option key={opt.value} value={opt.value}><Tag color={opt.color}>{opt.label}</Tag></Select.Option>)}</Select></Form.Item></Col>
                      <Col span={6}><Form.Item {...field} name={[field.name, 'solution_tags']} label="方案标签" tooltip="系统自动生成，用于匹配优化建议。可手动调整。"><Select mode="tags" placeholder="输入后回车添加" /></Form.Item></Col>
                    </Row>
                    <Form.Item {...field} name={[field.name, 'root_cause_chain']} label="根因链" tooltip="由 AI 自动生成因果推导链路。可手动调整节点顺序和内容。"><Select mode="tags" placeholder="按因果顺序依次输入，如：成本上升 → 毛利下降 → 利润率低" /></Form.Item>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add({ id: '', name: '', metric: '', operator: 'lt', threshold: 0, severity: 'warning', root_cause_chain: [], solution_tags: [] })} block icon={<PlusOutlined />}>手动添加规则</Button>
              </div>
            )}
          </Form.List>

          <Divider>任务配置（可选）</Divider>
          <Form.List name="tasks">
            {(fields, { add, remove }) => (
              <div className="space-y-4">
                {fields.map((field, index) => (
                  <Card key={field.key} size="small"
                    title={<div className="flex items-center gap-2"><PlayCircleOutlined className="text-blue-400" /><span>任务 {index + 1}</span></div>}
                    extra={<Button type="text" danger size="small" onClick={() => remove(field.name)}>删除</Button>}>
                    <Row gutter={16}>
                      <Col span={12}><Form.Item {...field} name={[field.name, 'task_id']} label="任务标识" rules={[{ required: true, message: '必填' }]}><Input placeholder="如: q1_quality_analysis" /></Form.Item></Col>
                      <Col span={12}><Form.Item {...field} name={[field.name, 'name']} label="任务名称" rules={[{ required: true, message: '必填' }]}><Input placeholder="如: 质量数据分析" /></Form.Item></Col>
                    </Row>
                    <Form.Item {...field} name={[field.name, 'description']} label="任务描述"><Input.TextArea placeholder="任务详细描述" rows={2} /></Form.Item>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item {...field} name={[field.name, 'execution_type']} label="执行类型" rules={[{ required: true, message: '必填' }]}>
                          <Select placeholder="选择执行类型">
                            <Select.Option value="auto"><Tag color="green">自动</Tag></Select.Option>
                            <Select.Option value="semi_auto"><Tag color="orange">半自动</Tag></Select.Option>
                            <Select.Option value="manual"><Tag color="blue">手动</Tag></Select.Option>
                            <Select.Option value="custom_api"><Tag color="purple">自定义API</Tag></Select.Option>
                            <Select.Option value="custom_script"><Tag color="cyan">自定义脚本</Tag></Select.Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'duration_days']} label="执行天数" rules={[{ required: true, message: '必填' }]}><InputNumber min={1} style={{ width: '100%' }} placeholder="3" /></Form.Item></Col>
                      <Col span={8}><Form.Item {...field} name={[field.name, 'trigger_rules']} label="触发规则"><Select mode="tags" placeholder="输入规则ID" /></Form.Item></Col>
                    </Row>
                    <Form.Item {...field} name={[field.name, 'dependencies']} label="依赖任务"><Select mode="tags" placeholder="输入依赖的任务ID" /></Form.Item>
                    <Form.Item noStyle shouldUpdate={(prev, cur) => prev?.tasks?.[field.name]?.execution_type !== cur?.tasks?.[field.name]?.execution_type}>
                      {({ getFieldValue }) => {
                        const execType = getFieldValue(['tasks', field.name, 'execution_type']);
                        if (execType === 'custom_api') {
                          return (
                            <Card size="small" className="bg-gray-800/30 mt-2">
                              <div className="flex items-center gap-2 mb-3"><CodeOutlined className="text-purple-400" /><span className="text-sm font-medium">API 调用配置</span></div>
                              <Row gutter={16}>
                                <Col span={12}><Form.Item {...field} name={[field.name, 'config', 'api_url']} label="API 地址" rules={[{ required: true }]}><Input placeholder="https://api.example.com/endpoint" /></Form.Item></Col>
                                <Col span={6}><Form.Item {...field} name={[field.name, 'config', 'method']} label="请求方法" initialValue="GET"><Select><Select.Option value="GET">GET</Select.Option><Select.Option value="POST">POST</Select.Option><Select.Option value="PUT">PUT</Select.Option></Select></Form.Item></Col>
                                <Col span={6}><Form.Item {...field} name={[field.name, 'config', 'timeout']} label="超时(秒)" initialValue={30}><InputNumber min={1} max={300} style={{ width: '100%' }} /></Form.Item></Col>
                              </Row>
                              <Form.Item {...field} name={[field.name, 'config', 'headers']} label="请求头（JSON格式）"><Input.TextArea rows={2} placeholder='{"Authorization": "Bearer ${API_TOKEN}"}' /></Form.Item>
                              <Form.Item {...field} name={[field.name, 'config', 'body']} label="请求体（JSON格式）"><Input.TextArea rows={3} placeholder='{"enterprise_id": "${enterprise_id}"}' /></Form.Item>
                            </Card>
                          );
                        } else if (execType === 'custom_script') {
                          return (
                            <Card size="small" className="bg-gray-800/30 mt-2">
                              <div className="flex items-center gap-2 mb-3"><CodeOutlined className="text-cyan-400" /><span className="text-sm font-medium">脚本执行配置</span></div>
                              <Row gutter={16}>
                                <Col span={8}><Form.Item {...field} name={[field.name, 'config', 'script_type']} label="脚本类型" initialValue="python"><Select><Select.Option value="python">Python</Select.Option><Select.Option value="shell">Shell</Select.Option><Select.Option value="javascript">JavaScript</Select.Option></Select></Form.Item></Col>
                                <Col span={8}><Form.Item {...field} name={[field.name, 'config', 'timeout']} label="超时(秒)" initialValue={60}><InputNumber min={1} max={600} style={{ width: '100%' }} /></Form.Item></Col>
                                <Col span={8}><Form.Item {...field} name={[field.name, 'config', 'working_dir']} label="工作目录" initialValue="/tmp"><Input placeholder="/tmp" /></Form.Item></Col>
                              </Row>
                              <Form.Item {...field} name={[field.name, 'config', 'script_content']} label="脚本内容" rules={[{ required: true }]}><Input.TextArea rows={6} placeholder="import json&#10;print(json.dumps({'success': True}))" /></Form.Item>
                              <Form.Item {...field} name={[field.name, 'config', 'env']} label="环境变量（JSON格式）"><Input.TextArea rows={2} placeholder='{"API_KEY": "${API_KEY}"}' /></Form.Item>
                            </Card>
                          );
                        }
                        return null;
                      }}
                    </Form.Item>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add({ task_id: '', name: '', execution_type: 'custom_api', duration_days: 3, dependencies: [], config: {} })} block icon={<PlusOutlined />}>添加任务</Button>
              </div>
            )}
          </Form.List>

          <Divider>数据源配置（可选）</Divider>
          <Card size="small" className="bg-gray-800/30">
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name={['data_source', 'type']} label="数据源类型">
                  <Select placeholder="选择数据源类型">
                    <Select.Option value="manual">手动录入</Select.Option>
                    <Select.Option value="api">API 接口</Select.Option>
                    <Select.Option value="database">数据库</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            <Form.Item noStyle shouldUpdate={(prev, cur) => prev?.data_source?.type !== cur?.data_source?.type}>
              {({ getFieldValue }) => {
                const dsType = getFieldValue(['data_source', 'type']);
                if (dsType === 'api') {
                  return (<><Divider orientation="left" plain className="text-xs">API 配置</Divider>
                    <Row gutter={16}>
                      <Col span={12}><Form.Item name={['data_source', 'api_config', 'base_url']} label="API 基础地址"><Input placeholder="留空则使用系统配置（.env）" /></Form.Item></Col>
                      <Col span={6}><Form.Item name={['data_source', 'api_config', 'auth_type']} label="认证方式"><Select placeholder="选择认证方式"><Select.Option value="none">无需认证</Select.Option><Select.Option value="bearer">Bearer Token</Select.Option><Select.Option value="api_key">API Key</Select.Option></Select></Form.Item></Col>
                      <Col span={6}><Form.Item name={['data_source', 'api_config', 'timeout']} label="超时(秒)"><InputNumber min={1} max={120} style={{ width: '100%' }} placeholder="30" /></Form.Item></Col>
                    </Row></>);
                } else if (dsType === 'database') {
                  return (<><Divider orientation="left" plain className="text-xs">数据库配置</Divider>
                    <Row gutter={16}><Col span={24}><Form.Item name={['data_source', 'database_config', 'connection_string']} label="连接字符串"><Input.Password placeholder="postgresql://user:pass@host:5432/dbname" /></Form.Item></Col></Row>
                    <Row gutter={16}><Col span={24}><Form.Item name={['data_source', 'database_config', 'query_template']} label="查询模板"><Input.TextArea rows={3} placeholder="SELECT metric_name, value FROM metrics WHERE enterprise_id = :enterprise_id" /></Form.Item></Col></Row></>);
                }
                return null;
              }}
            </Form.Item>
          </Card>
        </Form>
      </Modal>
    </div>
  );
}

