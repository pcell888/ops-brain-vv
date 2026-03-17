import { useState, useEffect } from 'react';
import {
  Card, Form, Input, Select, Button, App, Table, Space, Modal, InputNumber, Popconfirm,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  industryBenchmarkApi,
  type IndustryBenchmarkItem,
  type IndustryBenchmarkCreateBody,
} from '@/lib/api';
import { INDUSTRY_OPTIONS } from '@/lib/constants';

export default function BenchmarksTab() {
  const { message } = App.useApp();
  const [items, setItems] = useState<IndustryBenchmarkItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [industryFilter, setIndustryFilter] = useState<string | undefined>(undefined);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<IndustryBenchmarkItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<IndustryBenchmarkCreateBody & { id?: string }>();

  const loadList = async () => {
    setLoading(true);
    try {
      const res = await industryBenchmarkApi.list(industryFilter);
      setItems(res.items ?? []);
      setTotal(res.total ?? 0);
    } catch (e) {
      message.error('加载行业基准列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList();
  }, [industryFilter]);

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({
      industry: 'general',
      period: '2024-Q1',
    });
    setModalOpen(true);
  };

  const openEdit = (record: IndustryBenchmarkItem) => {
    setEditingRecord(record);
    form.setFieldsValue({
      id: record.id,
      industry: record.industry,
      metric_name: record.metric_name,
      metric_display_name: record.metric_display_name ?? undefined,
      period: record.period,
      avg_value: record.avg_value ?? undefined,
      median_value: record.median_value ?? undefined,
      excellent_value: record.excellent_value ?? undefined,
      sample_size: record.sample_size ?? undefined,
      source: record.source ?? undefined,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      if (editingRecord) {
        await industryBenchmarkApi.update(editingRecord.id, {
          industry: values.industry,
          metric_name: values.metric_name,
          metric_display_name: values.metric_display_name,
          period: values.period,
          avg_value: values.avg_value,
          median_value: values.median_value,
          excellent_value: values.excellent_value,
          sample_size: values.sample_size,
          source: values.source,
        });
        message.success('更新成功');
      } else {
        await industryBenchmarkApi.create({
          industry: values.industry,
          metric_name: values.metric_name,
          metric_display_name: values.metric_display_name,
          period: values.period,
          avg_value: values.avg_value,
          median_value: values.median_value,
          excellent_value: values.excellent_value,
          sample_size: values.sample_size,
          source: values.source,
        });
        message.success('新增成功');
      }
      setModalOpen(false);
      loadList();
    } catch (e) {
      if (e && typeof (e as Error).message === 'string' && (e as Error).message.includes('required')) {
        return;
      }
      message.error(editingRecord ? '更新失败' : '新增失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await industryBenchmarkApi.delete(id);
      message.success('已删除');
      loadList();
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<IndustryBenchmarkItem> = [
    { title: '行业', dataIndex: 'industry', key: 'industry', width: 100, render: (v) => INDUSTRY_OPTIONS.find(o => o.value === v)?.label ?? v },
    { title: '指标', dataIndex: 'metric_display_name', key: 'metric_display_name', ellipsis: true, render: (_, record) => record.metric_display_name ?? record.metric_name },
    { title: '指标编码', dataIndex: 'metric_name', key: 'metric_name', width: 140, ellipsis: true },
    { title: '周期', dataIndex: 'period', key: 'period', width: 100 },
    { title: '均值', dataIndex: 'avg_value', key: 'avg_value', width: 90, align: 'right', render: (v) => v != null ? Number(v).toFixed(2) : '-' },
    { title: '中位数', dataIndex: 'median_value', key: 'median_value', width: 90, align: 'right', render: (v) => v != null ? Number(v).toFixed(2) : '-' },
    { title: '优秀值', dataIndex: 'excellent_value', key: 'excellent_value', width: 90, align: 'right', render: (v) => v != null ? Number(v).toFixed(2) : '-' },
    { title: '样本量', dataIndex: 'sample_size', key: 'sample_size', width: 80, align: 'right', render: (v) => v ?? '-' },
    { title: '来源', dataIndex: 'source', key: 'source', width: 100, ellipsis: true, render: (v) => v || '-' },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      align: 'center',
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="text" icon={<EditOutlined />} onClick={() => openEdit(record)} className="hover:bg-blue-500/20" />
          <Popconfirm
            title="确定删除此条行业基准？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" danger icon={<DeleteOutlined />} className="hover:bg-red-500/20" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <Card
        title={<span className="text-base font-semibold">行业基准维护</span>}
        size="small"
        extra={
          <Space>
            <Select
              placeholder="按行业筛选"
              allowClear
              style={{ width: 140 }}
              value={industryFilter ?? undefined}
              onChange={(v) => setIndustryFilter(v ?? undefined)}
              options={[...INDUSTRY_OPTIONS]}
            />
            <Button icon={<ReloadOutlined />} onClick={loadList} loading={loading}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增</Button>
          </Space>
        }
        className="shadow-sm"
      >
        <p className="text-gray-400 text-sm mb-4">
          此处维护的基准数据将用于诊断报告中的「行业基准」对比（如雷达图）。GET /diagnosis/benchmarks 与 企业维度基准 均从此表按行业读取。
        </p>
        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={loading}
          pagination={{ total, pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
          size="small"
          scroll={{ x: 900 }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑行业基准' : '新增行业基准'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width={520}
      >
        <Form form={form} layout="vertical" className="mt-4">
          <Form.Item name="industry" label="行业" rules={[{ required: true, message: '请选择行业' }]}>
            <Select options={[...INDUSTRY_OPTIONS]} placeholder="选择行业" />
          </Form.Item>
          <Form.Item name="metric_name" label="指标编码 (metric_name)" rules={[{ required: true, message: '请输入指标编码' }]}>
            <Input placeholder="如: lead_conversion_rate" disabled={!!editingRecord} />
          </Form.Item>
          <Form.Item name="metric_display_name" label="指标中文名">
            <Input placeholder="如: 线索转化率（可选，不填则从维度配置推断）" />
          </Form.Item>
          <Form.Item name="period" label="统计周期" rules={[{ required: true, message: '请输入周期' }]}>
            <Input placeholder="如: 2024-Q1 或 2024-01" />
          </Form.Item>
          <Form.Item name="avg_value" label="均值（行业平均）">
            <InputNumber className="w-full" placeholder="可选" min={0} />
          </Form.Item>
          <Form.Item name="median_value" label="中位数">
            <InputNumber className="w-full" placeholder="可选" min={0} />
          </Form.Item>
          <Form.Item name="excellent_value" label="优秀值">
            <InputNumber className="w-full" placeholder="可选" min={0} />
          </Form.Item>
          <Form.Item name="sample_size" label="样本量">
            <InputNumber className="w-full" placeholder="可选" min={0} precision={0} />
          </Form.Item>
          <Form.Item name="source" label="数据来源">
            <Input placeholder="可选，如：内部调研、第三方报告" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
