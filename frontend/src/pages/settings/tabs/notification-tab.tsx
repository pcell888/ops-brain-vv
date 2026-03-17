

import { Card, Form, Switch, Select, Input, Divider } from 'antd';

export default function NotificationTab() {
  return (
    <Card size="small">
      <Form layout="vertical">
        <Form.Item label="诊断完成通知">
          <Switch defaultChecked />
          <span className="ml-3 text-gray-400 text-sm">诊断任务完成时发送通知</span>
        </Form.Item>
        <Form.Item label="异常预警通知">
          <Switch defaultChecked />
          <span className="ml-3 text-gray-400 text-sm">发现严重异常指标时发送预警</span>
        </Form.Item>
        <Form.Item label="方案推荐通知">
          <Switch defaultChecked />
          <span className="ml-3 text-gray-400 text-sm">新方案生成时发送通知</span>
        </Form.Item>
        <Form.Item label="任务到期提醒">
          <Switch defaultChecked />
          <span className="ml-3 text-gray-400 text-sm">执行任务即将到期时提醒</span>
        </Form.Item>
        <Form.Item label="追踪报告通知">
          <Switch defaultChecked />
          <span className="ml-3 text-gray-400 text-sm">复盘报告生成时发送通知</span>
        </Form.Item>
        <Divider />
        <Form.Item label="通知方式">
          <Select mode="multiple" defaultValue={['system', 'email']}>
            <Select.Option value="system">系统消息</Select.Option>
            <Select.Option value="email">邮件</Select.Option>
            <Select.Option value="sms">短信</Select.Option>
            <Select.Option value="webhook">Webhook</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item label="通知邮箱">
          <Input placeholder="admin@example.com" />
        </Form.Item>
      </Form>
    </Card>
  );
}


