
import { Outlet } from 'react-router-dom';
import TopNav from './TopNav';

export default function AppShell() {
  return (
    <div className="relative w-screen h-screen bg-[#EFEBE1] overflow-hidden text-[#333333] font-pixel selection:bg-[#5BC0DE]/30">
      <TopNav />
      <div className="absolute inset-0">
        <Outlet />
      </div>
    </div>
  );
}
