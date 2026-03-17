

import { Card, Form, Input, Select, Tag } from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';

export default function IntegrationTab() {
  return (
    <div className="space-y-4">
      <Card title="数据源配置" size="small">
        <div className="space-y-4">
          {[
            { icon: 'text-blue-400', name: 'CRM系统', desc: 'Salesforce / 用友CRM', connected: true },
            { icon: 'text-purple-400', name: '营销平台', desc: '广告投放数据', connected: true },
            { icon: 'text-amber-400', name: 'ERP系统', desc: '订单/库存数据', connected: false },
            { icon: 'text-emerald-400', name: '客服系统', desc: '工单/满意度数据', connected: false },
          ].map((item) => (
            <div key={item.name} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
              <div className="flex items-center gap-3">
                <DatabaseOutlined className={`text-2xl ${item.icon}`} />
                <div>
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs text-gray-500">{item.desc}</div>
                </div>
              </div>
              <Tag color={item.connected ? 'green' : 'default'}>{item.connected ? '已连接' : '未连接'}</Tag>
            </div>
          ))}
        </div>
      </Card>
      <Card title="API配置" size="small">
        <Form layout="vertical">
          <Form.Item label="API密钥"><Input.Password defaultValue="sk-xxxxx-xxxxx-xxxxx" /></Form.Item>
          <Form.Item label="Webhook URL"><Input placeholder="https://your-webhook-url.com/callback" /></Form.Item>
          <Form.Item label="数据同步频率">
            <Select defaultValue="hourly">
              <Select.Option value="realtime">实时</Select.Option>
              <Select.Option value="hourly">每小时</Select.Option>
              <Select.Option value="daily">每日</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}


