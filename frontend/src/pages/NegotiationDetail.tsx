import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

import { OfficeScene } from '../game/OfficeScene';
import { GameProvider, useGame } from '../game/GameContext';
import { MockEventStream, LiveEventStream, NegotiationEventStream, IdleEventStream } from '../game/state/EventStream';
import { NegotiationHUD } from '../components/hud/NegotiationHUD';

import { api } from '../api';
import { useNegotiationSession } from '../hooks/useNegotiationSession';
import { DealApprovedModal } from '../components/agreement/DealApprovedModal';
import { DealFailedModal } from '../components/agreement/DealFailedModal';

const NegotiationContent = ({ setupMode, simulationMode, children }: { setupMode: boolean, simulationMode: 'setup' | 'live' | 'demo', children?: React.ReactNode }) => {
  const { state } = useGame();
  const activityLogRef = useRef<HTMLDivElement>(null);
  const [logWidth, setLogWidth] = useState(350); // Increased default width
  const isDragging = useRef(false);
  const { activeNegotiationId } = useNegotiationSession();
  const [showModal, setShowModal] = useState(false);
  const [showFailedModal, setShowFailedModal] = useState(false);

  useEffect(() => {
    if (state.dealStatus === 'complete') {
      const timer = setTimeout(() => {
         setShowModal(true);
      }, 3000); // 3 seconds delay for visual scene
      return () => clearTimeout(timer);
    } else if (state.dealStatus === 'failed') {
      const timer = setTimeout(() => {
         setShowFailedModal(true);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [state.dealStatus]);
  
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
  const _agreedEvent = state.events.find(e => e.type === 'agreement_created');

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
             <>
               <div className="absolute top-4 left-4 text-[#888888] font-bold tracking-widest text-sm uppercase bg-white/50 px-3 py-2 border-[2px] border-[#333333] pointer-events-auto shadow-[2px_2px_0_0_rgba(51,51,51,1)]">
                 NEXORA // DEAL FLOOR
               </div>
               
               {/* Button to start a new negotiation */}
               <div className="absolute top-4 right-4 pointer-events-auto">
                 <button 
                   onClick={() => window.location.href = '/office?new=true'}
                   className="bg-[#333333] text-white border-2 border-[#111111] px-4 py-2 font-bold text-base tracking-widest uppercase hover:bg-[#111111] shadow-[2px_2px_0_0_rgba(51,51,51,1)] active:translate-y-px active:shadow-none transition-transform"
                 >
                   + NEW NEGOTIATION
                 </button>
               </div>
             </>
          )}
        </div>
        
        {/* Render setup mode popup passed via children */}
        {children}
        
        {/* Deal Complete Popup Overlay */}
        {showModal && activeNegotiationId && (
          <DealApprovedModal 
            negotiationId={activeNegotiationId} 
            merchantId="987f6543-e21b-34c5-b678-426614174999" 
            onDismiss={() => {
               setShowModal(false);
            }} 
          />
        )}
        
        {/* Deal Failed Popup Overlay */}
        {showFailedModal && activeNegotiationId && (
          <DealFailedModal 
            negotiationId={activeNegotiationId} 
            onDismiss={() => {
               setShowFailedModal(false);
            }} 
          />
        )}
      </div>
    </div>
  );
};

export default function NegotiationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { activeNegotiationId, setActiveNegotiationId, clearSession } = useNegotiationSession();
  
  const [stream, setStream] = useState<NegotiationEventStream | null>(null);
  const [simulationMode, setSimulationMode] = useState<'setup' | 'live' | 'demo'>('setup');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // State for buyer constraints
  const [maxBudget, setMaxBudget] = useState('450000');
  const [quantity, setQuantity] = useState('10');
  const [requirements, setRequirements] = useState('Must include 1 year warranty. Delivery within 14 days.');

  // State for merchant policy
  const [minPrice, setMinPrice] = useState('10000');
  const [maxDiscount, setMaxDiscount] = useState('20');
  const [maxAutonomousTransaction, setMaxAutonomousTransaction] = useState('500000');
  const [maxRounds, setMaxRounds] = useState('2');
  const [humanApproval, setHumanApproval] = useState(false);

  useEffect(() => {
    let _active = true;
    async function loadInitialState() {
      // Check query params
      const searchParams = new URLSearchParams(window.location.search);
      const isNew = searchParams.get('new') === 'true';

      if (id) {
        // 1. URL ID has highest precedence
        setSimulationMode('live');
        const liveStream = new LiveEventStream();
        setStream(liveStream);
        liveStream.start(id);
      } else if (isNew) {
        // 2. Explicit new negotiation requested
        clearSession();
        setSimulationMode('setup');
      } else if (activeNegotiationId) {
        // 3. Persisted active session
        setSimulationMode('live');
        const liveStream = new LiveEventStream();
        setStream(liveStream);
        liveStream.start(activeNegotiationId);
      } else {
        // 4. Default to setup
        setSimulationMode('setup');
      }
    }
    
    if (!stream) {
      loadInitialState();
    }

    return () => {
      active = false;
      if (stream) stream.stop();
    };
  }, [id, activeNegotiationId]);


  const startLive = async () => {
    try {
      setErrorMsg(null);
      setSimulationMode('live');
      
      const merchant_id = "987f6543-e21b-34c5-b678-426614174999";
      const buyer_id = "123e4567-e89b-12d3-a456-426614174000";

      // 1. Create/activate Merchant Policy
      await api.policies.create(merchant_id, {
        name: "Custom Live Policy",
        minimum_price: minPrice,
        maximum_discount_percent: maxDiscount,
        maximum_autonomous_transaction: maxAutonomousTransaction,
        max_negotiation_rounds: parseInt(maxRounds, 10),
        human_approval_required: humanApproval,
        is_active: true
      });

      // 2. Submit Buyer Intent
      const intent = {
          buyer_id,
          merchant_id,
          product_query: "monitor",
          quantity: parseInt(quantity, 10),
          maximum_budget: parseFloat(maxBudget),
          preferred_currency: "INR",
          requirements: requirements.split('.').filter(r => r.trim().length > 0)
      };

      const response = await api.buyers.runAgent(intent.buyer_id, intent);
      
      if (response.negotiation_id) {
          setActiveNegotiationId(response.negotiation_id);
          const liveStream = new LiveEventStream();
          setStream(liveStream);
          liveStream.start(response.negotiation_id);
          navigate(`/negotiations/${response.negotiation_id}`);
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
              <div className="absolute inset-0 z-50 bg-[#EAE8DD]/90 backdrop-blur-sm flex items-center justify-center p-8 overflow-y-auto custom-scrollbar">
                <div className="bg-[#FFFDF7] border-4 border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)] p-8 max-w-4xl w-full font-sans flex flex-col">
                  
                  {errorMsg && (
                    <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm font-mono">
                      <strong>Deployment Failed:</strong> {errorMsg}
                    </div>
                  )}

                  <div className="flex flex-col md:flex-row gap-8">
                    {/* Buyer Constraints */}
                    <div className="flex-1">
                      <h2 className="text-xl font-bold mb-2">Configure Buyer Constraints</h2>
                      <p className="text-sm text-[#888888] mb-6">Set up your procurement agent constraints before beginning the autonomous negotiation.</p>
                      
                      <div className="space-y-4 font-mono text-sm">
                        <div>
                          <label className="block text-[#888888] mb-1">MAXIMUM BUDGET TOTAL (₹)</label>
                          <input 
                            type="number" 
                            value={maxBudget}
                            onChange={e => setMaxBudget(e.target.value)}
                            className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none focus:bg-white transition-colors" 
                          />
                        </div>
                        <div>
                          <label className="block text-[#888888] mb-1">QUANTITY</label>
                          <input 
                            type="number" 
                            value={quantity}
                            onChange={e => setQuantity(e.target.value)}
                            className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none focus:bg-white transition-colors" 
                          />
                        </div>
                        <div>
                          <label className="block text-[#888888] mb-1">HARD REQUIREMENTS</label>
                          <textarea 
                            value={requirements}
                            onChange={e => setRequirements(e.target.value)}
                            className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none h-24 resize-none focus:bg-white transition-colors custom-scrollbar"
                          ></textarea>
                        </div>
                      </div>
                    </div>

                    <div className="hidden md:block w-0.5 bg-[#333333]/20"></div>

                    {/* Merchant Policy */}
                    <div className="flex-1">
                      <h2 className="text-xl font-bold mb-2">Configure Merchant Policy</h2>
                      <p className="text-sm text-[#888888] mb-6">Set the deterministic rules that govern the Merchant Agent.</p>
                      
                      <div className="space-y-4 font-mono text-sm">
                        <div>
                          <label className="block text-[#888888] mb-1">MINIMUM UNIT PRICE (₹)</label>
                          <input 
                            type="number" 
                            value={minPrice}
                            onChange={e => setMinPrice(e.target.value)}
                            className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none focus:bg-white transition-colors" 
                          />
                        </div>
                        <div className="flex gap-4">
                          <div className="flex-1">
                            <label className="block text-[#888888] mb-1">MAX DISCOUNT (%)</label>
                            <input 
                              type="number" 
                              value={maxDiscount}
                              onChange={e => setMaxDiscount(e.target.value)}
                              className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none focus:bg-white transition-colors" 
                            />
                          </div>
                          <div className="flex-1">
                            <label className="block text-[#888888] mb-1">MAX ROUNDS</label>
                            <input 
                              type="number" 
                              value={maxRounds}
                              onChange={e => setMaxRounds(e.target.value)}
                              className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none focus:bg-white transition-colors" 
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-[#888888] mb-1">MAX AUTONOMOUS TRANSACTION (₹)</label>
                          <input 
                            type="number" 
                            value={maxAutonomousTransaction}
                            onChange={e => setMaxAutonomousTransaction(e.target.value)}
                            className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-2 outline-none focus:bg-white transition-colors" 
                          />
                        </div>
                        <div className="flex items-center gap-3 pt-2">
                          <button
                            onClick={() => setHumanApproval(!humanApproval)}
                            className={`w-6 h-6 border-2 border-[#333333] flex items-center justify-center transition-colors ${humanApproval ? 'bg-[#D9534F]' : 'bg-[#EAE8DD]'}`}
                          >
                            {humanApproval && (
                              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </button>
                          <label className="text-[#333333] font-bold cursor-pointer" onClick={() => setHumanApproval(!humanApproval)}>
                            REQUIRE HUMAN APPROVAL FOR ALL DEALS
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-8 pt-8 border-t-2 border-[#333333]/20 flex justify-center gap-4">
                    <button 
                      onClick={startDemo}
                      className="bg-[#EAE8DD] text-[#333333] border-2 border-[#333333] px-8 py-3 font-bold tracking-widest uppercase hover:bg-black/5 shadow-[4px_4px_0_0_rgba(51,51,51,1)] transition-transform active:translate-y-1 active:shadow-none"
                    >
                      WATCH DEMO
                    </button>
                    <button 
                      onClick={startLive}
                      className="bg-[#D9534F] text-white border-2 border-[#333333] px-8 py-3 font-bold tracking-widest uppercase hover:bg-[#c9302c] shadow-[4px_4px_0_0_rgba(51,51,51,1)] transition-transform active:translate-y-1 active:shadow-none"
                    >
                      DEPLOY AGENTS & START (LIVE)
                    </button>
                  </div>
                </div>
              </div>
            )}
          </NegotiationContent>
          
        </div>

        {/* Bottom Timeline Section */}
        {simulationMode !== 'setup' && (
          <BottomSection startDemo={startDemo} simulationMode={simulationMode} />
        )}
      </GameProvider>
      ) : null}
    </div>
  );
}

// Extract bottom section to use GameContext for Timeline Graph
function BottomSection({ startDemo: _startDemo, simulationMode: _simulationMode }: { startDemo: () => void, simulationMode: 'setup' | 'live' | 'demo' }) {
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

