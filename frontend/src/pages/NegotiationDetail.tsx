import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Building, Clock, CheckCircle, ShieldCheck } from 'lucide-react';
import { api } from '../api';
import { usePolling } from '../hooks/usePolling';
import DecisionBoundary from '../components/policy/DecisionBoundary';

export default function NegotiationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const fetchState = React.useCallback(async () => {
    if (!id) throw new Error("No ID");
    const [negotiation, messages] = await Promise.all([
      api.negotiations.get(id),
      api.negotiations.getMessages(id)
    ]);
    return { negotiation, messages };
  }, [id]);

  const { data, error, isPolling } = usePolling(
    fetchState,
    2000,
    (res) => ['ACCEPTED', 'REJECTED', 'EXPIRED'].includes(res.negotiation.state.toUpperCase())
  );

  if (error) {
    return <div className="text-rose-400 glass-panel p-6">Error loading negotiation: {error.message}</div>;
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  const { negotiation, messages } = data;

  const formatPrice = (price: string) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(price));
  };

  return (
    <div className="max-w-5xl mx-auto animate-fade-in-up pb-20">
      <div className="mb-6 flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-white">Negotiation #{negotiation.id.split('-')[0]}</h1>
            <span className={`status-pill ${
              negotiation.state.toUpperCase() === 'ACCEPTED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              negotiation.state.toUpperCase() === 'REJECTED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
              'bg-blue-500/10 text-blue-400 border-blue-500/20'
            }`}>
              {negotiation.state.toUpperCase()}
            </span>
          </div>
          <p className="text-sm text-slate-400 font-mono">
            BUYER AGENT ↔ MERCHANT AGENT | Product: {negotiation.product_id.split('-')[0]}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6 relative">
          <div className="absolute left-6 top-8 bottom-8 w-px bg-slate-800" />
          {messages.map((msg) => {
            const isBuyer = msg.sender_type === 'buyer_agent';
            const isSystem = msg.sender_type === 'system';
            
            return (
              <div key={msg.id} className="relative pl-14">
                <div className={`absolute left-[21px] top-5 w-3 h-3 rounded-full border-2 border-slate-950 ${
                  isBuyer ? 'bg-blue-500' : isSystem ? 'bg-slate-500' : 'bg-indigo-500'
                }`} />
                
                <div className={`glass-panel p-5 border-l-4 ${
                  isBuyer ? 'border-l-blue-500' : isSystem ? 'border-l-slate-500' : 'border-l-indigo-500'
                }`}>
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      {isBuyer ? <User size={16} className="text-blue-400" /> : isSystem ? <ShieldCheck size={16} className="text-slate-400" /> : <Building size={16} className="text-indigo-400" />}
                      <span className="font-bold text-sm tracking-wider uppercase text-slate-200">
                        {msg.sender_type.replace('_', ' ')}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500 font-mono flex items-center gap-1">
                      <Clock size={12} />
                      {new Date(msg.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  <div className="text-slate-300 text-sm mb-4">
                    {msg.content}
                  </div>
                  
                  {msg.payload && (
                    <div className="bg-slate-900/50 rounded-lg p-3 font-mono text-xs text-slate-400 border border-slate-800 flex flex-wrap gap-4">
                      <div>
                        <span className="block text-slate-500 mb-1">UNIT PRICE</span>
                        <span className="text-slate-200">{formatPrice(msg.payload.unit_price)}</span>
                      </div>
                      <div>
                        <span className="block text-slate-500 mb-1">QUANTITY</span>
                        <span className="text-slate-200">{msg.payload.quantity}</span>
                      </div>
                      <div>
                        <span className="block text-slate-500 mb-1">TOTAL</span>
                        <span className="text-blue-300 font-bold">{formatPrice(msg.payload.total_amount)}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          
          {isPolling && (
            <div className="relative pl-14">
               <div className="absolute left-[21px] top-5 w-3 h-3 rounded-full border-2 border-slate-950 bg-slate-700 animate-pulse" />
               <div className="glass-panel p-5 bg-transparent border-dashed border-slate-700 flex items-center gap-3 text-slate-500 text-sm font-mono">
                 <div className="w-4 h-4 border-2 border-slate-500 border-t-transparent rounded-full animate-spin" />
                 Awaiting response...
               </div>
            </div>
          )}
        </div>
        
        <div className="lg:col-span-1 space-y-6">
          <div className="sticky top-8">
            <h3 className="text-sm font-bold tracking-widest text-slate-400 mb-4 uppercase">Verification Engine</h3>
            <DecisionBoundary 
              decision={negotiation.state.toUpperCase() === 'ACCEPTED' ? 'ALLOW' : negotiation.state.toUpperCase() === 'REJECTED' ? 'DENY' : null} 
            />
            
            {negotiation.state.toUpperCase() === 'ACCEPTED' && (
              <div className="mt-6 glass-panel p-5 border border-emerald-500/30 bg-emerald-500/5 text-center">
                <CheckCircle className="text-emerald-400 mx-auto mb-2" size={32} />
                <h4 className="text-emerald-400 font-bold mb-1">Agreement Validated</h4>
                <p className="text-xs text-slate-400 mb-4">The deterministic engine has authorized this transaction.</p>
                <button className="w-full glass-button bg-emerald-500/20 text-emerald-300 border-emerald-500/50 hover:bg-emerald-500/30">
                  View Agreement
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
