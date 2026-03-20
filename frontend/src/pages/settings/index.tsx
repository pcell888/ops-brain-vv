

import { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { Card, Button, Tabs, App, Spin } from 'antd';
import { SettingOutlined, SaveOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useAppStore } from '@/stores/app-store';
import { enterpriseApi, type EnterpriseConfig } from '@/lib/api';
import type { FormInstance } from 'antd';

const GeneralTab = lazy(() => import('./tabs/general-tab'));

const TabLoading = () => <Spin className="w-full py-12 flex justify-center" />;

export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab') || 'general';
  const validTabKeys = ['general'];
  const activeTabKey = validTabKeys.includes(tabFromUrl) ? tabFromUrl : 'general';
  const { message } = App.useApp();
  const { currentEnterprise } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [enterpriseConfig, setEnterpriseConfig] = useState<Record<string, unknown>>({});
  const [enterpriseContext, setEnterpriseContext] = useState<Record<string, unknown>>({});
  const generalFormRef = useRef<FormInstance>(null);

  const loadEnterpriseDetail = async () => {
    if (!currentEnterprise?.id) return;
    try {
      const res = await enterpriseApi.get(currentEnterprise.id) as Record<string, unknown>;
      setEnterpriseConfig((res?.config as Record<string, unknown>) ?? {});
      setEnterpriseContext({
        industry: res?.industry,
        name: res?.name,
      });
    } catch {
      setEnterpriseConfig({});
      setEnterpriseContext({});
    }
  };

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
      const configValues = generalFormRef.current?.getFieldsValue() as EnterpriseConfig | undefined;
      if (configValues) {
        await enterpriseApi.updateConfig(currentEnterprise.id, configValues);
      }
      await loadEnterpriseDetail();
      message.success('设置已保存');
    } catch {
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
          config={enterpriseConfig}
          context={enterpriseContext}
          formRef={generalFormRef}
        />
      ),
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
          <p className="text-gray-400 mt-2 text-sm">配置企业信息和诊断参数</p>
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
