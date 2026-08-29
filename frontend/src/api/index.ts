import { fetchApi } from './client';
import { Negotiation, NegotiationMessage, Agreement, ApprovalRequest, AuditEvent, Policy, PolicyCreate } from '../types/models';

export const api = {
  policies: {
    create: (merchantId: string, policy: PolicyCreate) => 
      fetchApi<Policy>(`/merchants/${merchantId}/policies`, { method: 'POST', body: JSON.stringify(policy) }),
    list: (merchantId: string) => 
      fetchApi<{ items: Policy[]; total: number }>(`/merchants/${merchantId}/policies`),
    get: (merchantId: string, policyId: string) => 
      fetchApi<Policy>(`/merchants/${merchantId}/policies/${policyId}`),
  },
  buyers: {
    runAgent: (buyerId: string, intent: any) => 
      fetchApi<{ run_id: string; status: string; negotiation_id: string | null; error_reason: string | null }>(
        `/buyers/${buyerId}/agent/runs`, 
        { method: 'POST', body: JSON.stringify(intent) }
      ),
  },
  merchants: {
    runAgent: (merchantId: string, negotiationId: string) => 
      fetchApi<{ run_id: string; status: string; error_reason: string | null }>(
        `/merchants/${merchantId}/agent/runs/${negotiationId}`, 
        { method: 'POST' }
      ),
  },
  negotiations: {
    get: (id: string) => fetchApi<Negotiation>(`/negotiations/${id}`),
    getMessages: (id: string) => fetchApi<NegotiationMessage[]>(`/negotiations/${id}/messages`),
    listForMerchant: (merchantId: string) => fetchApi<Negotiation[]>(`/merchants/${merchantId}/negotiations`),
  },
  agreements: {
    get: (id: string) => fetchApi<Agreement>(`/agreements/${id}`),
    listForMerchant: (merchantId: string) => fetchApi<Agreement[]>(`/merchants/${merchantId}/agreements`),
  },
  approvals: {
    list: (merchantId: string) => fetchApi<ApprovalRequest[]>(`/merchants/${merchantId}/approvals`),
    approve: (merchantId: string, id: string) => fetchApi<ApprovalRequest>(`/merchants/${merchantId}/approvals/${id}/approve`, { method: 'POST' }),
    reject: (merchantId: string, id: string, reason: string) => fetchApi<ApprovalRequest>(`/merchants/${merchantId}/approvals/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
  },
  audit: {
    listForMerchant: (merchantId: string) => fetchApi<AuditEvent[]>(`/merchants/${merchantId}/audit`),
  },
  payments: {
    initiate: (agreementId: string) => fetchApi<{ payment_id: string; razorpay_order_id: string; amount_paise: number; currency: string; status: string }>(
      `/payments/initiate`,
      { method: 'POST', body: JSON.stringify({ agreement_id: agreementId }) }
    ),
  }
};
