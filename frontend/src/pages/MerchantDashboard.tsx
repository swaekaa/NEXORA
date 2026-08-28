import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Negotiation } from '../types/models';

export default function MerchantDashboard() {
  const [negotiations, setNegotiations] = useState<Negotiation[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const data = await api.negotiations.listForMerchant("merch_556677");
        setNegotiations(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="w-full h-full pt-20 px-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold tracking-widest text-slate-200 mb-2">DEAL ARCHIVE</h1>
          <p className="text-slate-500 uppercase tracking-widest text-sm">Select a terminal to view negotiation history</p>
        </div>

        {loading ? (
          <div className="text-center text-slate-500 animate-pulse mt-20">ACCESSING ARCHIVE...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {negotiations.map(deal => (
              <div 
                key={deal.id} 
                className="pixel-panel flex flex-col group cursor-pointer hover:-translate-y-1 transition-transform"
                onClick={() => navigate(`/negotiations/${deal.id}`)}
              >
                <div className="pixel-panel-header">
                  <span>TERMINAL #{deal.id.split('-')[0]}</span>
                  <span className={`w-2 h-2 ${
                    deal.state === 'ACCEPTED' ? 'bg-emerald-500' : 
                    deal.state === 'REJECTED' ? 'bg-rose-500' : 'bg-blue-500 animate-pulse'
                  }`} />
                </div>
                <div className="p-6 flex-1 flex flex-col">
                  <div className="text-sm text-slate-500 mb-2">ASSET</div>
                  <div className="text-xl font-bold text-slate-200 mb-6 truncate">{deal.product_id}</div>
                  
                  <div className="mt-auto border-t-2 border-slate-800 pt-4 flex justify-between items-end">
                    <div>
                      <div className="text-sm text-slate-500 mb-1">STATUS</div>
                      <div className={`font-bold uppercase ${
                        deal.state === 'ACCEPTED' ? 'text-emerald-400' : 
                        deal.state === 'REJECTED' ? 'text-rose-400' : 'text-blue-400'
                      }`}>
                        {deal.state.replace('_', ' ')}
                      </div>
                    </div>
                    <button className="pixel-button text-xs py-1 px-3">ENTER</button>
                  </div>
                </div>
              </div>
            ))}
            
            {negotiations.length === 0 && (
              <div className="col-span-full text-center text-slate-500 py-12 border-2 border-dashed border-slate-800">
                NO DEALS FOUND IN ARCHIVE
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
