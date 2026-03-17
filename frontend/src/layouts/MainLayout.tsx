import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-[#0a0e17]">
      <Sidebar />
      <div className="ml-[200px] min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 p-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

