

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, theme, App } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: theme.darkAlgorithm,
          token: {
            colorPrimary: '#3b82f6',
            colorBgContainer: '#1a2234',
            colorBgElevated: '#232f46',
            colorBorder: '#2d3a52',
            colorText: '#f1f5f9',
            colorTextSecondary: '#94a3b8',
            borderRadius: 8,
          },
          components: {
            Card: {
              colorBgContainer: '#1a2234',
            },
            Button: {
              colorBgContainer: '#1a2234',
            },
            Menu: {
              colorBgContainer: '#111827',
              colorItemBgSelected: 'rgba(59, 130, 246, 0.15)',
            },
          },
        }}
      >
        <App>{children}</App>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

// 导出 useApp hook，用于在组件中获取 message/notification/modal 实例
export { App };
