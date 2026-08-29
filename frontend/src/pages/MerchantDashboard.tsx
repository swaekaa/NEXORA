import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Agreement } from '../types/models';
import { useNegotiationSession } from '../hooks/useNegotiationSession';

export default function MerchantDashboard() {
  const [agreements, setAgreements] = useState<Agreement[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { activeNegotiationId } = useNegotiationSession();

  const merchant_id = "987f6543-e21b-34c5-b678-426614174999";

  useEffect(() => {
    async function load() {
      try {
        const data = await api.agreements.listForMerchant(merchant_id);
        setAgreements(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="w-full h-full pt-24 px-8 pb-8 overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto font-sans">
        
        <div className="mb-10 border-b-4 border-[#333333] pb-6 flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-bold tracking-widest text-[#333333] mb-2 uppercase">Agreements Archive</h1>
            <p className="text-[#888888] uppercase tracking-widest text-sm font-mono">Completed deals bound by the policy core</p>
          </div>
          <div className="text-right">
             <div className="text-2xl font-bold text-[#333333]">{agreements.length}</div>
             <div className="text-[#888888] text-xs font-bold uppercase tracking-widest">Total Deals</div>
          </div>
        </div>

        {activeNegotiationId && (
          <div 
            onClick={() => navigate(`/office`)}
            className="mb-8 p-4 bg-[#5BC0DE]/10 border-[3px] border-[#5BC0DE] shadow-[4px_4px_0_0_rgba(91,192,222,1)] flex justify-between items-center cursor-pointer hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 rounded-full bg-[#5BC0DE] animate-pulse"></div>
              <span className="font-bold font-sans text-[#333333] uppercase tracking-widest text-lg">● NEGOTIATION IN PROGRESS</span>
            </div>
            <span className="font-bold text-[#333333] font-mono tracking-widest">VIEW OFFICE →</span>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64 border-[3px] border-[#333333] bg-[#FFFDF7] shadow-[4px_4px_0_0_rgba(51,51,51,1)]">
            <div className="animate-pulse font-mono font-bold text-[#333333] tracking-widest uppercase">Fetching Records...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {agreements.map(deal => (
              <div 
                key={deal.id} 
                className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[4px_4px_0_0_rgba(51,51,51,1)] flex flex-col group cursor-pointer hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
                onClick={() => navigate(`/deals/${deal.id}`)}
              >
                <div className="bg-[#111111] p-3 flex justify-between items-center text-white border-b-[3px] border-[#333333]">
                  <span className="font-mono text-xs font-bold tracking-widest">ID: {deal.id.split('-')[0]}</span>
                  <span className={`px-2 py-0.5 text-[9px] font-bold tracking-widest uppercase border-2 ${
                    deal.status.includes('APPROVED') || deal.status.includes('VALIDATED') ? 'bg-[#5CB85C] border-[#111111] text-[#111111]' : 
                    deal.status.includes('FAILED') || deal.status.includes('REJECTED') ? 'bg-[#D9534F] border-[#111111] text-white' : 'bg-[#F0AD4E] border-[#111111] text-[#111111]'
                  }`}>
                    {deal.status.replace('_', ' ')}
                  </span>
                </div>
                
                <div className="p-6 flex-1 flex flex-col font-mono text-sm space-y-4">
                  <div>
                    <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Product</div>
                    <div className="text-base font-bold text-[#333333]">{deal.product_name || deal.product_id}</div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t-2 border-dashed border-[#333333]/20">
                    <div>
                      <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Quantity</div>
                      <div className="font-bold text-[#333333]">{deal.quantity} Units</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Unit Price</div>
                      <div className="font-bold text-[#5BC0DE]">₹{deal.unit_price}</div>
                    </div>
                  </div>
                  
                  <div className="pt-4 mt-auto">
                    <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Total Value</div>
                    <div className="text-xl font-bold text-[#333333]">₹{deal.total_amount}</div>
                  </div>
                  
                  <div className="pt-4 border-t-[3px] border-[#333333] flex justify-between items-center">
                    <span className="text-[10px] text-[#888888]">
                      {new Date(deal.created_at).toLocaleDateString()}
                    </span>
                    <span className="text-xs font-bold text-[#333333] group-hover:text-[#D9534F] transition-colors">
                      VIEW DETAILS →
                    </span>
                  </div>
                </div>
              </div>
            ))}
            
            {agreements.length === 0 && (
              <div className="col-span-full text-center text-[#888888] py-16 border-[3px] border-dashed border-[#333333]/30 bg-[#FFFDF7] font-mono font-bold tracking-widest uppercase">
                NO AGREEMENTS FOUND IN ARCHIVE
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
