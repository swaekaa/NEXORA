import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Bot, ShieldCheck } from 'lucide-react';
import { api } from '../api';

export default function BuyerPage() {
  const [intent, setIntent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  
  // For MVP demo, hardcode a buyer_id that exists in the seeded DB
  const DEMO_BUYER_ID = "123e4567-e89b-12d3-a456-426614174000";
  const DEMO_MERCHANT_ID = "987f6543-e21b-34c5-b678-426614174999";

  const handleStartNegotiation = async () => {
    if (!intent) return;
    setIsLoading(true);
    try {
      const response = await api.buyers.runAgent(DEMO_BUYER_ID, {
        buyer_id: DEMO_BUYER_ID,
        merchant_id: DEMO_MERCHANT_ID,
        product_query: intent + " (Strict Instruction: Do NOT offer your maximum budget immediately. Your first offer MUST be exactly 10000 INR per unit, to leave room for negotiation. If they counter-offer below your budget, you may accept or counter again.)",
        quantity: 100,
        maximum_budget: "1200000.00",
        preferred_currency: "INR"
      });
      console.log('Agent run initiated:', response);
      if (response.negotiation_id) {
        navigate(`/negotiations/${response.negotiation_id}`);
      } else if (response.status === 'failed') {
        alert(`Agent failed: ${response.error_reason}`);
      } else {
        alert(`Agent stopped without proposing. Status: ${response.status}`);
      }
    } catch (error: any) {
      console.error('Failed to run agent', error);
      alert(`Failed to initiate negotiation:\n${error.message || error}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto animate-fade-in-up">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Buyer Console</h1>
          <p className="text-slate-400">Initiate autonomous procurement requests.</p>
        </div>
        <div className="glass-panel px-4 py-2 flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)] animate-pulse" />
          <span className="text-sm font-medium text-blue-100">BUYER AGENT ONLINE</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Input Panel */}
          <div className="glass-panel p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Bot className="text-blue-400" size={20} />
              Procurement Request
            </h2>
            <textarea
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              className="w-full h-32 bg-slate-900/50 border border-slate-700 rounded-lg p-4 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all resize-none"
              placeholder="E.g., I need 100 Dell monitors. My absolute max budget is ₹12 lakh, but try to get them for as cheap as possible. Don't accept the first list price!"
            />
            <div className="mt-4 flex justify-end">
              <button
                onClick={handleStartNegotiation}
                disabled={isLoading || !intent}
                className="glass-button-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-blue-200 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send size={16} />
                )}
                Start Negotiation
              </button>
            </div>
          </div>
          
          {/* Demo Notice */}
          <div className="glass-panel p-6 border-dashed border-slate-700/50 bg-transparent">
            <h3 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
              <ShieldCheck size={16} className="text-emerald-400" />
              Deterministic Execution
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              When you submit a request, the Buyer Agent will autonomously interact with the Merchant Agent. 
              NEXORA's Policy Engine mathematically enforces all limits before any agreement is generated.
            </p>
          </div>
        </div>
        
        {/* Sidebar Activity */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-panel p-6 h-full">
            <h2 className="text-lg font-semibold text-white mb-6">Agent Activity</h2>
            
            {isLoading ? (
              <div className="space-y-4">
                <div className="flex items-start gap-3 text-sm text-slate-400">
                  <div className="w-5 h-5 rounded-full border border-blue-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-ping" />
                  </div>
                  <p>Parsing procurement intent...</p>
                </div>
                <div className="flex items-start gap-3 text-sm text-slate-500">
                  <div className="w-5 h-5 rounded-full border border-slate-700 flex items-center justify-center flex-shrink-0 mt-0.5" />
                  <p>Searching merchant catalog</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center opacity-50">
                <Bot size={32} className="mb-3 text-slate-500" />
                <p className="text-sm text-slate-400">Agent is standing by.</p>
                <p className="text-xs text-slate-500 mt-1">Submit a request to begin.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
