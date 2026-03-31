import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/layout/sidebar';

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-[#F0F1F9]">
      <Sidebar />
      <div className="pt-16 min-h-screen flex flex-col">
        {/* <Header /> */}
        <main className="flex-1 px-5 pt-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

