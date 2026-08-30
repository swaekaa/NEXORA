import React from 'react';
import { NavLink } from 'react-router-dom';

export default function TopNav() {
  const getNavColor = (path: string) => {
    switch (path) {
      case '/office': return 'border-[#5BC0DE] text-[#333333] shadow-[3px_3px_0_0_#5BC0DE] bg-[#5BC0DE]/10';
      case '/deals': return 'border-[#5CB85C] text-[#333333] shadow-[3px_3px_0_0_#5CB85C] bg-[#5CB85C]/10';
      case '/agents': return 'border-[#F0AD4E] text-[#333333] shadow-[3px_3px_0_0_#F0AD4E] bg-[#F0AD4E]/10';
      case '/policies': return 'border-[#9B59B6] text-[#333333] shadow-[3px_3px_0_0_#9B59B6] bg-[#9B59B6]/10';
      case '/audit': return 'border-[#D9534F] text-[#333333] shadow-[3px_3px_0_0_#D9534F] bg-[#D9534F]/10';
      default: return 'border-[#333333] text-[#333333] shadow-[3px_3px_0_0_#333333] bg-[#333333]/10';
    }
  };

  const navLinkClass = (path: string) => ({ isActive }: { isActive: boolean }) =>
    `h-9 px-5 mx-1 flex items-center border-[2px] font-bold uppercase tracking-widest text-[11px] transition-all duration-200 ${
      isActive
        ? `${getNavColor(path)}`
        : 'border-transparent text-[#888888] hover:text-[#111111] hover:bg-black/5'
    }`;

  return (
    <div className="absolute top-0 left-0 right-0 h-16 z-50 flex items-center justify-between px-6 bg-[#EAE8DD] border-b-[3px] border-[#111111] font-sans shadow-sm">
      <div className="flex items-center gap-10 h-full">
        {/* LOGO */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[#D9534F] text-[#FFFDF7] flex items-center justify-center font-black text-2xl leading-none border-2 border-[#111111] shadow-[2px_2px_0_0_rgba(17,17,17,1)] -rotate-3 hover:rotate-0 transition-transform cursor-default">N</div>
          <div className="flex flex-col justify-center">
            <span className="font-black text-2xl tracking-tighter text-[#111111] leading-none uppercase">NEXORA</span>
            <span className="text-[9px] text-[#5BC0DE] font-bold tracking-[0.2em] uppercase leading-none mt-1">Autonomous</span>
          </div>
        </div>
        
        {/* NAVIGATION */}
        <div className="flex items-center h-full pt-1">
          <NavLink to="/office" className={navLinkClass('/office')}>
            Office
          </NavLink>
          <NavLink to="/deals" className={navLinkClass('/deals')}>
            Deals
          </NavLink>
          <NavLink to="/agents" className={navLinkClass('/agents')}>
            Agents
          </NavLink>
          <NavLink to="/policies" className={navLinkClass('/policies')}>
            Policies
          </NavLink>
          <NavLink to="/audit" className={navLinkClass('/audit')}>
            Audit Trail
          </NavLink>
        </div>
      </div>
      {/* STATUS BADGE */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3 bg-[#111111] px-4 py-1.5 border-2 border-[#111111] shadow-[3px_3px_0_0_rgba(92,184,92,0.4)]">
           <div className="w-2.5 h-2.5 rounded-full bg-[#5CB85C] animate-pulse shadow-[0_0_8px_#5CB85C]"></div>
           <span className="text-[#5CB85C] font-mono text-[10px] font-bold tracking-widest uppercase">NEXUS ACTIVE</span>
        </div>
      </div>
    </div>
  );
}
