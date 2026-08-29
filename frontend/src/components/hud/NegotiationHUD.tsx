import React from 'react';
import { useGame } from '../../game/GameContext';

export const NegotiationHUD: React.FC = () => {
  const { state } = useGame();

  const currentOffer = state.currentOffer ? `₹${Number(state.currentOffer.unitPrice).toLocaleString('en-IN')}` : '---';
  const quantity = state.currentOffer?.quantity ? `${state.currentOffer.quantity} UNITS` : '';
  const total = state.currentOffer?.total ? `TOTAL: ₹${Number(state.currentOffer.total).toLocaleString('en-IN')}` : '';

  return (
    <div className="absolute inset-0 pointer-events-none p-8">
      {/* Top Right: Deal Status */}
      <div className="absolute top-8 right-8 flex flex-col items-end gap-2">
        <div className="flex items-center gap-4 text-sm font-bold uppercase tracking-widest text-[#333333]">
          <span className={`w-3 h-3 border border-[#333333] ${state.dealStatus === 'complete' ? 'bg-[#5CB85C]' : state.dealStatus === 'failed' ? 'bg-[#D9534F]' : 'bg-[#5BC0DE] animate-pulse'}`}></span>
          <span>{state.dealStatus === 'complete' ? 'DEAL CLOSED' : state.dealStatus === 'failed' ? 'DEAL FAILED' : 'NEGOTIATING'}</span>
        </div>
      </div>

      {/* Top Right: Current Offer */}
      <div className="absolute top-20 right-8 flex flex-col items-end bg-[#EAE8DD]/90 backdrop-blur-sm p-6 border-2 border-[#111111] shadow-[4px_4px_0_0_rgba(17,17,17,1)]">
        <div className="text-[#888888] text-sm font-bold tracking-widest uppercase mb-2">CURRENT OFFER</div>
        <div className="text-5xl font-bold text-[#5BC0DE] tracking-tight mb-2" style={{ fontFamily: 'sans-serif' }}>
          {currentOffer}
        </div>
        {quantity && <div className="text-[#333333] text-sm font-bold uppercase mt-2 tracking-widest">{quantity}</div>}
        {total && <div className="text-[#333333] text-lg font-extrabold uppercase mt-2 tracking-widest">{total}</div>}
      </div>
    </div>
  );
};

