import React from 'react';
import { useGame } from '../../game/GameContext';

export const NegotiationHUD: React.FC = () => {
  const { state } = useGame();

  const currentOffer = state.currentOffer ? `₹${Number(state.currentOffer.unitPrice).toLocaleString('en-IN')}` : '---';

  return (
    <div className="absolute inset-0 pointer-events-none p-8">
      {/* Top Right: Deal Status */}
      <div className="absolute top-20 right-8 flex flex-col items-end gap-2">
        <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-widest text-[#333333]">
          <span className="w-2 h-2 bg-[#5BC0DE] border border-[#333333]"></span>
          <span>DEAL CLOSED</span>
          <span className="text-[#888888]">DEAL #NX-0042</span>
        </div>
      </div>

      {/* Top Right: Current Offer */}
      <div className="absolute top-32 right-8 flex flex-col items-end">
        <div className="text-[#888888] text-xs font-bold tracking-widest uppercase mb-1">CURRENT OFFER</div>
        <div className="text-4xl font-bold text-[#5BC0DE] tracking-tight" style={{ fontFamily: 'sans-serif' }}>
          {currentOffer}
        </div>
        <div className="text-[#888888] text-[10px] uppercase mt-1 tracking-widest">per month / 12 months</div>
        
        <div className="flex gap-2 mt-4 pointer-events-auto">
          <button className="pixel-button px-3 py-1 bg-[#EAE8DD] hover:bg-[#333333] hover:text-[#EAE8DD]">+</button>
          <button className="pixel-button px-4 py-1 bg-[#EAE8DD] hover:bg-[#333333] hover:text-[#EAE8DD] text-xs font-bold tracking-widest uppercase">RESET</button>
          <button className="pixel-button px-3 py-1 bg-[#EAE8DD] hover:bg-[#333333] hover:text-[#EAE8DD]">-</button>
        </div>
      </div>
    </div>
  );
};
