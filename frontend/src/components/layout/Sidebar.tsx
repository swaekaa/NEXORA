import { NavLink } from 'react-router-dom';
import { MessageSquare, LayoutDashboard, FileText, Activity } from 'lucide-react';

export default function Sidebar() {
  const navItems = [
    { to: '/buyer', icon: <MessageSquare size={20} />, label: 'Buyer Console' },
    { to: '/merchant', icon: <LayoutDashboard size={20} />, label: 'Merchant Dashboard' },
    { to: '/agreements', icon: <FileText size={20} />, label: 'Agreements' },
    { to: '/audit', icon: <Activity size={20} />, label: 'Audit Trail' },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/50 backdrop-blur-md flex flex-col">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-2xl font-bold text-gradient tracking-wider">NEXORA</h1>
        <p className="text-xs text-slate-500 mt-1 uppercase tracking-widest font-semibold">AI Commerce</p>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                isActive 
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-[0_0_15px_rgba(37,99,235,0.05)]' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
              }`
            }
          >
            {item.icon}
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-6 border-t border-slate-800 text-xs text-slate-500">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
          <span>System Online</span>
        </div>
        <p>Deterministic Engine: Active</p>
      </div>
    </aside>
  );
}
