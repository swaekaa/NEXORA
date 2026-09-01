import { useState, useEffect } from 'react';
import { api } from '../../api';

interface DealFailedModalProps {
  negotiationId: string;
  onDismiss: () => void;
}

export const DealFailedModal = ({ negotiationId, onDismiss }: DealFailedModalProps) => {
  const [_negotiation, setNegotiation] = useState<any>(null);
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [_loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    
    // Fetch both negotiation state and messages to find the failure reason
    Promise.all([
      api.negotiations.get(negotiationId),
      api.negotiations.getMessages(negotiationId)
    ]).then(([negData, messages]) => {
      if (active) {
        setNegotiation(negData);
        if (messages && messages.length > 0) {
          const lastMessage = messages[messages.length - 1];
          // Usually the failure reason is the content of the final message
          if (lastMessage.content) {
            setFailureReason(lastMessage.content);
          }
        }
        setLoading(false);
      }
    }).catch(() => {
      if (active) {
        setLoading(false);
      }
    });
    
    return () => { active = false; };
  }, [negotiationId]);

  return (
    <div className="fixed inset-0 z-[999] bg-[#EAE8DD]/80 flex items-center justify-center backdrop-blur-sm animate-in fade-in duration-500">
      <div className="bg-[#FFFDF7] border-4 border-[#111111] p-8 max-w-md w-full shadow-[8px_8px_0_0_rgba(17,17,17,1)] flex flex-col items-center pointer-events-auto relative">
        
        <button onClick={onDismiss} className="absolute top-4 right-4 text-[#888888] hover:text-[#333333] font-bold">✕</button>

        <div className="w-16 h-16 bg-[#D9534F] rounded-full border-4 border-[#111111] flex items-center justify-center mb-4">
          <span className="text-white text-3xl font-bold">✕</span>
        </div>
        <h2 className="text-2xl font-bold font-sans text-[#333333] mb-1 uppercase tracking-tight text-center">Negotiation Failed</h2>
        <p className="text-xs text-[#D9534F] uppercase tracking-widest mb-6 text-center font-bold">Agents Could Not Agree</p>
        
        <p className="text-sm font-mono text-[#333333] text-center mb-6">
          The Buyer and Merchant agents were unable to reach a mutually acceptable agreement within the constraints.
        </p>

        {failureReason && (
          <div className="w-full bg-[#EAE8DD] border-2 border-[#333333] p-3 mb-6 flex flex-col gap-2">
            <span className="text-[10px] font-bold text-[#888888] uppercase tracking-widest">FAILURE REASON</span>
            <span className="text-sm font-mono text-[#D9534F] font-bold">{failureReason}</span>
          </div>
        )}
        
        <div className="w-full flex flex-col gap-3">
          <button 
            className="w-full bg-[#111111] text-white border-2 border-[#111111] py-3 font-bold uppercase tracking-widest shadow-[4px_4px_0_0_rgba(17,17,17,1)] hover:bg-[#333333] active:translate-y-1 active:shadow-none transition-all" 
            onClick={onDismiss}
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  );
};
