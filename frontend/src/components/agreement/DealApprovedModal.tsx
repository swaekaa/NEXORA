import { useState, useEffect } from 'react';
import { api } from '../../api';

interface DealApprovedModalProps {
  negotiationId: string;
  merchantId: string;
  onDismiss: () => void;
}

export const DealApprovedModal = ({ negotiationId, merchantId, onDismiss }: DealApprovedModalProps) => {
  const [agreement, setAgreement] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'initializing' | 'blocked' | 'verifying' | 'confirmed' | 'failed'>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [approvalRequest, setApprovalRequest] = useState<any>(null);
  const [isApproving, setIsApproving] = useState(false);

  useEffect(() => {
    let active = true;
    api.agreements.listForMerchant(merchantId).then(agreements => {
      const data = agreements.find((a: any) => a.negotiation_id === negotiationId);
      if (active) {
        if (data) {
          setAgreement(data);
          setLoading(false);
          if (data.status === 'payment_captured') {
            setPaymentStatus('confirmed');
          } else if (data.status === 'payment_initiated') {
            setPaymentStatus('verifying');
          }
          
          // Check for pending approvals
          api.approvals.list(merchantId).then(approvals => {
            if (!active) return;
            const pending = approvals.find((ap: any) => ap.agreement_id === data.id && ap.status === 'pending');
            if (pending) {
               setApprovalRequest(pending);
            }
          }).catch(console.error);

        } else {
          setErrorMsg('AGREEMENT NOT FOUND YET');
          setLoading(false);
        }
      }
    }).catch(err => {
      if (active) {
        setErrorMsg('DEAL COULD NOT BE LOADED');
        setLoading(false);
      }
    });
    return () => { active = false; };
  }, [negotiationId, merchantId]);

  useEffect(() => {
    let intervalId: any;
    if (paymentStatus === 'verifying' && agreement) {
      intervalId = setInterval(async () => {
        try {
          const data = await api.agreements.get(agreement.id);
          if (data.status === 'payment_captured') {
            setPaymentStatus('confirmed');
            setAgreement(data);
            clearInterval(intervalId);
          } else if (data.status === 'payment_failed' || data.status === 'validation_failed' || data.status === 'cancelled') {
            setPaymentStatus('failed');
            setAgreement(data);
            clearInterval(intervalId);
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 2000);
      
      setTimeout(() => {
         if (paymentStatus === 'verifying') {
             clearInterval(intervalId);
             setPaymentStatus('idle');
         }
      }, 60000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [paymentStatus, agreement]);

  // Polling for approval status if it's pending
  useEffect(() => {
    let intervalId: any;
    if (approvalRequest && approvalRequest.status === 'pending') {
      intervalId = setInterval(async () => {
        try {
          const approvals = await api.approvals.list(merchantId);
          const current = approvals.find((ap: any) => ap.id === approvalRequest.id);
          if (current && current.status !== 'pending') {
             setApprovalRequest(current);
             clearInterval(intervalId);
             const data = await api.agreements.get(agreement.id);
             setAgreement(data);
          }
        } catch (e) {
          console.error("Approval polling error", e);
        }
      }, 3000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [approvalRequest, merchantId, agreement]);

  const handleDownloadReport = () => {
    if (agreement) window.open(`/deals/${agreement.id}/report`, '_blank');
  };

  const handleApprove = async () => {
    if (!approvalRequest) return;
    try {
      setIsApproving(true);
      setErrorMsg(null);
      await api.approvals.approve(merchantId, approvalRequest.id);
      setApprovalRequest(null);
      // Re-fetch agreement to update status
      const updatedAgreement = await api.agreements.get(agreement.id);
      setAgreement(updatedAgreement);
    } catch (e: any) {
      console.error(e);
      setErrorMsg('Failed to approve deal: ' + e.message);
    } finally {
      setIsApproving(false);
    }
  };

  const handlePayNow = async () => {
    if (!agreement) return;
    try {
      setPaymentStatus('initializing');
      setErrorMsg(null);
      const paymentInfo = await api.payments.initiate(agreement.id);
      
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID || 'rzp_test_TUpL4wSvURspvK',
        amount: paymentInfo.amount_paise,
        currency: paymentInfo.currency,
        name: "NEXORA",
        description: "Deal Payment - " + agreement.id.split('-')[0],
        order_id: paymentInfo.razorpay_order_id,
        handler: function (response: any) {
          // DO NOT TRUST FRONTEND CALLBACK FOR FINAL CONFIRMATION
          // ENTER VERIFYING STATE TO POLL BACKEND
          setPaymentStatus('verifying');
        },
        prefill: {
          name: "Nexora Buyer",
          email: "buyer@nexora.ai",
        },
        theme: {
          color: "#333333"
        },
        modal: {
            ondismiss: function() {
                setPaymentStatus('idle');
            }
        }
      };
      
      const rzp = new (window as any).Razorpay(options);
      rzp.on('payment.failed', function (response: any){
          setErrorMsg(response.error.description || 'Payment failed');
          setPaymentStatus('failed');
      });
      rzp.open();
    } catch (e: any) {
      console.error(e);
      let errMsg = 'PAYMENT CHECKOUT UNAVAILABLE';
      if (e.message && e.message.includes('blocked')) errMsg = 'PAYMENT BLOCKED: ' + e.message;
      else if (e.message) errMsg = e.message;
      setErrorMsg(errMsg);
      setPaymentStatus('blocked');
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-[999] bg-[#EAE8DD]/80 flex items-center justify-center backdrop-blur-sm">
        <div className="bg-[#FFFDF7] border-4 border-[#111111] p-8 max-w-sm w-full shadow-[8px_8px_0_0_rgba(17,17,17,1)] flex flex-col items-center">
          <div className="w-8 h-8 border-4 border-[#333333] border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="font-bold text-[#333333] uppercase tracking-widest text-sm">LOADING AGREEMENT...</p>
        </div>
      </div>
    );
  }

  if (errorMsg && !agreement) {
    return (
      <div className="fixed inset-0 z-[999] bg-[#EAE8DD]/80 flex items-center justify-center backdrop-blur-sm">
        <div className="bg-[#FFFDF7] border-4 border-[#111111] p-8 max-w-sm w-full shadow-[8px_8px_0_0_rgba(17,17,17,1)] flex flex-col items-center">
           <h2 className="text-xl font-bold text-[#D9534F] uppercase tracking-widest mb-4">ERROR</h2>
           <p className="font-mono text-sm text-[#333333] text-center mb-6">{errorMsg}</p>
           <button 
            className="w-full bg-[#333333] text-white border-2 border-[#111111] py-3 font-bold uppercase tracking-widest hover:bg-[#111111] transition-colors" 
            onClick={onDismiss}
           >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[999] bg-[#EAE8DD]/80 flex items-center justify-center backdrop-blur-sm animate-in fade-in duration-500">
      <div className="bg-[#FFFDF7] border-4 border-[#111111] p-8 max-w-md w-full shadow-[8px_8px_0_0_rgba(17,17,17,1)] flex flex-col items-center pointer-events-auto relative">
        
        {/* Decorative Close Button */}
        <button onClick={onDismiss} className="absolute top-4 right-4 text-[#888888] hover:text-[#333333] font-bold">✕</button>

        <div className="w-16 h-16 bg-[#5CB85C] rounded-full border-4 border-[#111111] flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold font-sans text-[#333333] mb-1 uppercase tracking-tight text-center">Deal Approved</h2>
        <p className="text-xs text-[#888888] uppercase tracking-widest mb-6 text-center font-bold">Negotiation Complete</p>
        
        <p className="text-sm font-mono text-[#333333] text-center mb-6">
          Buyer and Merchant have reached a commercial agreement.
        </p>

        <div className="w-full bg-[#EAE8DD] p-4 border-2 border-[#111111] font-mono text-sm space-y-3 mb-6">
           <div className="flex justify-between items-end border-b border-[#333333]/20 pb-2">
             <span className="text-[#888888] text-xs">AGREEMENT</span>
             <span className="font-bold">#{agreement?.id?.split('-')[0].toUpperCase()}</span>
           </div>
           <div className="flex justify-between items-end border-b border-[#333333]/20 pb-2">
             <span className="text-[#888888] text-xs">PRODUCT</span>
             <span className="font-bold text-right truncate max-w-[150px]">{agreement?.product_name || 'Agreed Product'}</span>
           </div>
           <div className="flex justify-between items-end border-b border-[#333333]/20 pb-2">
             <span className="text-[#888888] text-xs">QUANTITY</span>
             <span className="font-bold">{agreement?.quantity} UNITS</span>
           </div>
           <div className="flex justify-between items-end border-b border-[#333333]/20 pb-2">
             <span className="text-[#888888] text-xs">FINAL PRICE</span>
             <span className="font-bold">₹{Number(agreement?.unit_price).toLocaleString('en-IN')}</span>
           </div>
           <div className="flex justify-between items-end pb-1 pt-1">
             <span className="text-[#333333] font-bold">TOTAL</span>
             <span className="font-bold text-lg text-[#5CB85C]">₹{Number(agreement?.total_amount).toLocaleString('en-IN')}</span>
           </div>
        </div>
        
        <div className="w-full space-y-1 mb-6 font-mono text-xs uppercase font-bold">
           <div className="flex items-center gap-2 text-[#5CB85C]">
              <span>✓</span><span>POLICY APPROVED</span>
           </div>
           <div className="flex items-center gap-2 text-[#5CB85C]">
              <span>✓</span><span>AGREEMENT FINALIZED</span>
           </div>
        </div>

        {errorMsg && paymentStatus === 'blocked' && (
           <div className="w-full mb-6 p-3 bg-red-50 border-2 border-[#D9534F] text-[#D9534F] text-xs font-mono">
              <strong>PAYMENT BLOCKED:</strong><br/>{errorMsg}
           </div>
        )}
        
        {errorMsg && paymentStatus === 'failed' && (
           <div className="w-full mb-6 p-3 bg-red-50 border-2 border-[#D9534F] text-[#D9534F] text-xs font-mono">
              <strong>PAYMENT ERROR:</strong><br/>{errorMsg}
           </div>
        )}
        
        {approvalRequest && approvalRequest.status === 'pending' && (
           <div className="w-full mb-6 p-4 bg-[#FFFDF7] border-2 border-[#111111] text-[#333333] text-sm font-mono shadow-[4px_4px_0_0_rgba(17,17,17,1)]">
              <div className="font-bold uppercase text-[#D9534F] mb-2">HUMAN APPROVAL REQUIRED ⚠</div>
              <p className="mb-4">This transaction exceeds the merchant's autonomous limit.</p>
              <div className="flex justify-between border-b border-[#333333]/20 pb-1 mb-1">
                <span>Deal Total</span>
                <span className="font-bold">₹{Number(agreement?.total_amount).toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between pb-1 mb-4">
                <span>Auto Limit</span>
                <span className="font-bold text-[#D9534F]">₹5,00,000</span>
              </div>
              <div className="flex justify-between font-bold text-xs">
                <span>STATUS:</span>
                <span className="animate-pulse">● PENDING APPROVAL</span>
              </div>
              <div className="text-center mt-4 text-[#888888] text-xs">
                WAITING FOR HUMAN
              </div>
              <button 
                className="w-full mt-4 bg-[#f0ad4e] text-[#111111] border-2 border-[#111111] py-2 font-bold uppercase tracking-widest shadow-[4px_4px_0_0_rgba(17,17,17,1)] hover:bg-[#eea236] active:translate-y-1 active:shadow-none transition-all disabled:opacity-50 text-xs"
                onClick={handleApprove}
                disabled={isApproving}
              >
                {isApproving ? 'APPROVING...' : 'APPROVE DEAL'}
              </button>
           </div>
        )}

        {approvalRequest && approvalRequest.status === 'approved' && (
           <div className="w-full mb-6 p-3 bg-green-50 border-2 border-[#5CB85C] text-[#5CB85C] text-xs font-mono font-bold flex items-center justify-center gap-2">
              ✓ HUMAN APPROVAL APPROVED
           </div>
        )}

        {approvalRequest && approvalRequest.status === 'rejected' && (
           <div className="w-full mb-6 p-3 bg-red-50 border-2 border-[#D9534F] text-[#D9534F] text-xs font-mono font-bold flex items-center justify-center gap-2">
              ✕ HUMAN APPROVAL REJECTED
           </div>
        )}
        
        <div className="w-full flex flex-col gap-3">
          <button 
            className="w-full bg-[#5BC0DE] text-[#111111] border-2 border-[#111111] py-3 font-bold uppercase tracking-widest shadow-[4px_4px_0_0_rgba(17,17,17,1)] hover:bg-[#46b8da] active:translate-y-1 active:shadow-none transition-all disabled:opacity-50" 
            onClick={handleDownloadReport}
          >
            VIEW DEAL REPORT
          </button>

          {paymentStatus === 'confirmed' ? (
             <div className="w-full bg-[#5CB85C] text-white border-2 border-[#111111] py-3 font-bold uppercase tracking-widest shadow-[4px_4px_0_0_rgba(17,17,17,1)] flex justify-center items-center gap-2">
               ✓ PAYMENT CONFIRMED
             </div>
          ) : (
             <button 
               className="w-full bg-[#5CB85C] text-[#111111] border-2 border-[#111111] py-3 font-bold uppercase tracking-widest shadow-[4px_4px_0_0_rgba(17,17,17,1)] hover:bg-[#4cae4c] active:translate-y-1 active:shadow-none transition-all flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed" 
               onClick={handlePayNow}
               disabled={paymentStatus === 'initializing' || paymentStatus === 'verifying' || (approvalRequest && approvalRequest.status !== 'approved')}
             >
               {paymentStatus === 'initializing' ? 'INITIALIZING PAYMENT...' : 
                paymentStatus === 'verifying' ? 'VERIFYING PAYMENT...' : 'PAY NOW'}
             </button>
          )}
        </div>
      </div>
    </div>
  );
};
