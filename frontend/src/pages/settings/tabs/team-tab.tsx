

import { Card, Button, Tag } from 'antd';
import { UserOutlined } from '@ant-design/icons';

export default function TeamTab() {
  const members = [
    { name: '管理员', email: 'admin@example.com', role: '管理员', roleColor: 'gold', iconColor: 'text-blue-400', bgColor: 'bg-blue-500/20' },
    { name: '运营经理', email: 'ops@example.com', role: '编辑', roleColor: 'blue', iconColor: 'text-green-400', bgColor: 'bg-green-500/20' },
    { name: '数据分析师', email: 'analyst@example.com', role: '只读', roleColor: 'default', iconColor: 'text-purple-400', bgColor: 'bg-purple-500/20' },
  ];

  return (
    <div className="space-y-4">
      <Card title="团队成员" size="small" extra={<Button type="primary" size="small" icon={<UserOutlined />}>邀请成员</Button>}>
        <div className="space-y-3">
          {members.map((m) => (
            <div key={m.email} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full ${m.bgColor} flex items-center justify-center`}>
                  <UserOutlined className={m.iconColor} />
                </div>
                <div>
                  <div className="font-medium">{m.name}</div>
                  <div className="text-xs text-gray-500">{m.email}</div>
                </div>
              </div>
              <Tag style={{ backgroundColor: m.roleColor === 'gold' ? 'rgba(245, 158, 11, 0.2)' : m.roleColor === 'blue' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(107, 114, 128, 0.2)', color: m.roleColor === 'gold' ? '#f59e0b' : m.roleColor === 'blue' ? '#3b82f6' : '#6b7280', border: 'none' }}>{m.role}</Tag>
            </div>
          ))}
        </div>
      </Card>
      <Card title="角色权限" size="small">
        <div className="space-y-2 text-sm text-gray-400">
          <div className="flex items-center gap-2"><Tag style={{ backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', border: 'none' }}>管理员</Tag><span>拥有所有权限，可管理团队成员和系统设置</span></div>
          <div className="flex items-center gap-2"><Tag style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6', border: 'none' }}>编辑</Tag><span>可执行诊断、生成方案、管理执行计划</span></div>
          <div className="flex items-center gap-2"><Tag style={{ backgroundColor: 'rgba(107, 114, 128, 0.2)', color: '#6b7280', border: 'none' }}>只读</Tag><span>仅可查看诊断报告和方案，不可执行操作</span></div>
        </div>
      </Card>
    </div>
  );
}


