

import { Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  FileSearchOutlined,
  BulbOutlined,
  RocketOutlined,
  LineChartOutlined,
  BookOutlined,
  SettingOutlined,
} from '@ant-design/icons';

const menuItems = [
  {
    key: 'diagnosis',
    label: '智能诊断',
    type: 'group' as const,
    children: [
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
    ],
  },
  {
    key: 'solution',
    label: '优化方案',
    type: 'group' as const,
    children: [
      {
        key: '/solutions',
        icon: <BulbOutlined />,
        label: '方案管理',
      },
    ],
  },
  {
    key: 'execution',
    label: '执行管理',
    type: 'group' as const,
    children: [
      {
        key: '/execution',
        icon: <RocketOutlined />,
        label: '任务执行',
      },
    ],
  },
  {
    key: 'tracking',
    label: '效果分析',
    type: 'group' as const,
    children: [
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
    ],
  },
  {
    key: 'settings',
    label: '系统',
    type: 'group' as const,
    children: [
      {
        key: '/settings',
        icon: <SettingOutlined />,
        label: '系统设置',
      },
    ],
  },
];

export function Sidebar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <aside className="fixed left-0 top-0 w-[200px] h-screen bg-[#111827] border-r border-[#2d3a52] z-50">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-5 border-b border-[#2d3a52]">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-base shadow-lg">
          🧠
        </div>
        <span className="text-base font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
          运营AI中心
        </span>
      </div>

      {/* Menu */}
      <Menu
        mode="inline"
        theme="dark"
        selectedKeys={[pathname]}
        items={menuItems}
        className="border-none bg-transparent mt-2"
        onClick={({ key }) => navigate(key)}
      />
    </aside>
  );
}
