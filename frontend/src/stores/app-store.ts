import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Enterprise {
  id: string;
  name: string;
  industry: string | null;
  scale: string | null;
}

interface AppState {
  // 当前企业
  currentEnterprise: Enterprise | null;
  setCurrentEnterprise: (enterprise: Enterprise | null) => void;
  
  // 认证
  token: string | null;
  setToken: (token: string | null) => void;
  
  // UI状态
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentEnterprise: null,
      setCurrentEnterprise: (enterprise) => set({ currentEnterprise: enterprise }),
      
      token: null,
      setToken: (token) => set({ token }),
      
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
    }),
    {
      name: 'ops-brain-storage',
      partialize: (state) => ({
        currentEnterprise: state.currentEnterprise,
        token: state.token,
      }),
    }
  )
);
