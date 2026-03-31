

import { Menu, Avatar, Space } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  FileSearchOutlined,
  BulbOutlined,
  RocketOutlined,
  LineChartOutlined,
  BookOutlined,
  SettingOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useAppStore } from '@/stores/app-store';

const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/diagnosis/reports',
    icon: <FileSearchOutlined />,
    label: '诊断历史',
  },
  {
    key: '/solutions',
    icon: <BulbOutlined />,
    label: '方案管理',
  },
  {
    key: '/execution',
    icon: <RocketOutlined />,
    label: '任务执行',
  },
  {
    key: '/tracking',
    icon: <LineChartOutlined />,
    label: '效果追踪',
  },
  {
    key: '/tracking/cases',
    icon: <BookOutlined />,
    label: '案例库',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '系统设置',
  },
];

export function Sidebar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const currentEnterprise = useAppStore((s) => s.currentEnterprise);

  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-[#F0F1F9] border-b border-border z-50 flex items-center px-4">
      <Menu
        mode="horizontal"
        theme="light"
        selectedKeys={[pathname]}
        items={menuItems}
        className="border-none bg-transparent flex-1 flex items-center"
        onClick={({ key }) => navigate(key)}
      />

      <Space className="select-none">
        <Avatar
          className="bg-gradient-to-br from-cyan-500 to-emerald-500"
          icon={<UserOutlined />}
        />
        <span className="font-medium" style={{ color: '#303133' }}>
          {currentEnterprise?.name || '请先通过企业管理后台打开'}
        </span>
      </Space>
    </header>
  );
}
