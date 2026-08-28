import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Agreement } from '../types/models';

export default function AgreementDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [agreement, setAgreement] = useState<Agreement | null>(null);

  useEffect(() => {
    async function load() {
      if (!id) return;
      try {
        const data = await api.agreements.get(id);
        setAgreement(data);
      } catch (err) {
        console.error(err);
      }
    }
    load();
  }, [id]);

  if (!agreement) {
    return <div className="text-center pt-32 animate-pulse text-slate-500 tracking-widest font-mono">LOADING AGREEMENT...</div>;
  }

  const formatPrice = (price: string) => `₹${Number(price).toLocaleString('en-IN')}`;

  return (
    <div className="w-full h-full pt-20 px-8 flex justify-center items-start">
      <div className="w-full max-w-2xl pixel-panel border-amber-500/30 bg-[#FFFBEB] shadow-[8px_8px_0_0_rgba(245,158,11,0.2)]">
        
        {/* Paper Contract Header */}
        <div className="border-b-2 border-amber-900/20 px-8 py-6 text-amber-900 bg-[url('https://www.transparenttextures.com/patterns/rice-paper-2.png')]">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold tracking-widest uppercase mb-1">FINAL AGREEMENT</h1>
              <p className="text-amber-800/60 text-sm font-mono tracking-widest">NEXORA PLATFORM GENERATED</p>
            </div>
            <div className="border-2 border-amber-800 px-3 py-1 font-bold text-amber-800">
              ID: {agreement.id.split('-')[0]}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 font-mono text-sm">
            <div>
              <div className="text-amber-700/60">DATE OF ENACTMENT</div>
              <div className="font-bold">{new Date(agreement.created_at).toLocaleDateString()}</div>
            </div>
            <div>
              <div className="text-amber-700/60">STATUS</div>
              <div className="font-bold text-emerald-600">✓ VALIDATED & ACTIVE</div>
            </div>
          </div>
        </div>
        
        {/* Terms Section */}
        <div className="px-8 py-6 text-amber-950 font-mono">
          <h2 className="text-xl font-bold mb-6 border-b-2 border-amber-900/10 pb-2">COMMERCIAL TERMS</h2>
          
          <div className="space-y-4">
            <div className="flex justify-between border-b border-amber-900/10 pb-2">
              <span className="text-amber-800">ASSET IDENTIFIER</span>
              <span className="font-bold">{agreement.product_id}</span>
            </div>
            
            <div className="flex justify-between border-b border-amber-900/10 pb-2">
              <span className="text-amber-800">UNIT PRICE</span>
              <span className="font-bold">{formatPrice(agreement.agreed_terms.unit_price)}</span>
            </div>
            
            <div className="flex justify-between border-b border-amber-900/10 pb-2">
              <span className="text-amber-800">QUANTITY</span>
              <span className="font-bold">{agreement.agreed_terms.quantity} UNITS</span>
            </div>
            
            <div className="flex justify-between pt-4 mt-6 border-t-4 border-amber-900 border-double">
              <span className="text-xl font-bold">TOTAL OBLIGATION</span>
              <span className="text-xl font-bold text-emerald-700">{formatPrice(agreement.agreed_terms.total_amount)}</span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="bg-slate-900 border-t-2 border-slate-700 p-4 flex justify-between items-center">
          <button 
            onClick={() => navigate('/merchant')}
            className="pixel-button text-xs"
          >
            BACK TO DEALS
          </button>
          
          <button className="pixel-button pixel-button-primary text-xs">
            INITIATE PAYMENT
          </button>
        </div>
      </div>
    </div>
  );
}
