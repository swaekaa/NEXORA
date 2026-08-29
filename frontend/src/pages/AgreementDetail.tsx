import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Agreement } from '../types/models';

export default function AgreementDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [agreement, setAgreement] = useState<Agreement | null>(null);

  useEffect(() => {
    async function load() {
      if (!id) return;
      try {
        const data = await api.agreements.get(id);
        setAgreement(data);
      } catch (err) {
        console.error(err);
      }
    }
    load();
  }, [id]);

  if (!agreement) {
    return (
      <div className="w-full h-full pt-24 flex justify-center items-start bg-[#EAE8DD]">
        <div className="animate-pulse font-mono font-bold text-[#333333] tracking-widest uppercase bg-[#FFFDF7] border-[3px] border-[#333333] p-8 shadow-[4px_4px_0_0_rgba(51,51,51,1)]">
          LOADING AGREEMENT...
        </div>
      </div>
    );
  }

  const formatPrice = (price: string) => `₹${Number(price).toLocaleString('en-IN')}`;

  return (
    <div className="w-full h-full pt-24 px-8 pb-8 overflow-y-auto custom-scrollbar flex justify-center items-start">
      <div className="w-full max-w-2xl bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)] flex flex-col font-sans">
        
        {/* Paper Contract Header */}
        <div className="border-b-[3px] border-[#333333] px-8 py-6 bg-[#EAE8DD] relative">
          <div className="absolute top-0 right-0 w-16 h-16 border-l-[3px] border-b-[3px] border-[#333333] bg-[#D9534F] flex items-center justify-center -mr-[3px] -mt-[3px]">
            <span className="text-white font-bold text-2xl font-mono">OK</span>
          </div>
          
          <div className="flex justify-between items-start mb-6 pr-12">
            <div>
              <h1 className="text-3xl font-bold tracking-widest uppercase mb-1 text-[#333333]">FINAL AGREEMENT</h1>
              <p className="text-[#888888] text-sm font-mono tracking-widest uppercase">NEXORA PLATFORM GENERATED</p>
            </div>
          </div>
          
          <div className="grid grid-cols-3 gap-4 font-mono text-sm border-t-2 border-dashed border-[#333333]/30 pt-4">
            <div>
              <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">AGREEMENT ID</div>
              <div className="font-bold text-[#333333]">{agreement.id.split('-')[0]}</div>
            </div>
            <div>
              <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">DATE OF ENACTMENT</div>
              <div className="font-bold text-[#333333]">{new Date(agreement.created_at).toLocaleDateString()}</div>
            </div>
            <div>
              <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">STATUS</div>
              <div className={`font-bold ${
                agreement.status.includes('APPROVED') || agreement.status.includes('VALIDATED') ? 'text-[#5CB85C]' : 
                agreement.status.includes('FAILED') || agreement.status.includes('REJECTED') ? 'text-[#D9534F]' : 'text-[#F0AD4E]'
              }`}>
                {agreement.status.replace('_', ' ')}
              </div>
            </div>
          </div>
        </div>
        
        {/* Terms Section */}
        <div className="px-8 py-8 text-[#333333] font-mono">
          <h2 className="text-xl font-bold mb-6 border-b-[3px] border-[#333333] pb-2 uppercase tracking-widest">COMMERCIAL TERMS</h2>
          
          <div className="space-y-4">
            <div className="flex justify-between border-b-2 border-dashed border-[#333333]/20 pb-2">
              <span className="text-[#888888] font-bold">ASSET IDENTIFIER</span>
              <span className="font-bold">{agreement.product_name || agreement.product_id}</span>
            </div>
            
            <div className="flex justify-between border-b-2 border-dashed border-[#333333]/20 pb-2">
              <span className="text-[#888888] font-bold">UNIT PRICE</span>
              <span className="font-bold">{formatPrice(agreement.unit_price)}</span>
            </div>
            
            <div className="flex justify-between border-b-2 border-dashed border-[#333333]/20 pb-2">
              <span className="text-[#888888] font-bold">QUANTITY</span>
              <span className="font-bold">{agreement.quantity} UNITS</span>
            </div>
            
            <div className="flex justify-between pt-6 mt-6 border-t-[3px] border-[#333333]">
              <span className="text-xl font-bold tracking-widest">TOTAL OBLIGATION</span>
              <span className="text-xl font-bold text-[#5CB85C]">{formatPrice(agreement.total_amount)}</span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="bg-[#111111] p-4 flex justify-between items-center border-t-[3px] border-[#333333]">
          <button 
            onClick={() => navigate('/deals')}
            className="text-white border-2 border-transparent hover:border-white px-4 py-2 font-bold text-xs tracking-widest uppercase transition-colors"
          >
            ← BACK TO DEALS
          </button>
          
          <div className="flex gap-4">
             <button 
               onClick={() => navigate(`/negotiations/${agreement.negotiation_id}`)}
               className="bg-[#333333] text-white border-2 border-[#111111] hover:bg-[#222222] px-4 py-2 font-bold text-xs tracking-widest uppercase shadow-[2px_2px_0_0_rgba(255,255,255,0.2)] active:translate-y-1 active:shadow-none transition-all"
             >
               VIEW NEGOTIATION
             </button>
             <button className="bg-[#5CB85C] text-[#111111] border-2 border-[#111111] hover:bg-[#4CAe4C] px-6 py-2 font-bold text-xs tracking-widest uppercase shadow-[2px_2px_0_0_rgba(255,255,255,0.5)] active:translate-y-1 active:shadow-none transition-all">
               INITIATE PAYMENT
             </button>
          </div>
        </div>
      </div>
    </div>
  );
}
