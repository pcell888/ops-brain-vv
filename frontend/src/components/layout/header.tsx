

import { Layout, Dropdown, Avatar, Space, Modal, List, Tag, Spin, message } from 'antd';
import { DownOutlined, UserOutlined, SwapOutlined, BankOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { useAppStore } from '@/stores/app-store';
import { enterpriseApi } from '@/lib/api';

const { Header: AntHeader } = Layout;

interface Enterprise {
  id: string;
  name: string;
  industry: string | null;
  scale: string | null;
}

// scale字段映射为中文
const scaleMap: Record<string, string> = {
  small: '小型企业',
  medium: '中型企业',
  large: '大型企业',
  enterprise: '超大型企业',
};

function getScaleDisplay(scale: string | null): string {
  if (!scale) return '未设置';
  return scaleMap[scale] || scale;
}

export function Header() {
  const { currentEnterprise, setCurrentEnterprise } = useAppStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [loading, setLoading] = useState(false);

  // 加载企业列表
  useEffect(() => {
    const loadEnterprises = async () => {
      try {
        setLoading(true);
        const response = await enterpriseApi.list() as { enterprises: Enterprise[]; total: number };
        setEnterprises(response.enterprises || []);
        
        const current = useAppStore.getState().currentEnterprise;
        
        if (current) {
          // 如果已有选中企业，从服务器数据中查找并更新（确保数据是最新的）
          const updatedEnterprise = response.enterprises?.find(e => e.id === current.id);
          if (updatedEnterprise) {
            setCurrentEnterprise(updatedEnterprise);
          } else if (response.enterprises && response.enterprises.length > 0) {
            // 如果当前企业不存在，选择第一个
            setCurrentEnterprise(response.enterprises[0]);
          }
        } else if (response.enterprises && response.enterprises.length > 0) {
          // 如果没有选中企业，自动选择第一个
          setCurrentEnterprise(response.enterprises[0]);
        }
      } catch (error) {
        console.error('加载企业列表失败:', error);
        message.error('加载企业列表失败');
      } finally {
        setLoading(false);
      }
    };
    
    loadEnterprises();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 处理企业切换
  const handleEnterpriseSelect = (enterprise: Enterprise) => {
    setCurrentEnterprise(enterprise);
    setIsModalOpen(false);
  };

  // 下拉菜单项
  const menuItems = [
    { 
      key: 'switch', 
      label: '切换企业', 
      icon: <SwapOutlined />,
      onClick: () => setIsModalOpen(true),
    },
  ];

  return (
    <>
      <AntHeader className="bg-transparent px-6 flex items-center justify-end h-12">
        <Dropdown menu={{ items: menuItems }}>
          <Space className="cursor-pointer hover:opacity-80 transition-opacity">
            <Avatar
              className="bg-gradient-to-br from-cyan-500 to-emerald-500"
              icon={<UserOutlined />}
            />
            <span className="text-primary font-medium">
              {currentEnterprise?.name || '请选择企业'}
            </span>
            <DownOutlined className="text-secondary text-xs" />
          </Space>
        </Dropdown>
      </AntHeader>

      {/* 企业选择弹窗 */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <BankOutlined className="text-blue-500" />
            <span>选择企业</span>
          </div>
        }
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width={500}
      >
        {loading ? (
          <div className="flex justify-center py-8">
            <Spin />
          </div>
        ) : (
          <List
            dataSource={enterprises}
            renderItem={(item) => (
              <List.Item
                className={`cursor-pointer rounded-lg px-4 my-1 transition-all hover:bg-blue-500/10 ${
                  currentEnterprise?.id === item.id ? 'bg-blue-500/15 border border-blue-500/30' : ''
                }`}
                onClick={() => handleEnterpriseSelect(item)}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar 
                      className="bg-gradient-to-br from-blue-500 to-purple-500"
                      icon={<BankOutlined />} 
                    />
                  }
                  title={
                    <div className="flex items-center gap-2">
                      <span className="text-primary">{item.name}</span>
                      {currentEnterprise?.id === item.id && (
                        <Tag color="blue" className="!m-0">当前</Tag>
                      )}
                    </div>
                  }
                  description={
                    <span className="text-secondary">
                      {item.industry || '未设置'} · {getScaleDisplay(item.scale)}
                    </span>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </>
  );
}
