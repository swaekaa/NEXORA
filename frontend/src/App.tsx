import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';
import AppShell from './components/layout/AppShell';
import BuyerPage from './pages/BuyerPage';
import NegotiationDetail from './pages/NegotiationDetail';
import MerchantDashboard from './pages/MerchantDashboard';
import AgreementDetail from './pages/AgreementDetail';
import PolicyPage from './pages/PolicyPage';
import AuditTrailPage from './pages/AuditTrailPage';
import DealReport from './pages/DealReport';
import ToolsPage from './pages/ToolsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/office" replace />} />
          <Route path="office" element={<NegotiationDetail />} />
          <Route path="agents" element={<BuyerPage />} />
          <Route path="negotiations/:id" element={<NegotiationDetail />} />
          <Route path="deals" element={<MerchantDashboard />} />
          <Route path="deals/:id" element={<AgreementDetail />} />
          <Route path="policies" element={<PolicyPage />} />
          <Route path="audit" element={<AuditTrailPage />} />
          <Route path="tools" element={<ToolsPage />} />
        </Route>
        <Route path="/deals/:agreementId/report" element={<DealReport />} />
      </Routes>
      <Analytics />
    </BrowserRouter>
  );
}
