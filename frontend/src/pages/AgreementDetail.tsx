import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileCheck, CreditCard, Lock } from 'lucide-react';
import { api } from '../api';

export default function AgreementDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [agreement, setAgreement] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [paymentInitiating, setPaymentInitiating] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.agreements.get(id)
      .then(setAgreement)
      .catch(err => alert("Failed to load agreement: " + err.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handlePayment = async () => {
    if (!agreement) return;
    setPaymentInitiating(true);
    try {
      const res = await api.payments.initiate(agreement.id);
      
      // Simulate Razorpay popup success for MVP
      setTimeout(() => {
        setPaymentSuccess(true);
        setPaymentInitiating(false);
      }, 1500);
      
      /* Actual Razorpay integration would look like this:
      const options = {
        key: 'rzp_test_...', // Enter the Key ID generated from the Dashboard
        amount: res.amount_paise,
        currency: res.currency,
        name: 'NEXORA',
        description: 'Agreement Payment',
        order_id: res.razorpay_order_id,
        handler: function (response: any) {
          setPaymentSuccess(true);
        },
      };
      const rzp1 = new (window as any).Razorpay(options);
      rzp1.open();
      */
    } catch (err: any) {
      alert("Payment failed: " + (err.message || err));
      setPaymentInitiating(false);
    }
  };

  const formatPrice = (price: string) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(price));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!agreement) return null;

  return (
    <div className="max-w-3xl mx-auto animate-fade-in-up pb-20">
      <div className="mb-6 flex items-center gap-4">
        <button onClick={() => navigate('/merchant')} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-white">Agreement #{agreement.id.split('-')[0]}</h1>
            <span className={`status-pill ${
              agreement.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              agreement.status === 'PENDING_APPROVAL' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
              'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {agreement.status.replace('_', ' ')}
            </span>
          </div>
          <p className="text-sm text-slate-400 font-mono">
            Generated from Negotiation {agreement.negotiation_id.split('-')[0]}
          </p>
        </div>
      </div>

      <div className="glass-panel p-8 relative overflow-hidden mb-8">
        <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-bl-full -z-10" />
        <FileCheck className="absolute top-8 right-8 text-emerald-500/20" size={64} />
        
        <h2 className="text-xl font-bold text-white mb-6 border-b border-slate-700 pb-4">Digital Contract Terms</h2>
        
        <div className="grid grid-cols-2 gap-y-6 gap-x-12">
          <div>
            <div className="text-xs text-slate-500 font-mono mb-1">PRODUCT</div>
            <div className="text-slate-200 font-medium">{agreement.product_name}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono mb-1">QUANTITY</div>
            <div className="text-slate-200 font-medium">{agreement.quantity} Units</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono mb-1">UNIT PRICE</div>
            <div className="text-slate-200 font-medium">{formatPrice(agreement.unit_price)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono mb-1">DETERMINISTIC TOTAL</div>
            <div className="text-emerald-400 font-bold text-xl">{formatPrice(agreement.total_amount)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono mb-1">PAYMENT TERMS</div>
            <div className="text-slate-200 font-medium uppercase">{agreement.payment_terms}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono mb-1">DELIVERY</div>
            <div className="text-slate-200 font-medium">{agreement.delivery_days} Days</div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-700 flex items-start gap-3 text-sm text-slate-400">
          <Lock size={16} className="text-slate-500 flex-shrink-0 mt-0.5" />
          <p>
            This agreement is immutable and mathematically verified. The total amount is computed deterministically by the system based on the unit price and quantity agreed upon by the agents.
          </p>
        </div>
      </div>

      {agreement.status === 'APPROVED' && !paymentSuccess && (
        <div className="glass-panel p-6 border border-emerald-500/20 bg-emerald-500/5 text-center flex flex-col items-center">
          <h3 className="text-lg font-bold text-white mb-2">Ready for Execution</h3>
          <p className="text-slate-400 mb-6 text-sm max-w-md">
            This agreement has been approved and validated. Initiate payment to secure the inventory and finalize the contract.
          </p>
          <button 
            onClick={handlePayment}
            disabled={paymentInitiating}
            className="glass-button bg-emerald-500/20 text-emerald-300 border-emerald-500/50 hover:bg-emerald-500/30 flex items-center gap-2 px-8 py-3 text-lg font-bold disabled:opacity-50"
          >
            {paymentInitiating ? (
              <div className="w-5 h-5 border-2 border-emerald-200 border-t-transparent rounded-full animate-spin" />
            ) : (
              <CreditCard size={20} />
            )}
            Pay {formatPrice(agreement.total_amount)}
          </button>
        </div>
      )}

      {paymentSuccess && (
        <div className="glass-panel p-6 border border-blue-500/20 bg-blue-500/5 text-center">
          <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="text-blue-400" size={32} />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Payment Successful</h3>
          <p className="text-slate-400 text-sm">
            The transaction has been processed. The inventory has been reserved and the fulfillment process has started.
          </p>
        </div>
      )}
    </div>
  );
}

// Dummy CheckCircle since it's used in the payment success block
function CheckCircle(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}
