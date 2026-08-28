export default function PolicyPage() {
  return (
    <div className="w-full h-full pt-20 px-8 flex items-center justify-center">
      <div className="w-full max-w-4xl">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-widest text-emerald-400 mb-2">NEXORA POLICY CORE</h1>
          <p className="text-emerald-500/50 uppercase tracking-widest text-sm">DETERMINISTIC EVALUATION ENGINE</p>
        </div>

        <div className="pixel-panel border-emerald-500/30 bg-slate-900 shadow-[8px_8px_0_0_rgba(16,185,129,0.1)]">
          <div className="pixel-panel-header bg-emerald-900/30 border-emerald-500/30 text-emerald-400">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-emerald-500 rounded-none animate-blink"></span>
              <span>SYSTEM STATUS: ONLINE</span>
            </div>
            <span>V.2.0.4</span>
          </div>
          
          <div className="p-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8 font-mono">
              
              <div className="border-b-2 border-slate-800 pb-4">
                <div className="text-slate-500 text-sm mb-2">TRANSACTION LIMIT</div>
                <div className="text-2xl text-emerald-400 font-bold">₹5,00,000</div>
              </div>
              
              <div className="border-b-2 border-slate-800 pb-4">
                <div className="text-slate-500 text-sm mb-2">MERCHANT FLOOR (MIN)</div>
                <div className="text-2xl text-emerald-400 font-bold">₹10,000 / UNIT</div>
              </div>
              
              <div className="border-b-2 border-slate-800 pb-4">
                <div className="text-slate-500 text-sm mb-2">MAX DISCOUNT</div>
                <div className="text-2xl text-emerald-400 font-bold">20%</div>
              </div>
              
              <div className="border-b-2 border-slate-800 pb-4">
                <div className="text-slate-500 text-sm mb-2">HUMAN APPROVAL</div>
                <div className="text-2xl text-emerald-400 font-bold">ENABLED</div>
              </div>

              <div className="border-b-2 border-slate-800 pb-4">
                <div className="text-slate-500 text-sm mb-2">MAX NEGOTIATION ROUNDS</div>
                <div className="text-2xl text-emerald-400 font-bold">08</div>
              </div>
              
              <div className="border-b-2 border-slate-800 pb-4">
                <div className="text-slate-500 text-sm mb-2">DETERMINISTIC CHECKS</div>
                <div className="text-2xl text-emerald-400 font-bold">IMMUTABLE</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
