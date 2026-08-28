import React, { useEffect, useState } from 'react';
import { ShieldCheck, Activity, Search, Filter, Server, User } from 'lucide-react';
import { api } from '../api';
import { AuditEvent } from '../types/models';

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  
  const DEMO_MERCHANT_ID = "987f6543-e21b-34c5-b678-426614174999";

  useEffect(() => {
    api.audit.listForMerchant(DEMO_MERCHANT_ID)
      .then(setEvents)
      .catch(err => alert('Failed to load audit events: ' + err.message))
      .finally(() => setLoading(false));
  }, []);

  const filteredEvents = events.filter(e => 
    e.event_type.toLowerCase().includes(filter.toLowerCase()) || 
    e.actor_type.toLowerCase().includes(filter.toLowerCase()) ||
    (e.metadata && JSON.stringify(e.metadata).toLowerCase().includes(filter.toLowerCase()))
  );

  return (
    <div className="max-w-5xl mx-auto animate-fade-in-up pb-20">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
          <ShieldCheck className="text-slate-300" />
          Audit Trail
        </h1>
        <p className="text-slate-400">Append-only, cryptographically verifiable log of all system actions.</p>
      </div>

      <div className="glass-panel p-6 mb-8 flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <input 
            type="text" 
            placeholder="Search events, types, or metadata..." 
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
          />
        </div>
        <div className="flex items-center gap-2 text-slate-400 text-sm font-mono">
          <Filter size={16} />
          <span>Showing {filteredEvents.length} events</span>
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
             <div className="w-8 h-8 border-4 border-slate-500/30 border-t-slate-500 rounded-full animate-spin" />
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No events found matching your criteria.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/50 border-b border-slate-700/50 text-xs tracking-wider uppercase text-slate-400 font-mono">
                  <th className="p-4 pl-6 font-medium">Timestamp</th>
                  <th className="p-4 font-medium">Actor</th>
                  <th className="p-4 font-medium">Event Type</th>
                  <th className="p-4 font-medium">Resource IDs</th>
                  <th className="p-4 pr-6 font-medium">Metadata</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 text-sm">
                {filteredEvents.map(event => (
                  <tr key={event.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="p-4 pl-6 text-slate-400 font-mono text-xs whitespace-nowrap">
                      {new Date(event.created_at).toLocaleString()}
                    </td>
                    <td className="p-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {event.actor_type.toUpperCase().includes('SYSTEM') || event.actor_type.toUpperCase().includes('AGENT') ? (
                          <Server size={14} className="text-blue-400" />
                        ) : (
                          <User size={14} className="text-emerald-400" />
                        )}
                        <span className="font-mono text-xs text-slate-300 bg-slate-800 px-2 py-1 rounded">
                          {event.actor_type}
                        </span>
                      </div>
                    </td>
                    <td className="p-4 whitespace-nowrap">
                      <span className={`font-mono text-xs font-bold tracking-widest ${
                        event.event_type.includes('AGREEMENT') ? 'text-emerald-400' :
                        event.event_type.includes('POLICY') ? 'text-amber-400' :
                        event.event_type.includes('REJECT') ? 'text-rose-400' :
                        'text-blue-400'
                      }`}>
                        {event.event_type}
                      </span>
                    </td>
                    <td className="p-4 text-xs font-mono text-slate-500 space-y-1">
                      {event.negotiation_id && (
                        <div>Neg: <span className="text-slate-400">{event.negotiation_id.split('-')[0]}</span></div>
                      )}
                      {event.agreement_id && (
                        <div>Agr: <span className="text-slate-400">{event.agreement_id.split('-')[0]}</span></div>
                      )}
                    </td>
                    <td className="p-4 pr-6">
                      <div className="bg-slate-900 rounded border border-slate-800 p-2 text-xs font-mono text-slate-400 max-h-20 overflow-y-auto overflow-x-hidden">
                        {event.metadata ? (
                          <pre className="whitespace-pre-wrap m-0 font-inherit">{JSON.stringify(event.metadata, null, 2)}</pre>
                        ) : (
                          <span className="text-slate-600 italic">No metadata</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
