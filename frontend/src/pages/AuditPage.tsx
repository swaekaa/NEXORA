import { useEffect, useState } from 'react';
import { api } from '../api';
import { AuditEvent } from '../types/models';

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.audit.listForMerchant("merch_556677");
        setEvents(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="w-full h-full pt-20 px-8 flex flex-col items-center">
      <div className="w-full max-w-5xl">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-widest text-slate-200 mb-2">SYSTEM AUDIT LOG</h1>
          <p className="text-slate-500 uppercase tracking-widest text-sm">IMMUTABLE EVENT RECORDS</p>
        </div>

        <div className="pixel-panel flex flex-col h-[70vh]">
          <div className="pixel-panel-header">
            <span>AUDIT TRAIL</span>
            <span>{events.length} EVENTS</span>
          </div>
          
          <div className="p-4 flex-1 overflow-auto font-mono text-sm space-y-2">
            {loading ? (
              <div className="text-center text-slate-500 animate-pulse py-8">READING ARCHIVE...</div>
            ) : events.length === 0 ? (
              <div className="text-center text-slate-600 py-8">NO AUDIT LOGS FOUND</div>
            ) : (
              events.map((evt, idx) => (
                <div key={idx} className="flex gap-4 border-b border-slate-800 pb-2 mb-2 hover:bg-slate-800/30 p-2">
                  <div className="text-slate-500 shrink-0">
                    {new Date(evt.created_at).toLocaleString()}
                  </div>
                  <div className={`w-32 shrink-0 font-bold ${
                    evt.event_type === 'POLICY_CHECK' ? 'text-emerald-400' :
                    evt.event_type === 'AGREEMENT_CREATED' ? 'text-blue-400' : 'text-amber-400'
                  }`}>
                    {evt.event_type.replace('_', ' ')}
                  </div>
                  <div className="text-slate-300">
                    {evt.actor_type?.toUpperCase()} / {(evt.agreement_id ? 'AGREEMENT' : 'NEGOTIATION')} ({(evt.agreement_id || evt.negotiation_id || evt.id)?.split('-')[0]})
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
