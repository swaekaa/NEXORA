import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Agreement } from '../types/models';
import { useNegotiationSession } from '../hooks/useNegotiationSession';

export default function MerchantDashboard() {
  const [agreements, setAgreements] = useState<Agreement[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingPaymentId, setProcessingPaymentId] = useState<string | null>(null);
  const [processingApprovalId, setProcessingApprovalId] = useState<string | null>(null);
  const navigate = useNavigate();
  const { activeNegotiationId } = useNegotiationSession();

  const merchant_id = "987f6543-e21b-34c5-b678-426614174999";

  useEffect(() => {
    async function load() {
      try {
        const [data, approvalData] = await Promise.all([
           api.agreements.listForMerchant(merchant_id),
           api.approvals.list(merchant_id)
        ]);
        setAgreements(data);
        setApprovals(approvalData.filter((a: any) => a.status === 'pending'));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleDownloadReport = (e: React.MouseEvent, dealId: string) => {
    e.stopPropagation();
    window.open(`/deals/${dealId}/report`, '_blank');
  };

  const handleApprove = async (approvalId: string) => {
    try {
       setProcessingApprovalId(approvalId);
       await api.approvals.approve(merchant_id, approvalId);
       // Refresh lists
       const [data, approvalData] = await Promise.all([
          api.agreements.listForMerchant(merchant_id),
          api.approvals.list(merchant_id)
       ]);
       setAgreements(data);
       setApprovals(approvalData.filter((a: any) => a.status === 'pending'));
    } catch (e) {
       console.error(e);
       alert("Failed to approve");
    } finally {
       setProcessingApprovalId(null);
    }
  };

  const handleReject = async (approvalId: string) => {
    try {
       setProcessingApprovalId(approvalId);
       await api.approvals.reject(merchant_id, approvalId, "Merchant rejected the deal");
       // Refresh lists
       const [data, approvalData] = await Promise.all([
          api.agreements.listForMerchant(merchant_id),
          api.approvals.list(merchant_id)
       ]);
       setAgreements(data);
       setApprovals(approvalData.filter((a: any) => a.status === 'pending'));
    } catch (e) {
       console.error(e);
       alert("Failed to reject");
    } finally {
       setProcessingApprovalId(null);
    }
  };

  const handlePayNow = async (e: React.MouseEvent, deal: Agreement) => {
    e.stopPropagation();
    try {
      setProcessingPaymentId(deal.id);
      const paymentInfo = await api.payments.initiate(deal.id);
      
      const options = {
        key: (import.meta as any).env.VITE_RAZORPAY_KEY_ID || 'rzp_test_TUpL4wSvURspvK',
        amount: paymentInfo.amount_paise,
        currency: paymentInfo.currency,
        name: "NEXORA",
        description: "Deal Payment - " + deal.id.split('-')[0],
        order_id: paymentInfo.razorpay_order_id,
        handler: async function (response: any) {
          try {
            setProcessingPaymentId(deal.id + "_verifying"); // Use a pseudo-ID for verifying state
            const result = await api.payments.verify(
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature
            );
            
            if (result.status === 'captured') {
               // Refresh list
               const updated = await api.agreements.listForMerchant(merchant_id);
               setAgreements(updated);
            } else {
               alert("Payment not captured: " + result.status);
            }
          } catch (err: any) {
             console.error("Verification error:", err);
             alert("Verification failed: " + err.message);
          } finally {
             setProcessingPaymentId(null);
          }
        },
        prefill: { name: "Nexora Buyer", email: "buyer@nexora.ai" },
        theme: { color: "#333333" },
        modal: { ondismiss: function() { setProcessingPaymentId(null); } }
      };
      const rzp = new (window as any).Razorpay(options);
      rzp.on('payment.failed', function (response: any){
          alert("Payment failed: " + (response.error?.description || "Unknown error"));
          setProcessingPaymentId(null);
      });
      rzp.open();
    } catch (err: any) {
      console.error(err);
      let errMsg = 'PAYMENT UNAVAILABLE';
      if (err.message && err.message.includes('blocked')) errMsg = 'PAYMENT BLOCKED: ' + err.message;
      else if (err.message) errMsg = err.message;
      alert(errMsg);
      setProcessingPaymentId(null);
    }
  };

  return (
    <div className="w-full h-full pt-24 px-8 pb-8 overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto font-sans">
        
        <div className="mb-10 border-b-4 border-[#333333] pb-6 flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-bold tracking-widest text-[#333333] mb-2 uppercase">Agreements Archive</h1>
            <p className="text-[#888888] uppercase tracking-widest text-sm font-mono">Completed deals bound by the policy core</p>
          </div>
          <div className="text-right">
             <div className="text-2xl font-bold text-[#333333]">{agreements.length}</div>
             <div className="text-[#888888] text-xs font-bold uppercase tracking-widest">Total Deals</div>
          </div>
        </div>

        {activeNegotiationId && (
          <div 
            onClick={() => navigate(`/office`)}
            className="mb-8 p-4 bg-[#5BC0DE]/10 border-[3px] border-[#5BC0DE] shadow-[4px_4px_0_0_rgba(91,192,222,1)] flex justify-between items-center cursor-pointer hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 rounded-full bg-[#5BC0DE] animate-pulse"></div>
              <span className="font-bold font-sans text-[#333333] uppercase tracking-widest text-lg">● NEGOTIATION IN PROGRESS</span>
            </div>
            <span className="font-bold text-[#333333] font-mono tracking-widest">VIEW OFFICE →</span>
          </div>
        )}

        {!loading && approvals.length > 0 && (
          <div className="mb-12">
            <h2 className="text-xl font-bold tracking-widest text-[#D9534F] mb-4 uppercase flex items-center gap-2">
              <span className="animate-pulse">●</span> PENDING APPROVALS
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {approvals.map(approval => {
                const agreement = agreements.find(a => a.id === approval.agreement_id);
                return (
                  <div key={approval.id} className="bg-[#FFFDF7] border-4 border-[#D9534F] p-5 shadow-[4px_4px_0_0_rgba(217,83,79,1)]">
                    <div className="flex justify-between items-center border-b-2 border-dashed border-[#D9534F]/30 pb-3 mb-3">
                      <span className="font-bold font-mono text-xs uppercase tracking-widest text-[#D9534F]">HUMAN APPROVAL REQUIRED</span>
                      <span className="text-xs font-mono text-[#888888]">{new Date(approval.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="font-mono text-sm space-y-2 mb-4">
                      <div className="flex justify-between">
                        <span className="text-[#888888]">Buyer</span>
                        <span className="font-bold text-right">{agreement?.buyer_id.split('-')[0]}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#888888]">Product</span>
                        <span className="font-bold text-right truncate max-w-[150px]">{agreement?.product_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#888888]">Quantity</span>
                        <span className="font-bold">{agreement?.quantity} Units</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#888888]">Deal Total</span>
                        <span className="font-bold text-lg">₹{Number(agreement?.total_amount).toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#888888]">Reason</span>
                        <span className="text-[#D9534F] font-bold text-right max-w-[200px] text-xs leading-tight mt-1">{approval.reason}</span>
                      </div>
                    </div>
                    <div className="flex gap-4">
                      <button 
                        onClick={() => handleApprove(approval.id)}
                        disabled={processingApprovalId === approval.id}
                        className="flex-1 bg-[#5CB85C] text-[#111111] border-2 border-[#111111] py-2 font-bold uppercase tracking-widest text-xs shadow-[2px_2px_0_0_rgba(17,17,17,1)] hover:bg-[#4cae4c] active:translate-y-px active:shadow-none disabled:opacity-50"
                      >
                        [ APPROVE ]
                      </button>
                      <button 
                        onClick={() => handleReject(approval.id)}
                        disabled={processingApprovalId === approval.id}
                        className="flex-1 bg-[#D9534F] text-white border-2 border-[#111111] py-2 font-bold uppercase tracking-widest text-xs shadow-[2px_2px_0_0_rgba(17,17,17,1)] hover:bg-[#c9302c] active:translate-y-px active:shadow-none disabled:opacity-50"
                      >
                        [ REJECT ]
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64 border-[3px] border-[#333333] bg-[#FFFDF7] shadow-[4px_4px_0_0_rgba(51,51,51,1)]">
            <div className="animate-pulse font-mono font-bold text-[#333333] tracking-widest uppercase">Fetching Records...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {agreements.map(deal => (
              <div 
                key={deal.id} 
                className="bg-[#FFFDF7] border-[3px] border-[#333333] shadow-[4px_4px_0_0_rgba(51,51,51,1)] flex flex-col group cursor-pointer hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
                onClick={() => navigate(`/deals/${deal.id}`)}
              >
                <div className="bg-[#111111] p-3 flex justify-between items-center text-white border-b-[3px] border-[#333333]">
                  <span className="font-mono text-xs font-bold tracking-widest">ID: {deal.id.split('-')[0]}</span>
                  <span className={`px-2 py-0.5 text-[9px] font-bold tracking-widest uppercase border-2 ${
                    deal.status.includes('APPROVED') || deal.status.includes('VALIDATED') ? 'bg-[#5CB85C] border-[#111111] text-[#111111]' : 
                    deal.status.includes('FAILED') || deal.status.includes('REJECTED') ? 'bg-[#D9534F] border-[#111111] text-white' : 'bg-[#F0AD4E] border-[#111111] text-[#111111]'
                  }`}>
                    {deal.status.replace('_', ' ')}
                  </span>
                </div>
                
                <div className="p-6 flex-1 flex flex-col font-mono text-sm space-y-4">
                  <div>
                    <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Product</div>
                    <div className="text-base font-bold text-[#333333]">{deal.product_name || deal.product_id}</div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t-2 border-dashed border-[#333333]/20">
                    <div>
                      <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Quantity</div>
                      <div className="font-bold text-[#333333]">{deal.quantity} Units</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Unit Price</div>
                      <div className="font-bold text-[#5BC0DE]">₹{deal.unit_price}</div>
                    </div>
                  </div>
                  
                  <div className="pt-4 mt-auto">
                    <div className="text-[10px] text-[#888888] font-bold tracking-widest uppercase mb-1">Total Value</div>
                    <div className="text-xl font-bold text-[#333333]">₹{deal.total_amount}</div>
                  </div>
                  
                  <div className="pt-4 border-t-[3px] border-[#333333] flex flex-col gap-2">
                    <button 
                      onClick={(e) => handleDownloadReport(e, deal.id)}
                      className="w-full bg-[#111111] text-white py-2 font-bold uppercase tracking-widest text-xs hover:bg-[#333333]"
                    >
                      [ VIEW REPORT ]
                    </button>

                    {deal.status === 'PAYMENT_CAPTURED' ? (
                       <div className="w-full bg-[#EAE8DD] text-[#5CB85C] border-2 border-[#5CB85C] py-2 font-bold uppercase tracking-widest text-xs flex justify-center items-center">
                         ACCEPTED · ✓ PAID
                       </div>
                    ) : deal.status === 'PENDING_APPROVAL' ? (
                       <button 
                         disabled={true}
                         className="w-full bg-[#F0AD4E] text-[#111111] border-2 border-[#111111] py-2 font-bold uppercase tracking-widest text-xs shadow-[2px_2px_0_0_rgba(17,17,17,1)] disabled:opacity-50"
                       >
                         [ REQUIRES APPROVAL ]
                       </button>
                    ) : deal.status === 'VALIDATION_FAILED' || deal.status === 'PAYMENT_FAILED' || (deal.status as any) === 'CANCELLED' ? (
                       <button 
                         disabled={true}
                         className="w-full bg-[#D9534F] text-white border-2 border-[#111111] py-2 font-bold uppercase tracking-widest text-xs shadow-[2px_2px_0_0_rgba(17,17,17,1)] disabled:opacity-50"
                       >
                         [ DEAL FAILED ]
                       </button>
                    ) : (
                       <button 
                         onClick={(e) => handlePayNow(e, deal)}
                         disabled={processingPaymentId === deal.id || processingPaymentId === deal.id + "_verifying"}
                         className="w-full bg-[#5CB85C] text-[#111111] border-2 border-[#111111] py-2 font-bold uppercase tracking-widest text-xs shadow-[2px_2px_0_0_rgba(17,17,17,1)] hover:bg-[#4cae4c] active:translate-y-px active:shadow-none disabled:opacity-50"
                       >
                         {processingPaymentId === deal.id ? '[ INITIALIZING... ]' : 
                          processingPaymentId === deal.id + "_verifying" ? '[ VERIFYING... ]' : 
                          'ACCEPTED · PAYMENT PENDING (PAY NOW)'}
                       </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {agreements.length === 0 && (
              <div className="col-span-full text-center text-[#888888] py-16 border-[3px] border-dashed border-[#333333]/30 bg-[#FFFDF7] font-mono font-bold tracking-widest uppercase">
                NO AGREEMENTS FOUND IN ARCHIVE
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
