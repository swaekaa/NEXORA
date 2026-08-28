import { useState } from 'react';

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<'buyer' | 'merchant' | null>(null);

  return (
    <div className="w-full h-full pt-20 px-8 relative">
      <div className="max-w-6xl mx-auto">
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold tracking-widest text-slate-200 mb-2">AGENT ROSTER</h1>
          <p className="text-slate-500 uppercase tracking-widest text-sm">3 ACTIVE UNITS DEPLOYED</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Buyer Agent Card */}
          <div 
            className="pixel-panel cursor-pointer hover:-translate-y-1 transition-transform border-blue-500/50"
            onClick={() => setSelectedAgent('buyer')}
          >
            <div className="bg-blue-500/10 p-6 flex flex-col items-center">
              <div className="w-24 h-24 bg-blue-500 mb-4 flex items-center justify-center border-4 border-slate-900 shadow-[4px_4px_0_0_rgba(0,0,0,0.5)]">
                <div className="w-16 h-16 bg-red-200 relative">
                   <div className="absolute top-4 left-2 w-3 h-3 bg-slate-900"></div>
                   <div className="absolute top-4 right-2 w-3 h-3 bg-slate-900"></div>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-blue-400 mb-1">ALEX</h2>
              <p className="text-blue-500/70 text-xs font-bold tracking-widest uppercase">Buyer Agent - Analytical</p>
            </div>
            <div className="p-4 border-t-2 border-slate-700 bg-slate-900 text-slate-400 text-xs flex justify-between">
              <span>92 XP</span>
              <span className="text-emerald-400">● ONLINE</span>
            </div>
          </div>

          {/* Merchant Agent Card */}
          <div 
            className="pixel-panel cursor-pointer hover:-translate-y-1 transition-transform border-orange-500/50"
            onClick={() => setSelectedAgent('merchant')}
          >
            <div className="bg-orange-500/10 p-6 flex flex-col items-center">
              <div className="w-24 h-24 bg-orange-500 mb-4 flex items-center justify-center border-4 border-slate-900 shadow-[4px_4px_0_0_rgba(0,0,0,0.5)]">
                <div className="w-16 h-16 bg-red-200 relative">
                   <div className="absolute top-4 left-3 w-3 h-3 bg-slate-900"></div>
                   <div className="absolute top-4 right-3 w-3 h-3 bg-slate-900"></div>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-orange-400 mb-1">MORGAN</h2>
              <p className="text-orange-500/70 text-xs font-bold tracking-widest uppercase">Merchant Agent - Strategic</p>
            </div>
            <div className="p-4 border-t-2 border-slate-700 bg-slate-900 text-slate-400 text-xs flex justify-between">
              <span>85 XP</span>
              <span className="text-emerald-400">● ONLINE</span>
            </div>
          </div>

          {/* Policy Engine Card */}
          <div className="pixel-panel border-emerald-500/50 opacity-80">
            <div className="bg-emerald-500/10 p-6 flex flex-col items-center">
              <div className="w-24 h-24 bg-slate-700 mb-4 flex items-center justify-center border-4 border-slate-900 shadow-[4px_4px_0_0_rgba(0,0,0,0.5)]">
                 <div className="w-12 h-12 bg-slate-800 flex items-center justify-center">
                    <div className="w-4 h-4 bg-emerald-500 rounded-full animate-blink"></div>
                 </div>
              </div>
              <h2 className="text-2xl font-bold text-emerald-400 mb-1">NEXORA CORE</h2>
              <p className="text-emerald-500/70 text-xs font-bold tracking-widest uppercase">Policy Engine - Deterministic</p>
            </div>
            <div className="p-4 border-t-2 border-slate-700 bg-slate-900 text-slate-400 text-xs flex justify-between">
              <span>SYSTEM</span>
              <span className="text-emerald-400">● ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Agent Inspector Modal */}
      {selectedAgent && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="pixel-panel w-full max-w-md animate-fade-in-up border-slate-500">
            <div className="pixel-panel-header bg-slate-800">
              <span>UNIT 0{selectedAgent === 'buyer' ? '1' : '2'} / {selectedAgent.toUpperCase()}</span>
              <button 
                onClick={() => setSelectedAgent(null)}
                className="text-slate-500 hover:text-white"
              >
                [X]
              </button>
            </div>
            <div className="p-8">
              <div className="flex gap-6 mb-8">
                <div className={`w-24 h-24 ${selectedAgent === 'buyer' ? 'bg-blue-500' : 'bg-orange-500'} flex-shrink-0 flex items-center justify-center border-4 border-slate-900 shadow-[4px_4px_0_0_rgba(0,0,0,0.5)]`}>
                  <div className="w-16 h-16 bg-red-200 relative">
                     <div className="absolute top-4 left-3 w-3 h-3 bg-slate-900"></div>
                     <div className="absolute top-4 right-3 w-3 h-3 bg-slate-900"></div>
                  </div>
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-white mb-1">
                    {selectedAgent === 'buyer' ? 'ALEX' : 'MORGAN'}
                  </h2>
                  <p className="text-slate-400 text-xs tracking-widest uppercase mb-4">
                    {selectedAgent === 'buyer' ? 'Procurement Agent' : 'Sales Agent'}
                  </p>
                  <div className="inline-flex items-center gap-2 text-xs font-bold text-emerald-400 bg-emerald-900/30 px-2 py-1 border border-emerald-800">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                    ONLINE & READY
                  </div>
                </div>
              </div>

              <div className="space-y-4 font-mono text-sm">
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-500">CONFIDENCE</span>
                  <span className="text-emerald-400">92%</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-500">CURRENT STATE</span>
                  <span className="text-blue-400">IDLE</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-500">NEGOTIATIONS</span>
                  <span className="text-white">24</span>
                </div>
                <div className="flex justify-between pb-2">
                  <span className="text-slate-500">POLICY CONNECTION</span>
                  <span className="text-emerald-400">✓ ACTIVE</span>
                </div>
              </div>

              <button 
                onClick={() => setSelectedAgent(null)}
                className="w-full mt-8 pixel-button bg-slate-800 border-slate-600"
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
