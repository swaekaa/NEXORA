import React, { useState } from 'react';
import { useGame } from '../../game/GameContext';

export const ActivityLog: React.FC = () => {
  const { state } = useGame();
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`absolute left-6 top-6 bg-slate-900/90 border-2 border-slate-700 pointer-events-auto transition-all duration-300 font-mono flex flex-col ${
      expanded ? 'w-80 h-96' : 'w-64 h-48'
    }`}>
      <div 
        className="bg-slate-800 p-2 text-xs font-bold text-slate-300 cursor-pointer flex justify-between items-center"
        onClick={() => setExpanded(!expanded)}
      >
        <span>ACTIVITY LOG</span>
        <span>{expanded ? '▼' : '▲'}</span>
      </div>
      
      <div className="flex-1 p-3 overflow-y-auto space-y-2 text-xs">
        {state.events.map((evt, idx) => (
          <div key={idx} className="border-b border-slate-800 pb-2 mb-2 last:border-0">
            <div className="flex gap-2 text-slate-500 mb-1">
              <span>{new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
              <span className="uppercase text-slate-400">{evt.agent || 'SYSTEM'}</span>
            </div>
            <div className="text-slate-300">
              {evt.type === 'message' ? '💬 Message sent' :
               evt.type === 'offer' ? '📄 Proposal created' :
               evt.type === 'counteroffer' ? '↩ Counteroffer sent' :
               evt.type === 'policy_check' ? '🔍 Policy validation requested' :
               evt.type === 'policy_result' ? `⚡ Policy result: ${evt.policy?.status}` :
               evt.type.toUpperCase().replace('_', ' ')}
            </div>
          </div>
        ))}
        {state.events.length === 0 && (
          <div className="text-slate-600 text-center mt-4">No activity yet.</div>
        )}
      </div>
    </div>
  );
};
