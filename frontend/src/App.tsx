import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import BuyerPage from './pages/BuyerPage';
import NegotiationDetail from './pages/NegotiationDetail';
import MerchantDashboard from './pages/MerchantDashboard';
import AgreementDetail from './pages/AgreementDetail';
import AuditPage from './pages/AuditPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/buyer" replace />} />
          <Route path="buyer" element={<BuyerPage />} />
          <Route path="negotiations/:id" element={<NegotiationDetail />} />
          <Route path="merchant" element={<MerchantDashboard />} />
          <Route path="agreements" element={<MerchantDashboard />} />
          <Route path="agreements/:id" element={<AgreementDetail />} />
          <Route path="audit" element={<AuditPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
