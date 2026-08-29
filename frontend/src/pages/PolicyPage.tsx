import { useEffect, useState } from 'react';
import { api } from '../api';
import { Policy } from '../types/models';

export default function PolicyPage() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [loading, setLoading] = useState(true);
  
  const merchant_id = "987f6543-e21b-34c5-b678-426614174999";

  useEffect(() => {
    async function load() {
      try {
        const data = await api.policies.list(merchant_id);
        if (data.items.length > 0) {
          // Assume the first one or filter by is_active
          const activePolicy = data.items.find(p => p.is_active) || data.items[0];
          setPolicy(activePolicy);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="w-full h-full pt-24 px-8 pb-8 flex items-center justify-center bg-[#EAE8DD]">
      <div className="w-full max-w-4xl font-sans">
        <div className="mb-10 text-center border-b-[3px] border-[#333333] pb-6">
          <h1 className="text-4xl font-bold tracking-widest text-[#333333] mb-2 uppercase">Policy Core</h1>
          <p className="text-[#888888] uppercase tracking-widest text-sm font-mono">DETERMINISTIC EVALUATION ENGINE</p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64 border-[3px] border-[#333333] bg-[#FFFDF7] shadow-[4px_4px_0_0_rgba(51,51,51,1)]">
            <div className="animate-pulse font-mono font-bold text-[#333333] tracking-widest uppercase">Fetching Active Policy...</div>
          </div>
        ) : policy ? (
          <div className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)]">
            <div className="bg-[#111111] p-4 flex justify-between items-center text-white border-b-[3px] border-[#333333] font-mono text-xs font-bold tracking-widest">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 bg-[#5CB85C] border-2 border-[#111111] shadow-[0_0_0_1px_#5CB85C] rounded-full"></span>
                <span>SYSTEM STATUS: {policy.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
              </div>
              <span className="uppercase text-[#888888]">ID: {policy.id.split('-')[0]}</span>
            </div>
            
            <div className="p-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8 font-mono">
                
                <div className="border-b-2 border-dashed border-[#333333]/20 pb-4">
                  <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">TRANSACTION LIMIT</div>
                  <div className="text-2xl text-[#333333] font-bold">₹{Number(policy.maximum_autonomous_transaction).toLocaleString('en-IN')}</div>
                </div>
                
                <div className="border-b-2 border-dashed border-[#333333]/20 pb-4">
                  <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">MERCHANT FLOOR (MIN)</div>
                  <div className="text-2xl text-[#333333] font-bold">₹{Number(policy.minimum_price).toLocaleString('en-IN')} / UNIT</div>
                </div>
                
                <div className="border-b-2 border-dashed border-[#333333]/20 pb-4">
                  <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">MAX DISCOUNT</div>
                  <div className="text-2xl text-[#333333] font-bold">{policy.maximum_discount_percent}%</div>
                </div>
                
                <div className="border-b-2 border-dashed border-[#333333]/20 pb-4">
                  <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">HUMAN APPROVAL</div>
                  <div className={`text-2xl font-bold ${policy.human_approval_required ? 'text-[#D9534F]' : 'text-[#5CB85C]'}`}>
                    {policy.human_approval_required ? 'REQUIRED' : 'DISABLED'}
                  </div>
                </div>
  
                <div className="border-b-2 border-dashed border-[#333333]/20 pb-4">
                  <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">MAX NEGOTIATION ROUNDS</div>
                  <div className="text-2xl text-[#333333] font-bold">{policy.max_negotiation_rounds}</div>
                </div>
                
                <div className="border-b-2 border-dashed border-[#333333]/20 pb-4">
                  <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">DETERMINISTIC CHECKS</div>
                  <div className="text-2xl text-[#5BC0DE] font-bold">IMMUTABLE</div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center text-[#888888] py-16 border-[3px] border-dashed border-[#333333]/30 bg-[#FFFDF7] font-mono font-bold tracking-widest uppercase">
            NO ACTIVE POLICY FOUND
          </div>
        )}
      </div>
    </div>
  );
}
