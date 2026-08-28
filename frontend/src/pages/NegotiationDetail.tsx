import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play } from 'lucide-react';
import { OfficeScene } from '../game/OfficeScene';
import { GameProvider, useGame } from '../game/GameContext';
import { MockEventStream } from '../game/state/EventStream';
import { NegotiationHUD } from '../components/hud/NegotiationHUD';
import { ActivityLog } from '../components/hud/ActivityLog';

// We create a wrapper to use GameContext for the ActivityLog & Deal Popup
const NegotiationContent = ({ stream, setupMode, startDemo }: { stream: any, setupMode: boolean, startDemo: () => void }) => {
  const { state } = useGame();
  
  // Find agreed deal event for the popup
  const agreedEvent = state.events.find(e => e.type === 'agreement_created');

  return (
    <div className="flex w-full h-full">
      {/* Activity Log (Left Side) */}
      <div className="w-72 bg-[#FFFDF7] border-r-[3px] border-[#333333] flex flex-col z-10 pointer-events-auto h-full shadow-[4px_0_0_0_rgba(51,51,51,0.1)] relative">
        <div className="p-4 border-b border-[#333333]/20 flex justify-between items-center bg-white">
          <span className="font-bold text-[10px] uppercase tracking-widest text-[#888888]">Activity Log</span>
        </div>
        <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-4 custom-scrollbar">
          {state.events.filter(e => e.message || e.offer).map((e, i) => (
             <div key={i} className="flex flex-col gap-1 border-l-2 pl-3 py-1" style={{ borderLeftColor: e.agent === 'buyer' ? '#5BC0DE' : '#D9534F' }}>
               <div className="flex items-center gap-2">
                 <span className={e.agent === 'buyer' ? 'text-[#5BC0DE] font-bold text-[11px]' : 'text-[#D9534F] font-bold text-[11px]'}>
                   {e.agent === 'buyer' ? 'Alex' : 'Morgan'}
                 </span>
                 <span className="text-[#888888] text-[9px]">{new Date(e.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}</span>
               </div>
               <div className="text-[#333333] break-words leading-relaxed">{e.message || `Proposed offer: ₹${e.offer?.unitPrice}`}</div>
             </div>
          ))}
          {state.events.length === 0 && <div className="text-[#888888] italic">Waiting for negotiation...</div>}
        </div>
      </div>

      {/* Office Scene (Right Side) */}
      <div className="flex-1 relative overflow-hidden">
        <OfficeScene />
        <NegotiationHUD />
        {!setupMode && (
           <div className="absolute top-4 left-4 text-[#888888] font-bold tracking-widest text-[10px] uppercase">
             NEXORA // DEAL FLOOR
           </div>
        )}
        
        {/* Deal Complete Popup Overlay */}
        {state.dealStatus === 'complete' && (
          <div className="absolute inset-0 z-50 bg-[#EAE8DD]/80 flex items-center justify-center backdrop-blur-sm animate-in fade-in duration-500">
            <div className="bg-[#FFFDF7] border-4 border-[#111111] p-8 max-w-sm w-full shadow-[8px_8px_0_0_rgba(17,17,17,1)] flex flex-col items-center">
              <div className="w-16 h-16 bg-[#5CB85C] rounded-full border-4 border-[#111111] flex items-center justify-center mb-6">
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold font-sans text-[#333333] mb-2 uppercase tracking-tight">Deal Agreed</h2>
              <div className="text-[#888888] font-mono text-xs uppercase tracking-widest mb-6">ID: {agreedEvent?.id || 'NX-0042'}</div>
              <div className="w-full bg-[#EAE8DD] p-4 border-2 border-[#111111] font-mono text-sm space-y-2">
                 <div className="flex justify-between"><span className="text-[#888888]">FINAL PRICE</span><span className="font-bold">₹{state.currentOffer?.unitPrice}</span></div>
                 <div className="flex justify-between"><span className="text-[#888888]">QUANTITY</span><span className="font-bold">{state.currentOffer?.quantity} UNITS</span></div>
              </div>
              <button className="mt-8 w-full bg-[#333333] text-white py-3 font-bold uppercase tracking-widest hover:bg-[#111111] transition-colors" onClick={() => window.location.href = '/deals'}>
                View Contract
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default function NegotiationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [stream] = useState(() => new MockEventStream());
  const [setupMode, setSetupMode] = useState(true);

  const startDemo = () => {
    setSetupMode(false);
    stream.stop();
    stream.start();
  };

  return (
    <div className="w-full h-full relative overflow-hidden pt-16 flex flex-col">
      {/* Top Title Bar */}
      <div className="px-8 py-4 z-40 bg-transparent flex flex-col pointer-events-none">
        <div className="text-[#888888] text-[10px] uppercase font-bold tracking-widest mb-2">ACTIVE DEAL / COMMERCIAL LEASE</div>
        <div className="text-3xl text-[#333333] font-sans font-medium tracking-tight">Office lease renewal</div>
        <div className="text-[#888888] text-[10px] uppercase font-bold tracking-widest mt-6">ROOM 01 / LIVE NEGOTIATION</div>
      </div>
      
      {/* Game Window with Border */}
      <GameProvider stream={stream}>
        <div className="flex-1 mx-8 relative border-[3px] border-[#333333] bg-[#EAE8DD] shadow-[4px_4px_0_0_rgba(51,51,51,1)] overflow-hidden flex flex-col">
          
          {setupMode && (
            <div className="absolute inset-0 z-50 bg-[#EAE8DD]/90 backdrop-blur-sm flex items-center justify-center">
              <div className="bg-[#FFFDF7] border-4 border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)] p-8 max-w-lg w-full font-sans">
                <h2 className="text-xl font-bold mb-2">Configure Constraints</h2>
                <p className="text-sm text-[#888888] mb-6">Set up your procurement agent constraints before beginning the autonomous negotiation.</p>
                
                <div className="space-y-4 font-mono text-sm">
                  <div>
                    <label className="block text-[#888888] mb-1">MAXIMUM PRICE (₹)</label>
                    <input type="text" defaultValue="9000" className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none" />
                  </div>
                  <div>
                    <label className="block text-[#888888] mb-1">QUANTITY</label>
                    <input type="text" defaultValue="100" className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none" />
                  </div>
                  <div>
                    <label className="block text-[#888888] mb-1">HARD REQUIREMENTS</label>
                    <textarea defaultValue="Must include 1 year maintenance. Delivery within 14 days." className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none h-20 resize-none"></textarea>
                  </div>
                </div>

                <div className="mt-8 flex justify-end">
                  <button 
                    onClick={startDemo}
                    className="bg-[#D9534F] text-white border-2 border-[#333333] px-6 py-2 font-bold tracking-widest uppercase hover:bg-[#c9302c] shadow-[4px_4px_0_0_rgba(51,51,51,1)] transition-transform active:translate-y-1 active:shadow-none"
                  >
                    DEPLOY AGENT & START
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="flex-1 relative">
            <NegotiationContent stream={stream} setupMode={setupMode} startDemo={startDemo} />
          </div>
          
        </div>

        {/* Bottom Timeline Section */}
        <BottomSection startDemo={startDemo} />
      </GameProvider>
    </div>
  );
}

// Extract bottom section to use GameContext for Timeline
function BottomSection({ startDemo }: { startDemo: () => void }) {
  const { state } = useGame();
  
  return (
    <div className="h-40 px-8 flex items-start justify-between pointer-events-none mt-4">
      
      <div className="flex-1 max-w-3xl border-t border-[#333333]/20 pt-4 flex flex-col relative pointer-events-auto">
        <div className="flex justify-between text-[10px] font-bold text-[#888888] uppercase tracking-widest mb-4">
          <span>NEGOTIATION TIMELINE</span>
          <span>ROUND {state.roundCount}</span>
        </div>
        
        <div className="relative flex items-center justify-between px-2">
          <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-[#333333]/20 -z-10"></div>
          
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 border border-[#333333] ${state.roundCount > 0 ? 'bg-[#5BC0DE]' : 'bg-[#EAE8DD]'}`}></div>
            <div className="text-[10px] font-bold text-[#333333] mt-2 uppercase tracking-widest">OPENING OFFER</div>
          </div>
          
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 border border-[#333333] ${state.roundCount > 1 ? 'bg-[#5BC0DE]' : 'bg-[#EAE8DD]'}`}></div>
            <div className="text-[10px] font-bold text-[#333333] mt-2 uppercase tracking-widest">COUNTEROFFER</div>
          </div>
          
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 border border-[#333333] ${state.policyStatus === 'validating' || state.policyStatus === 'approved' ? 'bg-[#5BC0DE]' : 'bg-[#EAE8DD]'}`}></div>
            <div className="text-[10px] font-bold text-[#333333] mt-2 uppercase tracking-widest">POLICY CHECK</div>
          </div>
          
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 border border-[#333333] ${state.dealStatus === 'complete' ? 'bg-[#5CB85C]' : 'bg-[#EAE8DD]'}`}></div>
            <div className="text-[10px] font-bold text-[#888888] mt-2 uppercase tracking-widest">ACCEPTED</div>
          </div>
        </div>
      </div>

      <div className="w-64 flex flex-col items-end gap-2 pointer-events-auto mt-4">
        <button 
           onClick={startDemo}
           className="bg-[#D9534F] text-white border-2 border-[#333333] px-6 py-2 text-xs font-bold tracking-widest uppercase hover:bg-[#c9302c] shadow-[4px_4px_0_0_rgba(51,51,51,1)] transition-transform active:translate-y-1 active:shadow-none flex items-center gap-2"
        >
           WATCH DEMO <Play size={12} className="fill-white" />
        </button>
        
        <div className="flex gap-2">
          <button className="bg-white text-[#333333] border-2 border-[#333333] px-4 py-1 text-[10px] font-bold tracking-widest uppercase hover:bg-gray-50 shadow-[2px_2px_0_0_rgba(51,51,51,1)] active:translate-y-1 active:shadow-none">
            COMPLETE DEAL
          </button>
          <button className="bg-white text-[#333333] border-2 border-[#333333] px-4 py-1 text-[10px] font-bold tracking-widest uppercase hover:bg-gray-50 shadow-[2px_2px_0_0_rgba(51,51,51,1)] active:translate-y-1 active:shadow-none">
            REPLAY
          </button>
        </div>
      </div>
    </div>
  );
}
