import { useEffect, useState } from 'react';
import { api } from '../api';
import { AuditEvent } from '../types/models';

export default function AuditTrailPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const merchant_id = "987f6543-e21b-34c5-b678-426614174999";

  useEffect(() => {
    async function load() {
      try {
        const data = await api.audit.listForMerchant(merchant_id);
        
        // Find the most recent negotiation ID
        const sortedEvents = [...data].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        const latestNegotiationId = sortedEvents.find(e => e.negotiation_id)?.negotiation_id;
        
        if (latestNegotiationId) {
          // Filter out events that belong to older negotiations, keeping global events (null negotiation_id) or latest
          const filtered = sortedEvents.filter(e => 
             !e.negotiation_id || e.negotiation_id === latestNegotiationId || e.agreement_id // keep agreement events too
          );
          setEvents(filtered);
        } else {
          setEvents(sortedEvents);
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
    <div className="w-full h-full pt-24 px-8 pb-8 overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto font-sans">
        
        <div className="mb-10 border-b-4 border-[#333333] pb-6 flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-bold tracking-widest text-[#333333] mb-2 uppercase">Audit Trail</h1>
            <p className="text-[#888888] uppercase tracking-widest text-sm font-mono">IMMUTABLE SYSTEM LOGS</p>
          </div>
          <div className="text-right">
             <div className="text-2xl font-bold text-[#333333]">{events.length}</div>
             <div className="text-[#888888] text-xs font-bold uppercase tracking-widest">Total Events</div>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64 border-[3px] border-[#333333] bg-[#FFFDF7] shadow-[4px_4px_0_0_rgba(51,51,51,1)]">
            <div className="animate-pulse font-mono font-bold text-[#333333] tracking-widest uppercase">Fetching Records...</div>
          </div>
        ) : (
          <div className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)] overflow-hidden">
            
            <div className="bg-[#111111] p-3 grid grid-cols-12 gap-4 text-white border-b-[3px] border-[#333333] font-mono text-[10px] font-bold tracking-widest uppercase">
              <div className="col-span-2">Timestamp</div>
              <div className="col-span-2">Event Type</div>
              <div className="col-span-2">Actor</div>
              <div className="col-span-2">Negotiation / Deal</div>
              <div className="col-span-4">Metadata</div>
            </div>

            <div className="divide-y-2 divide-dashed divide-[#333333]/20">
              {events.map(event => (
                <div key={event.id} className="p-4 grid grid-cols-12 gap-4 font-mono text-sm hover:bg-[#EAE8DD] transition-colors items-start">
                  <div className="col-span-2 text-xs text-[#888888]">
                    {new Date(event.created_at).toLocaleString()}
                  </div>
                  <div className="col-span-2 font-bold">
                    <span className={`px-2 py-0.5 text-[9px] border-2 uppercase tracking-widest ${
                      event.event_type.includes('ACCEPTED') || event.event_type.includes('CREATED') ? 'bg-[#5CB85C]/20 border-[#5CB85C] text-[#5CB85C]' :
                      event.event_type.includes('FAILED') || event.event_type.includes('REJECTED') ? 'bg-[#D9534F]/20 border-[#D9534F] text-[#D9534F]' :
                      event.event_type.includes('POLICY') ? 'bg-[#F0AD4E]/20 border-[#F0AD4E] text-[#F0AD4E]' :
                      'bg-[#5BC0DE]/20 border-[#5BC0DE] text-[#5BC0DE]'
                    }`}>
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <span className={`px-2 py-0.5 text-[9px] font-bold tracking-widest uppercase border-2 ${
                      event.actor_type === 'buyer_agent' ? 'bg-[#5BC0DE] border-[#111111] text-[#111111]' : 
                      event.actor_type === 'merchant_agent' ? 'bg-[#D9534F] border-[#111111] text-white' : 'bg-[#111111] border-[#111111] text-white'
                    }`}>
                      {event.actor_type.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="col-span-2 text-xs text-[#888888] truncate">
                    {(event.negotiation_id || (event.metadata as any)?.negotiation_id || (event.metadata as any)?.run_id)?.split('-')[0] || '-'} / {event.agreement_id?.split('-')[0] || '-'}
                  </div>
                  <div className="col-span-4 text-[10px] text-[#888888] break-words">
                    {event.metadata && Object.keys(event.metadata).length > 0 ? (
                      <div className="space-y-1 bg-[#111111]/5 p-2 border border-[#333333]/20">
                        {Object.entries(event.metadata).map(([k, v]) => (
                          <div key={k} className="flex gap-2">
                            <span className="text-[#333333] font-bold uppercase shrink-0">{k.replace(/_/g, ' ')}:</span>
                            <span className="text-[#888888] break-all">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="italic">No metadata</span>
                    )}
                  </div>
                </div>
              ))}

              {events.length === 0 && (
                <div className="p-8 text-center text-[#888888] font-mono font-bold tracking-widest uppercase">
                  NO AUDIT EVENTS FOUND
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
