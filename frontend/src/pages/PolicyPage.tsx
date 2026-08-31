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
    <div className="w-full h-full pt-24 px-8 pb-16 overflow-y-auto custom-scrollbar bg-[#EAE8DD]">
      <div className="w-full max-w-6xl mx-auto font-sans">
        <div className="mb-10 text-center border-b-[3px] border-[#333333] pb-6">
          <h1 className="text-4xl font-bold tracking-widest text-[#333333] mb-2 uppercase">Policy Core</h1>
          <p className="text-[#888888] uppercase tracking-widest text-sm font-mono">DETERMINISTIC EVALUATION ENGINE</p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64 border-[3px] border-[#333333] bg-[#FFFDF7] shadow-[4px_4px_0_0_rgba(51,51,51,1)]">
            <div className="animate-pulse font-mono font-bold text-[#333333] tracking-widest uppercase">Fetching Active Policy...</div>
          </div>
        ) : policy ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
            {/* Left Column: Avatar & System Status */}
            <div className="lg:col-span-1 flex flex-col gap-8">
              <div className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[4px_4px_0_0_rgba(51,51,51,1)] p-8 flex flex-col items-center text-center">
                <div className="w-32 h-32 bg-[#EAE8DD] border-[3px] border-[#333333] mb-6 flex items-center justify-center shadow-[4px_4px_0_0_rgba(51,51,51,1)]">
                  <img src="/policy.png" alt="Policy Mascot" className="w-24 h-24 object-contain" style={{ imageRendering: 'pixelated' }} />
                </div>
                <h2 className="text-3xl font-bold text-[#333333] mb-1">POLICY CORE</h2>
                <p className="text-[#888888] text-xs font-bold tracking-widest uppercase mb-2">Immutable Rule Engine</p>
                <div className="px-3 py-1 bg-[#5CB85C]/20 border-2 border-[#5CB85C] text-[#5CB85C] text-[10px] font-bold tracking-widest uppercase rounded-sm">
                  PROTECTED ASSET
                </div>
              </div>

              {/* Live Activity Logs (Moved to bottom left) */}
              <div className="bg-[#111111] border-[3px] border-[#333333] shadow-[4px_4px_0_0_rgba(51,51,51,1)] flex flex-col flex-1">
                <div className="p-3 border-b-[3px] border-[#333333] bg-[#222222] flex gap-2 justify-between items-center">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-[#D9534F] border border-[#111111]"></div>
                    <div className="w-3 h-3 rounded-full bg-[#F0AD4E] border border-[#111111]"></div>
                    <div className="w-3 h-3 rounded-full bg-[#5CB85C] border border-[#111111]"></div>
                  </div>
                  <span className="font-mono text-[10px] text-[#888888] tracking-widest uppercase flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#5CB85C] animate-pulse"></span>
                    system/engine_logs.sh
                  </span>
                </div>
                <div className="p-6 overflow-y-auto custom-scrollbar flex-1 font-mono text-[10px] leading-relaxed flex flex-col justify-end">
                  <div className="text-[#888888] mb-2">[INFO] Initializing Policy Engine v2.4.1-rc...</div>
                  <div className="text-[#888888] mb-2">[INFO] Loading rule constraints for Merchant {policy.id.split('-')[0]}</div>
                  <div className="text-[#5BC0DE] mb-2">[OK] Constraints successfully loaded into memory</div>
                  <div className="text-[#5CB85C] mb-2">[OK] Engine status: ACTIVE</div>
                  <div className="text-[#F0AD4E] mb-2">[WARN] Watching for incoming negotiations...</div>
                  <div className="text-white mt-2 flex items-center gap-2">
                    <span className="text-[#5CB85C]">root@policy:~#</span>
                    <span className="w-2 h-3 bg-white animate-pulse"></span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Parameters and Raw Data */}
            <div className="lg:col-span-2 flex flex-col gap-8">
              {/* Main Parameter Card */}
              <div className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)]">
                <div className="bg-[#111111] p-4 flex justify-between items-center text-white border-b-[3px] border-[#333333] font-mono text-xs font-bold tracking-widest">
                  <div className="flex items-center gap-3">
                    <span className={`w-3 h-3 rounded-full ${policy.is_active ? 'bg-[#5CB85C] shadow-[0_0_8px_2px_rgba(92,184,92,0.6)] animate-pulse' : 'bg-[#D9534F]'}`}></span>
                    <span>SYSTEM STATUS: {policy.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
                  </div>
                  <span className="uppercase text-[#888888]">ID: {policy.id.split('-')[0]}</span>
                </div>
                
                <div className="p-8">
                  <h3 className="font-mono font-bold text-[#888888] text-sm tracking-widest uppercase mb-8 border-b-2 border-dashed border-[#333333]/20 pb-2">Active Enforcement Parameters</h3>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-12 gap-y-8 font-mono">
                    <div>
                      <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">TRANSACTION LIMIT</div>
                      <div className="text-3xl text-[#333333] font-bold">₹{Number(policy.maximum_autonomous_transaction).toLocaleString('en-IN')}</div>
                      <div className="w-full h-2 bg-[#EAE8DD] mt-2 border border-[#333333]"><div className="h-full bg-[#5BC0DE] w-[85%]"></div></div>
                    </div>
                    
                    <div>
                      <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">MERCHANT FLOOR (MIN)</div>
                      <div className="text-3xl text-[#333333] font-bold">₹{Number(policy.minimum_price).toLocaleString('en-IN')}</div>
                      <div className="text-xs text-[#888888] mt-1 italic">per unit</div>
                    </div>
                    
                    <div>
                      <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">MAX DISCOUNT</div>
                      <div className="text-3xl text-[#333333] font-bold">{policy.maximum_discount_percent}%</div>
                      <div className="w-full h-2 bg-[#EAE8DD] mt-2 border border-[#333333]"><div className="h-full bg-[#D9534F]" style={{ width: `${policy.maximum_discount_percent}%` }}></div></div>
                    </div>
                    
                    <div>
                      <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">HUMAN APPROVAL</div>
                      <div className={`text-3xl font-bold ${policy.human_approval_required ? 'text-[#D9534F]' : 'text-[#5CB85C]'}`}>
                        {policy.human_approval_required ? 'REQUIRED' : 'DISABLED'}
                      </div>
                    </div>
      
                    <div>
                      <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">MAX NEGOTIATION ROUNDS</div>
                      <div className="text-3xl text-[#333333] font-bold">{policy.max_negotiation_rounds}</div>
                    </div>
                    
                    <div>
                      <div className="text-[10px] font-bold text-[#888888] tracking-widest uppercase mb-1">DETERMINISTIC CHECKS</div>
                      <div className="text-3xl text-[#5BC0DE] font-bold uppercase tracking-wider">Pass</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Raw JSON Dump (Full width) */}
              <div className="bg-[#111111] border-[3px] border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)] flex flex-col flex-1 min-h-[250px]">
                <div className="p-3 border-b-[3px] border-[#333333] bg-[#222222] flex gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#D9534F] border border-[#111111]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#F0AD4E] border border-[#111111]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#5CB85C] border border-[#111111]"></div>
                  <span className="ml-4 font-mono text-[10px] text-[#888888] tracking-widest uppercase">system/config_dump.json</span>
                </div>
                <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
                  <pre className="text-[#5CB85C] font-mono text-xs leading-relaxed">
                    {JSON.stringify(policy, null, 2)}
                  </pre>
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
