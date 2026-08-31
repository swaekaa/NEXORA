import { useState } from 'react';

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<'buyer' | 'merchant' | 'policy' | null>(null);

  return (
    <div className="w-full h-full pt-24 px-8 pb-8 overflow-y-auto custom-scrollbar flex justify-center">
      <div className="w-full max-w-6xl font-sans">
        <div className="mb-10 text-center border-b-[3px] border-[#333333] pb-6">
          <h1 className="text-4xl font-bold tracking-widest text-[#333333] mb-2 uppercase">Agent Roster</h1>
          <p className="text-[#888888] uppercase tracking-widest text-sm font-mono">3 ACTIVE UNITS DEPLOYED</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Buyer Agent Card */}
          <div 
            className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[4px_4px_0_0_rgba(51,51,51,1)] cursor-pointer hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            onClick={() => setSelectedAgent('buyer')}
          >
            <div className="bg-[#5BC0DE]/10 p-6 flex flex-col items-center">
              <div className="w-24 h-24 bg-[#5BC0DE] mb-4 flex items-center justify-center border-[3px] border-[#333333] shadow-[2px_2px_0_0_rgba(51,51,51,1)]">
                <img src="/buyer.png" alt="Buyer Mascot" className="w-20 h-20 object-contain drop-shadow-md" style={{ imageRendering: 'pixelated' }} />
              </div>
              <h2 className="text-2xl font-bold text-[#333333] mb-1">JAKE</h2>
              <p className="text-[#888888] text-xs font-bold tracking-widest uppercase text-center">Buyer Agent<br/>Procurement Optimization</p>
            </div>
            <div className="p-4 border-t-[3px] border-[#333333] bg-[#111111] text-white text-xs font-mono font-bold tracking-widest uppercase flex justify-between">
              <span>TYPE: LLM</span>
              <span className="text-[#5CB85C]">● ONLINE</span>
            </div>
          </div>

          {/* Merchant Agent Card */}
          <div 
            className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[4px_4px_0_0_rgba(51,51,51,1)] cursor-pointer hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            onClick={() => setSelectedAgent('merchant')}
          >
            <div className="bg-[#D9534F]/10 p-6 flex flex-col items-center">
              <div className="w-24 h-24 bg-[#D9534F] mb-4 flex items-center justify-center border-[3px] border-[#333333] shadow-[2px_2px_0_0_rgba(51,51,51,1)]">
                <img src="/merchant.png" alt="Merchant Mascot" className="w-20 h-20 object-contain drop-shadow-md" style={{ imageRendering: 'pixelated' }} />
              </div>
              <h2 className="text-2xl font-bold text-[#333333] mb-1">HOLT</h2>
              <p className="text-[#888888] text-xs font-bold tracking-widest uppercase text-center">Merchant Agent<br/>Sales & Policy Adherence</p>
            </div>
            <div className="p-4 border-t-[3px] border-[#333333] bg-[#111111] text-white text-xs font-mono font-bold tracking-widest uppercase flex justify-between">
              <span>TYPE: LLM</span>
              <span className="text-[#5CB85C]">● ONLINE</span>
            </div>
          </div>

          {/* Policy Engine Card */}
          <div 
            className="bg-[#EAE8DD] border-[3px] border-[#333333] shadow-[4px_4px_0_0_rgba(51,51,51,1)] cursor-pointer hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            onClick={() => setSelectedAgent('policy')}
          >
            <div className="bg-[#111111]/5 p-6 flex flex-col items-center">
              <div className="w-24 h-24 bg-[#EAE8DD] mb-4 flex items-center justify-center border-[3px] border-[#333333] shadow-[2px_2px_0_0_rgba(51,51,51,1)]">
                 <img src="/policy.png" alt="Policy Mascot" className="w-20 h-20 object-contain drop-shadow-md" style={{ imageRendering: 'pixelated' }} />
              </div>
              <h2 className="text-2xl font-bold text-[#333333] mb-1">POLICY CORE</h2>
              <p className="text-[#888888] text-xs font-bold tracking-widest uppercase text-center">Verification Engine<br/>Immutable Deterministic</p>
            </div>
            <div className="p-4 border-t-[3px] border-[#333333] bg-[#111111] text-white text-xs font-mono font-bold tracking-widest uppercase flex justify-between">
              <span>TYPE: SYSTEM</span>
              <span className="text-[#5CB85C]">● ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Agent Inspector Modal */}
      {selectedAgent && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#EAE8DD]/90 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-[#FFFDF7] border-[3px] border-[#333333] w-full max-w-md shadow-[8px_8px_0_0_rgba(51,51,51,1)] font-sans mt-12 mb-12">
            <div className="bg-[#111111] px-4 py-2 border-b-[3px] border-[#333333] flex justify-between items-center text-white">
              <span className="font-mono text-xs font-bold tracking-widest uppercase">
                UNIT 0{selectedAgent === 'buyer' ? '1' : selectedAgent === 'merchant' ? '2' : '3'} / {selectedAgent}
              </span>
              <button 
                onClick={() => setSelectedAgent(null)}
                className="text-white hover:text-[#D9534F] font-bold"
              >
                [X]
              </button>
            </div>
            <div className="p-8">
              <div className="flex gap-6 mb-8">
                <div className={`w-24 h-24 flex-shrink-0 flex items-center justify-center border-[3px] border-[#333333] shadow-[2px_2px_0_0_rgba(51,51,51,1)] ${
                  selectedAgent === 'buyer' ? 'bg-[#5BC0DE]' : 
                  selectedAgent === 'merchant' ? 'bg-[#D9534F]' : 'bg-[#EAE8DD]'
                }`}>
                  <img 
                    src={selectedAgent === 'buyer' ? '/buyer.png' : selectedAgent === 'merchant' ? '/merchant.png' : '/policy.png'} 
                    alt="Agent Mascot" 
                    className="w-20 h-20 object-contain drop-shadow-md" 
                    style={{ imageRendering: 'pixelated' }} 
                  />
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-[#333333] mb-1">
                    {selectedAgent === 'buyer' ? 'JAKE' : selectedAgent === 'merchant' ? 'HOLT' : 'POLICY CORE'}
                  </h2>
                  <p className="text-[#888888] text-xs font-bold tracking-widest uppercase mb-4">
                    {selectedAgent === 'buyer' ? 'Procurement Agent' : 
                     selectedAgent === 'merchant' ? 'Sales Agent' : 'Verification System'}
                  </p>
                  <div className="inline-flex items-center gap-2 text-[10px] font-bold text-[#333333] border-2 border-[#333333] px-2 py-1 uppercase tracking-widest bg-[#EAE8DD]">
                    <span className="w-2 h-2 bg-[#5CB85C] border border-[#111111]"></span>
                    ONLINE & READY
                  </div>
                </div>
              </div>

              <div className="space-y-4 font-mono text-sm">
                <div className="flex justify-between border-b-2 border-dashed border-[#333333]/20 pb-2">
                  <span className="text-[#888888] font-bold tracking-widest uppercase text-xs">MODEL TYPE</span>
                  <span className="text-[#333333] font-bold">
                    {selectedAgent === 'policy' ? 'DETERMINISTIC' : 'LLM (GPT-4.1-MINI)'}
                  </span>
                </div>
                <div className="flex justify-between border-b-2 border-dashed border-[#333333]/20 pb-2">
                  <span className="text-[#888888] font-bold tracking-widest uppercase text-xs">PERSONALITY</span>
                  <span className="text-[#333333] font-bold text-right ml-4">
                    {selectedAgent === 'buyer' ? 'Sharp, data-driven, optimized' :
                     selectedAgent === 'merchant' ? 'Firm but fair sales veteran' :
                     'Cold, immutable, strict'}
                  </span>
                </div>
                <div className="flex justify-between border-b-2 border-dashed border-[#333333]/20 pb-2">
                  <span className="text-[#888888] font-bold tracking-widest uppercase text-xs">ROLE</span>
                  <span className="text-[#333333] font-bold text-right ml-4">
                    {selectedAgent === 'buyer' ? 'Negotiates best terms for buyer' :
                     selectedAgent === 'merchant' ? 'Proposes terms on behalf of merchant' :
                     'Enforces constraints strictly'}
                  </span>
                </div>
                <div className="flex justify-between pb-2">
                  <span className="text-[#888888] font-bold tracking-widest uppercase text-xs">CONNECTION</span>
                  <span className="text-[#5CB85C] font-bold">✓ SECURE</span>
                </div>
              </div>

              <button 
                onClick={() => setSelectedAgent(null)}
                className="w-full mt-8 bg-[#D9534F] text-white border-[3px] border-[#333333] py-3 font-bold tracking-widest uppercase shadow-[4px_4px_0_0_rgba(51,51,51,1)] active:translate-y-1 active:shadow-none transition-all"
              >
                RETURN TO ROSTER
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
