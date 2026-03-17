

import { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { Card, Button, Tabs, App, Badge, Spin } from 'antd';
import {
  SettingOutlined, BellOutlined, SafetyOutlined,
  CloudOutlined, SaveOutlined, TeamOutlined, AppstoreAddOutlined, LineChartOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useAppStore } from '@/stores/app-store';
import { customDimensionApi, enterpriseApi, type EnterpriseConfig, type EnterpriseContext } from '@/lib/api';
import type { FormInstance } from 'antd';

// 懒加载各 tab 组件
const GeneralTab = lazy(() => import('./tabs/general-tab'));
const DimensionsTab = lazy(() => import('./tabs/dimensions-tab'));
const BenchmarksTab = lazy(() => import('./tabs/benchmarks-tab'));
const NotificationTab = lazy(() => import('./tabs/notification-tab'));
const IntegrationTab = lazy(() => import('./tabs/integration-tab'));
const SecurityTab = lazy(() => import('./tabs/security-tab'));
const TeamTab = lazy(() => import('./tabs/team-tab'));

const TabLoading = () => <Spin className="w-full py-12 flex justify-center" />;

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
  metrics_config?: any;
  rules_config?: any;
  tasks_config?: any;
  data_source_config?: any;
}

export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab') || 'general';
  const validTabKeys = ['general', 'dimensions', 'benchmarks', 'notification', 'integration', 'security', 'team'];
  const activeTabKey = validTabKeys.includes(tabFromUrl) ? tabFromUrl : 'general';
  const { message } = App.useApp();
  const { currentEnterprise } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [dimensionsLoading, setDimensionsLoading] = useState(false);
  const [allDimensions, setAllDimensions] = useState<DimensionOption[]>([]);
  const [enterpriseConfig, setEnterpriseConfig] = useState<Record<string, unknown>>({});
  const [enterpriseContext, setEnterpriseContext] = useState<Record<string, unknown>>({});
  const generalFormRef = useRef<FormInstance>(null);
  const contextFormRef = useRef<FormInstance>(null);

  const loadDimensions = async () => {
    if (!currentEnterprise?.id) return;
    setDimensionsLoading(true);
    try {
      const res = await customDimensionApi.getAllDimensions(currentEnterprise.id);
      const data = res as unknown as { all_dimensions: DimensionOption[] };
      setAllDimensions(data.all_dimensions || []);
    } catch (error) {
      console.error('Failed to load dimensions:', error);
    } finally {
      setDimensionsLoading(false);
    }
  };

  const loadEnterpriseDetail = async () => {
    if (!currentEnterprise?.id) return;
    try {
      const res = await enterpriseApi.get(currentEnterprise.id) as Record<string, unknown>;
      setEnterpriseConfig((res?.config as Record<string, unknown>) ?? {});
      setEnterpriseContext({
        industry: res?.industry,
        scale: res?.scale,
        team_size: res?.team_size,
        budget_level: res?.budget_level,
        data_quality: res?.data_quality,
      });
    } catch (e) {
      setEnterpriseConfig({});
      setEnterpriseContext({});
    }
  };

  useEffect(() => {
    loadDimensions();
  }, [currentEnterprise?.id]);

  useEffect(() => {
    loadEnterpriseDetail();
  }, [currentEnterprise?.id]);

  const handleSave = async () => {
    if (!currentEnterprise?.id) {
      message.warning('请先选择企业');
      return;
    }
    setLoading(true);
    try {
      // 保存通用配置
      const configValues = generalFormRef.current?.getFieldsValue() as EnterpriseConfig | undefined;
      if (configValues) {
        await enterpriseApi.updateConfig(currentEnterprise.id, configValues);
      }
      // 保存企业上下文
      const contextValues = contextFormRef.current?.getFieldsValue() as EnterpriseContext | undefined;
      if (contextValues) {
        await enterpriseApi.updateContext(currentEnterprise.id, contextValues);
      }
      await loadEnterpriseDetail();
      message.success('设置已保存');
    } catch (e) {
      message.error('保存失败');
    } finally {
      setLoading(false);
    }
  };

  const tabItems = [
    {
      key: 'general',
      label: <span className="flex items-center gap-2"><SettingOutlined />通用设置</span>,
      children: (
        <GeneralTab
          currentEnterprise={currentEnterprise}
          enabledCount={allDimensions.filter(d => d.enabled).length}
          totalCount={allDimensions.length}
          config={enterpriseConfig}
          context={enterpriseContext}
          formRef={generalFormRef}
          contextFormRef={contextFormRef}
        />
      ),
    },
    {
      key: 'dimensions',
      label: (
        <span className="flex items-center gap-2">
          <AppstoreAddOutlined />诊断维度
          <Badge count={allDimensions.length} size="small" style={{ backgroundColor: '#52c41a' }} />
        </span>
      ),
      children: (
        <DimensionsTab
          allDimensions={allDimensions}
          dimensionsLoading={dimensionsLoading}
          loadDimensions={loadDimensions}
          currentEnterprise={currentEnterprise}
        />
      ),
    },
    {
      key: 'benchmarks',
      label: <span className="flex items-center gap-2"><LineChartOutlined />行业基准</span>,
      children: <BenchmarksTab />,
    },
    {
      key: 'notification',
      label: <span className="flex items-center gap-2"><BellOutlined />通知设置</span>,
      children: <NotificationTab />,
    },
    {
      key: 'integration',
      label: <span className="flex items-center gap-2"><CloudOutlined />数据集成</span>,
      children: <IntegrationTab />,
    },
    {
      key: 'security',
      label: <span className="flex items-center gap-2"><SafetyOutlined />安全设置</span>,
      children: <SecurityTab />,
    },
    {
      key: 'team',
      label: <span className="flex items-center gap-2"><TeamOutlined />团队管理</span>,
      children: <TeamTab />,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center text-lg shadow-lg">
              <SettingOutlined />
            </span>
            系统设置
          </h1>
          <p className="text-gray-400 mt-2 text-sm">配置诊断参数、通知选项、数据集成和安全设置</p>
        </div>
        <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave}>保存设置</Button>
      </div>
      <Card>
        <Suspense fallback={<TabLoading />}>
          <Tabs
            activeKey={activeTabKey}
            onChange={(key) => setSearchParams({ tab: key })}
            items={tabItems}
          />
        </Suspense>
      </Card>
    </div>
  );
}
