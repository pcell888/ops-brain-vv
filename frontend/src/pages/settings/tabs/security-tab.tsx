

import { Card, Form, Switch, Select, Input } from 'antd';

export default function SecurityTab() {
  return (
    <div className="space-y-4">
      <Card title="访问控制" size="small">
        <Form layout="vertical">
          <Form.Item label="双因素认证"><Switch /><span className="ml-3 text-gray-400 text-sm">启用双因素身份验证</span></Form.Item>
          <Form.Item label="会话超时">
            <Select defaultValue="30">
              <Select.Option value="15">15分钟</Select.Option><Select.Option value="30">30分钟</Select.Option>
              <Select.Option value="60">1小时</Select.Option><Select.Option value="120">2小时</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="IP白名单"><Input.TextArea placeholder="每行一个IP地址，留空表示不限制" rows={3} /></Form.Item>
        </Form>
      </Card>
      <Card title="数据安全" size="small">
        <Form layout="vertical">
          <Form.Item label="数据加密"><Switch defaultChecked /><span className="ml-3 text-gray-400 text-sm">敏感数据传输加密</span></Form.Item>
          <Form.Item label="数据脱敏"><Switch defaultChecked /><span className="ml-3 text-gray-400 text-sm">日志和报告中脱敏处理</span></Form.Item>
          <Form.Item label="数据保留期限">
            <Select defaultValue="365">
              <Select.Option value="90">90天</Select.Option><Select.Option value="180">180天</Select.Option>
              <Select.Option value="365">1年</Select.Option><Select.Option value="730">2年</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Card>
      <Card title="审计日志" size="small">
        <Form layout="vertical">
          <Form.Item label="操作日志"><Switch defaultChecked /><span className="ml-3 text-gray-400 text-sm">记录所有操作行为</span></Form.Item>
          <Form.Item label="登录日志"><Switch defaultChecked /><span className="ml-3 text-gray-400 text-sm">记录登录/登出事件</span></Form.Item>
        </Form>
      </Card>
    </div>
  );
}


