import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Building, AlertCircle, FileText, Activity } from 'lucide-react';
import { api } from '../api';
import { usePolling } from '../hooks/usePolling';

export default function MerchantDashboard() {
  const navigate = useNavigate();
  const DEMO_MERCHANT_ID = "987f6543-e21b-34c5-b678-426614174999";

  const fetchDashboardData = React.useCallback(async () => {
    const [negotiations, agreements, approvals] = await Promise.all([
      api.negotiations.listForMerchant(DEMO_MERCHANT_ID),
      api.agreements.listForMerchant(DEMO_MERCHANT_ID),
      api.approvals.list(DEMO_MERCHANT_ID)
    ]);
    return { negotiations, agreements, approvals };
  }, []);

  const { data, error } = usePolling(fetchDashboardData, 5000, () => false); // Poll every 5s continuously

  if (error) {
    return <div className="text-rose-400 glass-panel p-6">Error loading dashboard: {error.message}</div>;
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  const { negotiations, agreements, approvals } = data;
  
  const pendingApprovals = approvals.filter(a => a.status === 'PENDING');
  const activeNegotiations = negotiations.filter(n => !['ACCEPTED', 'REJECTED', 'EXPIRED'].includes(n.state));

  const formatPrice = (price: string) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(price));
  };

  const handleApprove = async (approvalId: string) => {
    try {
      await api.approvals.approve(DEMO_MERCHANT_ID, approvalId);
      // Data will refresh on next poll
    } catch (err: any) {
      alert('Failed to approve: ' + (err.message || err));
    }
  };

  const handleReject = async (approvalId: string) => {
    const reason = prompt("Enter rejection reason:");
    if (!reason) return;
    try {
      await api.approvals.reject(DEMO_MERCHANT_ID, approvalId, reason);
    } catch (err: any) {
      alert('Failed to reject: ' + (err.message || err));
    }
  };

  return (
    <div className="max-w-6xl mx-auto animate-fade-in-up pb-20">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
          <Building className="text-indigo-400" />
          Merchant Command Center
        </h1>
        <p className="text-slate-400">Monitor active negotiations, review approvals, and manage agreements.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="glass-panel p-6 border-l-4 border-l-indigo-500">
          <div className="text-slate-400 text-sm font-semibold mb-1 uppercase tracking-wider">Active Negotiations</div>
          <div className="text-3xl font-bold text-white">{activeNegotiations.length}</div>
        </div>
        <div className="glass-panel p-6 border-l-4 border-l-amber-500">
          <div className="text-slate-400 text-sm font-semibold mb-1 uppercase tracking-wider">Pending Approvals</div>
          <div className="text-3xl font-bold text-white">{pendingApprovals.length}</div>
        </div>
        <div className="glass-panel p-6 border-l-4 border-l-emerald-500">
          <div className="text-slate-400 text-sm font-semibold mb-1 uppercase tracking-wider">Total Agreements</div>
          <div className="text-3xl font-bold text-white">{agreements.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Pending Approvals Queue */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <AlertCircle className="text-amber-400" size={20} />
            Action Required
          </h2>
          
          {pendingApprovals.length === 0 ? (
            <div className="glass-panel p-8 text-center text-slate-500 border-dashed border-slate-700/50">
              No pending approvals.
            </div>
          ) : (
            pendingApprovals.map(approval => (
              <div key={approval.id} className="glass-panel p-5 border border-amber-500/20 bg-amber-500/5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <span className="text-xs font-mono text-amber-400 uppercase tracking-widest bg-amber-500/10 px-2 py-1 rounded">
                      POLICY OVERRIDE
                    </span>
                    <h3 className="font-bold text-slate-200 mt-2">Agreement / Negotiation Review</h3>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">
                    {new Date(approval.requested_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="bg-slate-900/50 rounded p-3 text-sm text-slate-300 font-mono mb-4 border border-slate-800">
                  {approval.reason}
                </div>
                <div className="flex gap-3">
                  <button 
                    onClick={() => handleApprove(approval.id)}
                    className="flex-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded py-2 text-sm font-bold transition-colors"
                  >
                    APPROVE
                  </button>
                  <button 
                    onClick={() => handleReject(approval.id)}
                    className="flex-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded py-2 text-sm font-bold transition-colors"
                  >
                    REJECT
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Active Negotiations & Agreements */}
        <div className="space-y-8">
          <div>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="text-blue-400" size={20} />
              Active Negotiations
            </h2>
            <div className="space-y-3">
              {activeNegotiations.length === 0 ? (
                <div className="glass-panel p-6 text-center text-slate-500 border-dashed border-slate-700/50">
                  No active negotiations.
                </div>
              ) : (
                activeNegotiations.map(neg => (
                  <div 
                    key={neg.id} 
                    onClick={() => navigate(`/negotiations/${neg.id}`)}
                    className="glass-panel p-4 hover:border-blue-500/50 cursor-pointer transition-colors flex justify-between items-center group"
                  >
                    <div>
                      <div className="font-mono text-sm text-slate-300 mb-1">#{neg.id.split('-')[0]}</div>
                      <div className="text-xs text-slate-500">Rounds: {neg.round_count} / {neg.max_rounds}</div>
                    </div>
                    <span className="status-pill bg-blue-500/10 text-blue-400 border-blue-500/20 group-hover:bg-blue-500/20">
                      {neg.state}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="text-emerald-400" size={20} />
              Recent Agreements
            </h2>
            <div className="space-y-3">
              {agreements.length === 0 ? (
                <div className="glass-panel p-6 text-center text-slate-500 border-dashed border-slate-700/50">
                  No agreements yet.
                </div>
              ) : (
                agreements.slice(0, 5).map(agr => (
                  <div 
                    key={agr.id}
                    onClick={() => navigate(`/agreements/${agr.id}`)}
                    className="glass-panel p-4 hover:border-emerald-500/50 cursor-pointer transition-colors flex justify-between items-center group"
                  >
                    <div>
                      <div className="font-mono text-sm text-slate-300 mb-1">#{agr.id.split('-')[0]} - {agr.product_name}</div>
                      <div className="text-xs text-slate-500">{agr.quantity} units @ {formatPrice(agr.unit_price)}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-emerald-400 font-bold text-sm mb-1">{formatPrice(agr.total_amount)}</div>
                      <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${
                        agr.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                        agr.status === 'PENDING_APPROVAL' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
                        'bg-slate-800 text-slate-400 border-slate-700'
                      }`}>
                        {agr.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
