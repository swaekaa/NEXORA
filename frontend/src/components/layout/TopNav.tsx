
import { NavLink, useLocation } from 'react-router-dom';

export default function TopNav() {
  const location = useLocation();

  const getNavColor = (path: string) => {
    switch (path) {
      case '/office': return 'border-[#5BC0DE] text-[#333333] shadow-[3px_3px_0_0_#5BC0DE] bg-[#5BC0DE]/10';
      case '/deals': return 'border-[#5CB85C] text-[#333333] shadow-[3px_3px_0_0_#5CB85C] bg-[#5CB85C]/10';
      case '/agents': return 'border-[#F0AD4E] text-[#333333] shadow-[3px_3px_0_0_#F0AD4E] bg-[#F0AD4E]/10';
      case '/tools': return 'border-[#FF69B4] text-[#333333] shadow-[3px_3px_0_0_#FF69B4] bg-[#FF69B4]/10';
      case '/policies': return 'border-[#9B59B6] text-[#333333] shadow-[3px_3px_0_0_#9B59B6] bg-[#9B59B6]/10';
      case '/audit': return 'border-[#D9534F] text-[#333333] shadow-[3px_3px_0_0_#D9534F] bg-[#D9534F]/10';
      default: return 'border-[#333333] text-[#333333] shadow-[3px_3px_0_0_#333333] bg-[#333333]/10';
    }
  };

  const navLinkClass = (path: string) => ({ isActive }: { isActive: boolean }) => {
    const isNegotiation = location.pathname.startsWith('/negotiations');
    const actuallyActive = isActive || (path === '/office' && isNegotiation);
    
    return `h-9 px-5 mx-1 flex items-center border-[2px] font-bold uppercase tracking-widest text-[11px] transition-all duration-200 ${
      actuallyActive
        ? `${getNavColor(path)}`
        : 'border-transparent text-[#888888] hover:text-[#111111] hover:bg-black/5'
    }`;
  };

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
          <NavLink to="/tools" className={navLinkClass('/tools')}>
            Tools
          </NavLink>
          <NavLink to="/policies" className={navLinkClass('/policies')}>
            Policies
          </NavLink>
          <NavLink to="/audit" className={navLinkClass('/audit')}>
            Audit Trail
          </NavLink>
        </div>
      </div>

      {/* GITHUB LINK */}
      <div className="flex items-center h-full">
        <a 
          href="https://github.com/swaekaa/NEXORA" 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-2 h-9 px-4 border-[2px] border-[#111111] bg-[#FFFDF7] text-[#111111] font-bold uppercase tracking-widest text-[11px] shadow-[3px_3px_0_0_#111111] hover:translate-y-[1px] hover:shadow-[2px_2px_0_0_#111111] active:translate-y-[3px] active:shadow-none transition-all"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true">
            <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
          </svg>
          GITHUB
        </a>
      </div>
    </div>
  );
}
