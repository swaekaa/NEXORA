import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play } from 'lucide-react';
import { OfficeScene } from '../game/OfficeScene';
import { GameProvider, useGame } from '../game/GameContext';
import { MockEventStream, LiveEventStream, NegotiationEventStream, IdleEventStream } from '../game/state/EventStream';
import { NegotiationHUD } from '../components/hud/NegotiationHUD';
import { ActivityLog } from '../components/hud/ActivityLog';
import { api } from '../api';

const NegotiationContent = ({ setupMode, simulationMode, children }: { setupMode: boolean, simulationMode: 'setup' | 'live' | 'demo', children?: React.ReactNode }) => {
  const { state } = useGame();
  const activityLogRef = useRef<HTMLDivElement>(null);
  const [logWidth, setLogWidth] = useState(288); // Default 72rem
  const isDragging = useRef(false);
  
  useEffect(() => {
    if (activityLogRef.current) {
      activityLogRef.current.scrollTop = activityLogRef.current.scrollHeight;
    }
  }, [state.events]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      // Restrict width between 250px and 40% of the screen
      const newWidth = Math.max(250, Math.min(e.clientX, window.innerWidth * 0.4));
      setLogWidth(newWidth);
    };
    const handleMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = 'default';
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // Find agreed deal event for the popup
  const agreedEvent = state.events.find(e => e.type === 'agreement_created');

  return (
    <div className="w-full h-full overflow-hidden bg-[#EAE8DD] relative">
      
      {/* Activity Log (Absolute Resizable Panel) */}
      <div 
        className="absolute top-0 left-0 h-full bg-[#FFFDF7] border-r-[3px] border-[#333333] flex flex-col z-40 shadow-[4px_0_0_0_rgba(51,51,51,1)]"
        style={{ width: `${logWidth}px` }}
      >
        <div className="p-4 border-b-[3px] border-[#333333] flex justify-between items-center bg-white/50">
          <span className="font-extrabold text-lg uppercase tracking-widest text-[#333333]">
            Activity Log {simulationMode === 'live' ? '(LIVE)' : simulationMode === 'demo' ? '(DEMO)' : ''}
          </span>
        </div>
        <div ref={activityLogRef} className="flex-1 overflow-y-auto overflow-x-hidden p-4 font-mono text-xs space-y-4 custom-scrollbar scroll-smooth">
          {state.events.filter(e => e.message || e.offer).map((e, i) => (
             <div key={i} className="flex flex-col gap-1 border-l-2 pl-3 py-1" style={{ borderLeftColor: e.agent === 'buyer' ? '#5BC0DE' : '#D9534F' }}>
               <div className="flex items-center gap-2">
                 <span className={e.agent === 'buyer' ? 'text-[#5BC0DE] font-bold text-[11px]' : 'text-[#D9534F] font-bold text-[11px]'}>
                   {e.agent === 'buyer' ? 'Jake' : 'Holt'}
                 </span>
                 <span className="text-[#888888] text-[9px]">{new Date(e.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}</span>
               </div>
               <div className="text-[#333333] break-words leading-relaxed">{e.message || `Proposed offer: ₹${e.offer?.unitPrice}`}</div>
             </div>
          ))}
          {state.events.length === 0 && <div className="text-[#888888] italic">Waiting for negotiation...</div>}
        </div>
        
        {/* Drag Handle */}
        <div 
          className="absolute top-0 -right-2 w-4 h-full cursor-col-resize z-50 flex items-center justify-center group"
          onMouseDown={(e) => { e.preventDefault(); isDragging.current = true; document.body.style.cursor = 'col-resize'; }}
        >
           <div className="w-1 h-16 bg-[#333333] rounded-full opacity-50 group-hover:opacity-100 transition-opacity"></div>
        </div>
      </div>

      {/* Office Area (Full Width, never resizes) */}
      <div className="w-full h-full relative bg-[#EAE8DD]">
        
        {/* Pixel Canvas Background */}
        <div className="absolute inset-0 z-0">
          <OfficeScene />
        </div>

        {/* HUD Overlay */}
        <div className="absolute inset-0 pointer-events-none z-10">
          <NegotiationHUD />
          {!setupMode && (
             <div className="absolute top-4 left-4 text-[#888888] font-bold tracking-widest text-sm uppercase bg-white/50 px-3 py-2 border-[2px] border-[#333333] pointer-events-auto shadow-[2px_2px_0_0_rgba(51,51,51,1)]">
               NEXORA // DEAL FLOOR
             </div>
          )}
        </div>
        
        {/* Render setup mode popup passed via children */}
        {children}
        
        {/* Deal Complete Popup Overlay */}
        {state.dealStatus === 'complete' && (
          <div className="absolute inset-0 z-50 bg-[#EAE8DD]/80 flex items-center justify-center backdrop-blur-sm animate-in fade-in duration-500">
            <div className="bg-[#FFFDF7] border-4 border-[#111111] p-8 max-w-sm w-full shadow-[8px_8px_0_0_rgba(17,17,17,1)] flex flex-col items-center pointer-events-auto">
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
  
  const [stream, setStream] = useState<NegotiationEventStream | null>(null);
  const [simulationMode, setSimulationMode] = useState<'setup' | 'live' | 'demo'>('setup');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // State for constraints
  const [maxBudget, setMaxBudget] = useState('1500000');
  const [quantity, setQuantity] = useState('100');
  const [requirements, setRequirements] = useState('Must include 1 year warranty. Delivery within 14 days.');

  useEffect(() => {
    return () => {
      if (stream) stream.stop();
    };
  }, [stream]);

  const startLive = async () => {
    try {
      setErrorMsg(null);
      setSimulationMode('live');
      
      const intent = {
          buyer_id: "123e4567-e89b-12d3-a456-426614174000",
          merchant_id: "987f6543-e21b-34c5-b678-426614174999",
          product_query: "monitor",
          quantity: parseInt(quantity, 10),
          maximum_budget: parseFloat(maxBudget),
          preferred_currency: "INR",
          requirements: requirements.split('.').filter(r => r.trim().length > 0)
      };

      const response = await api.buyers.runAgent(intent.buyer_id, intent);
      
      if (response.negotiation_id) {
          const liveStream = new LiveEventStream();
          setStream(liveStream);
          liveStream.start(response.negotiation_id);
      } else {
          console.error("No negotiation ID returned", response);
          setErrorMsg(response.error_reason || "Agent stopped unexpectedly (e.g. found no products matching your query).");
          setSimulationMode('setup');
      }
    } catch (e: any) {
      console.error("Failed to start live negotiation", e);
      setErrorMsg(e.message || "Failed to connect to the backend API.");
      setSimulationMode('setup');
    }
  };

  const startDemo = () => {
    setErrorMsg(null);
    setSimulationMode('demo');
    const mockStream = new MockEventStream();
    setStream(mockStream);
    mockStream.start();
  };

  return (
    <div className="w-full h-full relative overflow-y-auto overflow-x-hidden flex flex-col px-8 pt-24 pb-8 gap-8 custom-scrollbar scroll-smooth">

      {/* Game Window with Border */}
      {simulationMode === 'live' && !stream ? (
        <div className="h-[calc(100vh-128px)] min-h-[500px] shrink-0 relative border-[3px] border-[#333333] bg-[#EAE8DD] shadow-[4px_4px_0_0_rgba(51,51,51,1)] overflow-hidden flex flex-col items-center justify-center">
          <div className="w-16 h-16 border-4 border-[#333333] border-t-transparent rounded-full animate-spin mb-6"></div>
          <h2 className="text-xl font-bold text-[#333333] tracking-widest uppercase mb-2">Deploying Agents</h2>
          <p className="text-[#888888] font-mono text-sm text-center max-w-md">
            The Buyer Agent is analyzing market conditions and formulating its initial proposal. Please wait...
          </p>
        </div>
      ) : stream || simulationMode === 'setup' ? (
      <GameProvider stream={stream || (simulationMode === 'setup' ? new IdleEventStream() : new MockEventStream())}>
        <div className="h-[calc(100vh-128px)] min-h-[500px] shrink-0 relative border-[3px] border-[#333333] bg-[#EAE8DD] shadow-[4px_4px_0_0_rgba(51,51,51,1)] overflow-hidden flex flex-col">
          
          <NegotiationContent setupMode={simulationMode === 'setup'} simulationMode={simulationMode}>
            {simulationMode === 'setup' && (
              <div className="absolute inset-0 z-50 bg-[#EAE8DD]/90 backdrop-blur-sm flex items-center justify-center">
                <div className="bg-[#FFFDF7] border-4 border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)] p-8 max-w-lg w-full font-sans">
                  <h2 className="text-xl font-bold mb-2">Configure Constraints</h2>
                  <p className="text-sm text-[#888888] mb-6">Set up your procurement agent constraints before beginning the autonomous negotiation.</p>
                  
                  {errorMsg && (
                    <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm font-mono">
                      <strong>Deployment Failed:</strong> {errorMsg}
                    </div>
                  )}
                  
                  <div className="space-y-4 font-mono text-sm">
                    <div>
                      <label className="block text-[#888888] mb-1">MAXIMUM PRICE TOTAL (₹)</label>
                      <input 
                        type="number" 
                        value={maxBudget}
                        onChange={e => setMaxBudget(e.target.value)}
                        className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none" 
                      />
                    </div>
                    <div>
                      <label className="block text-[#888888] mb-1">QUANTITY</label>
                      <input 
                        type="number" 
                        value={quantity}
                        onChange={e => setQuantity(e.target.value)}
                        className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none" 
                      />
                    </div>
                    <div>
                      <label className="block text-[#888888] mb-1">HARD REQUIREMENTS</label>
                      <textarea 
                        value={requirements}
                        onChange={e => setRequirements(e.target.value)}
                        className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none h-20 resize-none"
                      ></textarea>
                    </div>
                  </div>

                  <div className="mt-8 flex justify-end">
                    <button 
                      onClick={startLive}
                      className="bg-[#D9534F] text-white border-2 border-[#333333] px-6 py-2 font-bold tracking-widest uppercase hover:bg-[#c9302c] shadow-[4px_4px_0_0_rgba(51,51,51,1)] transition-transform active:translate-y-1 active:shadow-none"
                    >
                      DEPLOY AGENT & START (LIVE)
                    </button>
                  </div>
                </div>
              </div>
            )}
          </NegotiationContent>
          
        </div>

        {/* Bottom Timeline Section */}
        <BottomSection startDemo={startDemo} simulationMode={simulationMode} />
      </GameProvider>
      ) : null}
    </div>
  );
}

// Extract bottom section to use GameContext for Timeline Graph
function BottomSection({ startDemo, simulationMode }: { startDemo: () => void, simulationMode: 'setup' | 'live' | 'demo' }) {
  const { state } = useGame();
  const timelineRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [graphHeight, setGraphHeight] = useState(200);
  
  // Auto-scroll timeline to the right when new events occur
  useEffect(() => {
    if (timelineRef.current) {
      timelineRef.current.scrollLeft = timelineRef.current.scrollWidth;
    }
  }, [state.events]);

  // Track container height for precise SVG coordinate mapping
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (let entry of entries) {
        setGraphHeight(entry.contentRect.height);
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);
  
  // Create timeline nodes from events
  const timelineEvents = state.events.filter(e => 
    e.type === 'offer' || 
    e.type === 'counteroffer' || 
    e.type === 'policy_check' || 
    e.type === 'agreement_created' || 
    e.type === 'negotiation_failed'
  );

  const prices = timelineEvents.filter(e => e.offer).map(e => parseFloat(e.offer?.unitPrice || "0"));
  const maxPrice = prices.length > 0 ? Math.max(...prices) : 100;
  const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
  const priceRange = maxPrice - minPrice || 1;

  const nodeWidth = 140;
  let lastPrice = maxPrice - (priceRange / 2); // Start in middle if no price yet

  // Map events to physical X/Y coordinates
  const nodes = timelineEvents.map((evt, idx) => {
    if (evt.offer && evt.offer.unitPrice) {
      lastPrice = parseFloat(evt.offer.unitPrice);
    }
    
    // Normalize Y between 20% and 70% of the container height to leave room for labels
    const normalizedY = priceRange > 0 ? ((lastPrice - minPrice) / priceRange) : 0.5;
    const y = (graphHeight * 0.2) + (1 - normalizedY) * (graphHeight * 0.5);
    const x = idx * nodeWidth + (nodeWidth / 2);

    let label = 'EVENT';
    let color = '#EAE8DD';
    if (evt.type === 'offer') { label = 'OPENING OFFER'; color = '#5BC0DE'; }
    if (evt.type === 'counteroffer') { label = 'COUNTEROFFER'; color = '#D9534F'; }
    if (evt.type === 'policy_check') { label = 'POLICY CHECK'; color = '#F0AD4E'; }
    if (evt.type === 'agreement_created') { label = 'ACCEPTED'; color = '#5CB85C'; }
    if (evt.type === 'negotiation_failed') { label = 'FAILED'; color = '#333333'; }

    return { ...evt, x, y, label, color, price: evt.offer ? lastPrice : null };
  });

  const svgWidth = Math.max(800, nodes.length * nodeWidth);

  // Generate smooth bezier curve path for SVG
  let pathD = "";
  nodes.forEach((node, idx) => {
    if (idx === 0) {
      pathD += `M ${node.x} ${node.y} `;
    } else {
      const prev = nodes[idx - 1];
      pathD += `C ${prev.x + 40} ${prev.y}, ${node.x - 40} ${node.y}, ${node.x} ${node.y} `;
    }
  });

  return (
    <div className="h-[500px] shrink-0 relative border-[3px] border-[#333333] bg-[#EAE8DD] shadow-[4px_4px_0_0_rgba(51,51,51,1)] overflow-hidden flex flex-col">
      <div className="p-4 border-b-[3px] border-[#333333] flex justify-between items-center bg-white/50 z-10 pointer-events-none">
        <span className="font-extrabold text-lg uppercase tracking-widest text-[#333333]">
          NEGOTIATION TIMELINE GRAPH // ROUND {state.roundCount}
        </span>
        {simulationMode === 'setup' && (
          <button 
             onClick={startDemo}
             className="bg-[#333333] text-white border-2 border-[#333333] px-4 py-1 text-[10px] font-bold tracking-widest uppercase hover:bg-[#111111] pointer-events-auto flex items-center gap-2 shadow-[2px_2px_0_0_rgba(17,17,17,1)] active:translate-y-px active:shadow-none transition-transform"
          >
             WATCH DEMO <Play size={10} className="fill-white" />
          </button>
        )}
      </div>

      <div ref={timelineRef} className="flex-1 overflow-x-auto overflow-y-hidden relative custom-scrollbar pointer-events-auto scroll-smooth">
        <div ref={containerRef} style={{ width: svgWidth, height: '100%', minWidth: '100%' }} className="relative">
          
          {/* SVG connecting lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
             <path d={pathD} fill="none" stroke="#333333" strokeWidth="3" strokeDasharray="6 6" className="opacity-40" />
          </svg>

          {/* HTML Nodes overlay */}
          {nodes.map((node, idx) => {
            const timeStr = new Date(node.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
            return (
              <div 
                key={node.id || idx} 
                className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 group"
                style={{ left: node.x, top: node.y }}
              >
                {/* Visual Dot */}
                <div 
                  className="w-4 h-4 border-2 border-[#333333] rounded-sm transition-transform duration-300 group-hover:scale-150 z-10 cursor-pointer shadow-[2px_2px_0_0_rgba(51,51,51,1)]" 
                  style={{ backgroundColor: node.color }}
                ></div>
                
                {/* Label Block */}
                <div className="absolute top-6 flex flex-col items-center min-w-[120px] opacity-80 group-hover:opacity-100 transition-opacity z-20">
                  <div className="text-[10px] font-bold text-[#333333] uppercase tracking-widest text-center leading-tight bg-[#FFFDF7] border-2 border-[#333333] px-2 py-0.5 shadow-[2px_2px_0_0_rgba(51,51,51,1)]">
                    {node.label}
                  </div>
                  <div className="text-[9px] text-[#888888] font-mono mt-1 bg-[#EAE8DD]/90 px-1 rounded-sm">{timeStr}</div>
                  
                  {node.price && (
                    <div className="text-[11px] font-bold text-[#5BC0DE] mt-1 bg-[#111111] border-2 border-[#333333] px-2 py-0.5 text-white shadow-[2px_2px_0_0_rgba(51,51,51,1)]">
                      ₹{Number(node.price).toLocaleString('en-IN')}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          
          {nodes.length === 0 && (
             <div className="absolute inset-0 flex items-center justify-center text-[#888888] text-xs font-mono italic">
               Awaiting negotiation events...
             </div>
          )}
        </div>
      </div>
    </div>
  );
}

