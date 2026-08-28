import React from 'react';
import { Shield, ShieldAlert, ShieldX, ArrowDown } from 'lucide-react';

interface DecisionBoundaryProps {
  decision?: 'ALLOW' | 'REVIEW' | 'DENY' | 'HUMAN_APPROVAL_REQUIRED' | null;
  failedChecks?: any[];
}

export default function DecisionBoundary({ decision, failedChecks }: DecisionBoundaryProps) {
  const getDecisionVisual = () => {
    switch (decision) {
      case 'ALLOW':
        return { color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10', icon: <Shield size={24} className="text-emerald-400" />, text: 'ALLOW' };
      case 'REVIEW':
      case 'HUMAN_APPROVAL_REQUIRED':
        return { color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10', icon: <ShieldAlert size={24} className="text-amber-400" />, text: 'REVIEW' };
      case 'DENY':
        return { color: 'text-rose-400', border: 'border-rose-500/30', bg: 'bg-rose-500/10', icon: <ShieldX size={24} className="text-rose-400" />, text: 'DENY' };
      default:
        return { color: 'text-slate-400', border: 'border-slate-700', bg: 'bg-slate-800/50', icon: <Shield size={24} className="text-slate-400" />, text: 'EVALUATING...' };
    }
  };

  const visual = getDecisionVisual();

  return (
    <div className="flex flex-col items-center py-6 w-full max-w-sm mx-auto opacity-90 hover:opacity-100 transition-opacity">
      <div className="text-xs font-mono text-slate-500 mb-2 flex flex-col items-center">
        <span>AI AGENT PROPOSES</span>
        <ArrowDown size={14} className="mt-1" />
      </div>
      
      <div className={`w-full border ${visual.border} ${visual.bg} rounded-xl p-4 backdrop-blur-md shadow-lg flex flex-col items-center relative overflow-hidden`}>
        <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-transparent via-slate-500/20 to-transparent" />
        
        <div className="flex items-center gap-2 mb-3">
          {visual.icon}
          <span className="font-bold tracking-widest text-sm text-slate-200">POLICY ENGINE</span>
        </div>
        
        <div className="w-full space-y-2 mb-4">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-mono">DETERMINISTIC VALIDATION</span>
          </div>
          {failedChecks && failedChecks.length > 0 ? (
            failedChecks.map((check, idx) => (
              <div key={idx} className="bg-rose-500/10 border border-rose-500/20 rounded p-2 text-xs font-mono text-rose-300">
                <div className="font-bold mb-1">✕ {check.rule || 'RULE'}</div>
                <div>{check.reason || 'Failed constraint check'}</div>
              </div>
            ))
          ) : decision === 'ALLOW' ? (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded p-2 text-xs font-mono text-emerald-300 flex items-center gap-2">
              <span>✓</span>
              <span>All constraints satisfied</span>
            </div>
          ) : (
            <div className="h-4 bg-slate-800/50 rounded animate-pulse" />
          )}
        </div>
        
        <div className={`px-4 py-1 rounded-full text-xs font-black tracking-widest border ${visual.border} ${visual.color} bg-slate-950`}>
          {visual.text}
        </div>
      </div>
    </div>
  );
}
