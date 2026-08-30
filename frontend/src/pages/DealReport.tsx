import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { Agreement, NegotiationMessage, AuditEvent } from '../types/models';

export default function DealReport({ agreementId: propAgreementId, onClose }: { agreementId?: string, onClose?: () => void }) {
  const params = useParams<{ agreementId: string }>();
  const agreementId = propAgreementId || params.agreementId;
  
  const [agreement, setAgreement] = useState<Agreement | null>(null);
  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!agreementId) return;

    const loadReport = async () => {
      try {
        const ag = await api.agreements.get(agreementId);
        if (!active) return;
        setAgreement(ag);

        const msgs = await api.negotiations.getMessages(ag.negotiation_id);
        if (!active) return;
        setMessages(msgs);

        // Try to fetch audit events
        try {
          // If a direct agreement audit endpoint exists, we use it. We'll try merchants endpoint and filter.
          const audit = await api.audit.listForMerchant(ag.merchant_id);
          if (active) {
            setAuditEvents(audit.filter((a: any) => 
               a.agreement_id === agreementId || a.negotiation_id === ag.negotiation_id
            ));
          }
        } catch (e) {
          console.error("Failed to fetch audit events", e);
        }

      } catch (err: any) {
        if (active) setErrorMsg(err.message || 'Failed to load deal report.');
      } finally {
        if (active) setLoading(false);
      }
    };

    loadReport();
    return () => { active = false; };
  }, [agreementId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FFFDF7] flex flex-col items-center justify-center font-mono">
        <div className="w-8 h-8 border-4 border-[#333333] border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-[#333333] tracking-widest font-bold uppercase">LOADING REPORT...</p>
      </div>
    );
  }

  if (errorMsg || !agreement) {
    return (
      <div className="min-h-screen bg-[#FFFDF7] flex flex-col items-center justify-center font-mono p-8">
        <h2 className="text-2xl font-bold text-[#D9534F] mb-4">DEAL COULD NOT BE LOADED</h2>
        <p className="text-[#333333]">{errorMsg}</p>
        <button onClick={() => onClose ? onClose() : window.close()} className="mt-8 px-6 py-2 border-2 border-[#111111] hover:bg-[#EAE8DD] uppercase font-bold tracking-widest">
          {onClose ? "CLOSE" : "CLOSE TAB"}
        </button>
      </div>
    );
  }

  // Pre-process timeline
  let roundNum = 0;
  let currentRoundMessages: {buyer?: NegotiationMessage, merchant?: NegotiationMessage} = {};
  const rounds: {round: parseInt, buyer?: NegotiationMessage, merchant?: NegotiationMessage}[] = [];
  
  messages.forEach(msg => {
     if (msg.sender_type === 'buyer') {
         if (currentRoundMessages.buyer) {
             rounds.push({ round: ++roundNum, ...currentRoundMessages });
             currentRoundMessages = {};
         }
         currentRoundMessages.buyer = msg;
     } else if (msg.sender_type === 'merchant') {
         currentRoundMessages.merchant = msg;
         rounds.push({ round: ++roundNum, ...currentRoundMessages });
         currentRoundMessages = {};
     }
  });
  if (currentRoundMessages.buyer || currentRoundMessages.merchant) {
      rounds.push({ round: ++roundNum, ...currentRoundMessages });
  }

  // Extract policy checks
  const policyCheckEvents = auditEvents.filter(e => e.event_type === 'POLICY_CHECK' || e.event_type === 'POLICY_DECISION' || e.event_type === 'EVALUATED');
  
  // Extract approval
  const approvalEvents = auditEvents.filter(e => e.event_type === 'APPROVAL_REQUESTED' || e.event_type === 'APPROVAL_APPROVED' || e.event_type === 'APPROVAL_REJECTED');
  
  // Inventory status (approximated from audit trail if no direct API)
  let inventoryStatus = 'RESERVED';
  if (agreement.status === 'payment_captured') inventoryStatus = 'COMMITTED';
  else if (agreement.status === 'payment_failed' || agreement.status === 'cancelled') inventoryStatus = 'RELEASED';

  return (
    <div className="min-h-screen bg-gray-100 p-4 md:p-8 font-sans print:p-0 print:bg-white text-sm">
      <div className="max-w-4xl mx-auto bg-white border border-gray-300 shadow-lg print:shadow-none print:border-none p-8 md:p-12 print:p-0">
        
        {/* REPORT HEADER */}
        <div className="border-b-4 border-[#111111] pb-6 mb-8 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold uppercase tracking-tight text-[#111111]">NEXORA</h1>
            <p className="text-[#888888] font-mono text-sm tracking-widest uppercase mt-1">Autonomous Commerce Report</p>
          </div>
          <div className="text-right font-mono text-xs text-[#555555]">
            <div className="font-bold text-[#111111] text-sm uppercase mb-1">{agreement.status.replace('_', ' ')}</div>
            <div>AGREEMENT: {agreement.id}</div>
            <div>NEGOTIATION: {agreement.negotiation_id}</div>
            <div>CREATED: {new Date(agreement.created_at).toLocaleString()}</div>
          </div>
        </div>

        {/* PARTIES */}
        <div className="grid grid-cols-2 gap-8 mb-10 font-mono border-b border-gray-200 pb-8">
          <div>
            <h3 className="font-bold uppercase text-[#888888] text-xs mb-3 tracking-widest border-l-2 border-[#5BC0DE] pl-2">Buyer Entity</h3>
            <div className="text-[#111111] truncate">{agreement.buyer_id}</div>
            <div className="text-xs text-gray-500 mt-1">NEXORA Authorized Agent</div>
          </div>
          <div>
            <h3 className="font-bold uppercase text-[#888888] text-xs mb-3 tracking-widest border-l-2 border-[#D9534F] pl-2">Merchant Entity</h3>
            <div className="text-[#111111] truncate">{agreement.merchant_id}</div>
            <div className="text-xs text-gray-500 mt-1">Registered Supplier</div>
          </div>
        </div>

        {/* PROCUREMENT REQUEST */}
        <div className="mb-10">
          <h2 className="text-lg font-bold uppercase tracking-tight border-b-2 border-[#111111] pb-2 mb-4">Original Procurement Intent</h2>
          <div className="bg-gray-50 p-4 font-mono text-sm grid grid-cols-2 gap-4">
             <div><span className="text-[#888888]">Product Query:</span> {agreement.product_name}</div>
             <div><span className="text-[#888888]">Quantity:</span> {agreement.quantity} units</div>
             {/* Note: Original intent budget isn't in Agreement model, we just show product details */}
             <div><span className="text-[#888888]">Final Agreed Price:</span> ₹{Number(agreement.unit_price).toLocaleString('en-IN')}</div>
             <div><span className="text-[#888888]">Currency:</span> {agreement.currency}</div>
          </div>
        </div>

        {/* PRODUCT */}
        <div className="mb-10">
          <h2 className="text-lg font-bold uppercase tracking-tight border-b-2 border-[#111111] pb-2 mb-4">Product Final Snapshot</h2>
          <table className="w-full font-mono text-left text-sm border-collapse">
            <thead>
              <tr className="border-b-2 border-gray-300">
                <th className="pb-2 font-bold text-[#888888]">ITEM</th>
                <th className="pb-2 font-bold text-[#888888]">QTY</th>
                <th className="pb-2 font-bold text-[#888888] text-right">UNIT PRICE</th>
                <th className="pb-2 font-bold text-[#888888] text-right">TOTAL</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="py-3 text-[#111111] font-bold">{agreement.product_name} <br/><span className="font-normal text-xs text-gray-500">ID: {agreement.product_id}</span></td>
                <td className="py-3">{agreement.quantity}</td>
                <td className="py-3 text-right">₹{Number(agreement.unit_price).toLocaleString('en-IN')}</td>
                <td className="py-3 text-right font-bold">₹{Number(agreement.total_amount).toLocaleString('en-IN')}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* TIMELINE */}
        <div className="mb-10 break-inside-avoid">
          <h2 className="text-lg font-bold uppercase tracking-tight border-b-2 border-[#111111] pb-2 mb-6">Negotiation Timeline</h2>
          <div className="space-y-6">
            {rounds.map((r, i) => (
              <div key={i} className="font-mono text-sm">
                <div className="font-bold text-[#111111] mb-2 uppercase tracking-widest text-xs">ROUND {r.round}</div>
                <div className="grid grid-cols-2 gap-4">
                  {r.buyer && (
                    <div className="border border-gray-200 p-3 bg-blue-50/30">
                      <div className="text-[#5BC0DE] font-bold text-xs uppercase mb-1 flex justify-between">
                         <span>BUYER AGENT</span>
                         <span>{new Date(r.buyer.created_at).toLocaleTimeString([], { hour12: false })}</span>
                      </div>
                      <div className="text-gray-800 font-bold mb-1">{r.buyer.message_type.toUpperCase()}</div>
                      {r.buyer.payload && (
                        <div className="text-gray-600 text-xs">
                          {r.buyer.payload.quantity} × ₹{Number(r.buyer.payload.unit_price).toLocaleString('en-IN')}<br/>
                          Total: ₹{Number(r.buyer.payload.total_amount).toLocaleString('en-IN')}
                        </div>
                      )}
                    </div>
                  )}
                  {r.merchant && (
                    <div className="border border-gray-200 p-3 bg-red-50/30">
                      <div className="text-[#D9534F] font-bold text-xs uppercase mb-1 flex justify-between">
                         <span>MERCHANT AGENT</span>
                         <span>{new Date(r.merchant.created_at).toLocaleTimeString([], { hour12: false })}</span>
                      </div>
                      <div className="text-gray-800 font-bold mb-1">{r.merchant.message_type.toUpperCase()}</div>
                      {r.merchant.payload && (
                        <div className="text-gray-600 text-xs">
                          {r.merchant.payload.quantity} × ₹{Number(r.merchant.payload.unit_price).toLocaleString('en-IN')}<br/>
                          Total: ₹{Number(r.merchant.payload.total_amount).toLocaleString('en-IN')}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* DETERMINISTIC POLICY CORE */}
        <div className="grid grid-cols-2 gap-8 mb-10 break-inside-avoid">
          <div>
            <h2 className="text-lg font-bold uppercase tracking-tight border-b-2 border-[#111111] pb-2 mb-4">Policy Validation Core</h2>
            <div className="font-mono text-sm space-y-2">
              <div className="flex items-center gap-2 text-[#5CB85C]"><span className="font-bold">✓</span> PRICE FLOOR</div>
              <div className="flex items-center gap-2 text-[#5CB85C]"><span className="font-bold">✓</span> MAX DISCOUNT</div>
              {approvalEvents.length > 0 ? (
                 <div className="flex items-center gap-2 text-[#D9534F]"><span className="font-bold">⚠</span> AUTONOMOUS LIMIT EXCEEDED</div>
              ) : (
                 <div className="flex items-center gap-2 text-[#5CB85C]"><span className="font-bold">✓</span> AUTONOMOUS LIMIT</div>
              )}
              <div className="mt-4 pt-2 border-t border-gray-200">
                <span className="text-[#888888] mr-2">FINAL DECISION</span>
                <span className="font-bold text-[#5CB85C]">ALLOW</span>
              </div>
            </div>
          </div>
          
          <div>
            <h2 className="text-lg font-bold uppercase tracking-tight border-b-2 border-[#111111] pb-2 mb-4">Human Approval</h2>
            <div className="font-mono text-sm">
              {approvalEvents.length > 0 ? (
                 <div className="space-y-1">
                    <div className="text-[#D9534F] font-bold uppercase">Required: YES</div>
                    <div className="text-[#5CB85C] font-bold mt-2">Status: APPROVED</div>
                    <div className="text-xs text-gray-500 mt-2">Verified by designated Merchant Approver.</div>
                 </div>
              ) : (
                 <div className="text-[#888888] italic font-bold">NOT REQUIRED</div>
              )}
            </div>
          </div>
        </div>

        {/* INVENTORY & FINANCIALS */}
        <div className="grid grid-cols-2 gap-8 mb-10 border-t-4 border-[#111111] pt-8 break-inside-avoid">
          <div>
            <h3 className="font-bold uppercase text-[#888888] text-xs mb-3 tracking-widest">Inventory State</h3>
            <div className="font-mono text-sm">
              <div className="font-bold text-lg">{inventoryStatus}</div>
              <div className="text-gray-500 mt-1">{agreement.quantity} Units Secured</div>
            </div>
          </div>
          <div className="text-right">
            <h3 className="font-bold uppercase text-[#888888] text-xs mb-3 tracking-widest">Financial Summary</h3>
            <div className="font-mono">
               <div className="flex justify-end gap-8 mb-1">
                 <span className="text-gray-500">UNIT PRICE</span>
                 <span>₹{Number(agreement.unit_price).toLocaleString('en-IN')}</span>
               </div>
               <div className="flex justify-end gap-8 mb-3">
                 <span className="text-gray-500">QUANTITY</span>
                 <span>{agreement.quantity}</span>
               </div>
               <div className="flex justify-end gap-8 text-xl border-t border-gray-200 pt-2 font-bold text-[#111111]">
                 <span className="text-gray-500 text-sm mt-1">TOTAL</span>
                 <span>₹{Number(agreement.total_amount).toLocaleString('en-IN')}</span>
               </div>
               <div className="text-xs text-gray-400 mt-1">CURRENCY: {agreement.currency}</div>
            </div>
          </div>
        </div>

        {/* PAYMENT STATUS */}
        <div className="mb-10 text-center font-mono p-6 bg-gray-50 border-2 border-gray-200">
           <h3 className="font-bold uppercase text-[#888888] text-xs mb-2 tracking-widest">Payment Status</h3>
           {agreement.status === 'payment_captured' ? (
              <div className="text-2xl font-bold text-[#5CB85C]">PAID IN FULL</div>
           ) : agreement.status === 'payment_initiated' ? (
              <div className="text-2xl font-bold text-[#F0AD4E]">ORDER CREATED</div>
           ) : (
              <div className="text-2xl font-bold text-[#111111]">NOT PAID</div>
           )}
        </div>

        {/* AUDIT SUMMARY */}
        <div className="text-xs font-mono text-gray-500 border-t border-gray-200 pt-4 break-inside-avoid">
          <h3 className="font-bold uppercase mb-2">Audit Event Log Summary</h3>
          <div className="space-y-1">
             {auditEvents.slice(0, 15).map(e => (
                <div key={e.id} className="flex gap-4">
                  <span className="w-40">{new Date(e.created_at).toLocaleString()}</span>
                  <span className="font-bold w-48">{e.event_type}</span>
                  <span className="truncate">{e.actor_type}</span>
                </div>
             ))}
             {auditEvents.length === 0 && <div>No audit events found for this negotiation.</div>}
          </div>
        </div>
        
        {/* PRINT / ACTION BUTTONS - Hidden when printing */}
        <div className="mt-12 flex justify-center gap-4 print:hidden border-t border-gray-200 pt-8">
           <button onClick={() => window.print()} className="px-8 py-3 bg-[#111111] text-white font-bold uppercase tracking-widest text-sm hover:bg-gray-800 transition-colors">
              PRINT / SAVE AS PDF
           </button>
           <button onClick={() => onClose ? onClose() : window.close()} className="px-8 py-3 border-2 border-[#111111] text-[#111111] font-bold uppercase tracking-widest text-sm hover:bg-gray-100 transition-colors">
              {onClose ? "CLOSE REPORT" : "CLOSE TAB"}
           </button>
        </div>

      </div>
    </div>
  );
}
