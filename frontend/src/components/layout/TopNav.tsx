import React from 'react';
import { NavLink } from 'react-router-dom';

export default function TopNav() {
  return (
    <div className="absolute top-0 left-0 right-0 h-16 z-50 flex items-center justify-between px-8 bg-[#EAE8DD] border-b-2 border-[#333333] font-sans text-sm font-medium tracking-wide shadow-sm">
      <div className="flex items-center gap-12 h-full">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#2A2F35] text-white flex items-center justify-center font-bold text-lg leading-none">N</div>
          <div className="flex items-baseline gap-2">
            <span className="font-bold text-lg tracking-widest text-[#2A2F35]">NEXORA</span>
            <span className="text-[#888888] text-xs tracking-widest uppercase">Agent Office</span>
          </div>
        </div>
        
        <div className="flex items-center gap-8 h-full pt-1">
          <NavLink to="/office" className={({ isActive }) => `h-full flex items-center border-b-4 transition-colors ${isActive ? 'border-[#D9534F] text-[#2A2F35]' : 'border-transparent text-[#888888] hover:text-[#2A2F35]'}`}>
            Office
          </NavLink>
          <NavLink to="/merchant" className={({ isActive }) => `h-full flex items-center border-b-4 transition-colors ${isActive ? 'border-[#D9534F] text-[#2A2F35]' : 'border-transparent text-[#888888] hover:text-[#2A2F35]'}`}>
            Deals
          </NavLink>
          <NavLink to="/agents" className={({ isActive }) => `h-full flex items-center border-b-4 transition-colors ${isActive ? 'border-[#D9534F] text-[#2A2F35]' : 'border-transparent text-[#888888] hover:text-[#2A2F35]'}`}>
            Agents
          </NavLink>
          <NavLink to="/policies" className={({ isActive }) => `h-full flex items-center border-b-4 transition-colors ${isActive ? 'border-[#D9534F] text-[#2A2F35]' : 'border-transparent text-[#888888] hover:text-[#2A2F35]'}`}>
            Policies
          </NavLink>
        </div>
      </div>

      <div className="flex items-center gap-6 text-[#2A2F35] text-xs font-bold tracking-widest uppercase">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 bg-[#5CB85C] border border-[#2A2F35]"></div>
          SYSTEM ONLINE
        </div>
        <div className="text-[#888888]">
          VERSION 2.0
        </div>
      </div>
    </div>
  );
}
