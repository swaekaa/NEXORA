export interface NegotiationMessagePayload {
  product_id: string;
  quantity: number;
  unit_price: string;
  discount_percent: string;
  total_amount: string;
  currency: string;
}

export interface NegotiationMessage {
  id: string;
  negotiation_id: string;
  sender_type: 'buyer_agent' | 'merchant_agent' | 'system';
  sender_id: string;
  sequence_number: number;
  message_type: 'OFFER' | 'COUNTER_OFFER' | 'ACCEPT' | 'REJECT' | 'INFO';
  content: string;
  payload: NegotiationMessagePayload | null;
  created_at: string;
}

export interface Negotiation {
  id: string;
  buyer_id: string;
  merchant_id: string;
  product_id: string;
  state: 'offer' | 'counter_offer' | 'accepted' | 'rejected' | 'expired';
  round_count: number;
  max_rounds: number;
  created_at: string;
  updated_at: string;
}

export interface Agreement {
  id: string;
  negotiation_id: string;
  merchant_id: string;
  buyer_id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  total_amount: string;
  currency: string;
  payment_terms: string;
  delivery_days: number;
  warranty_months: number;
  status: 'pending_validation' | 'validated' | 'pending_approval' | 'approved' | 'validation_failed' | 'payment_initiated' | 'payment_captured' | 'payment_failed' | 'expired' | 'cancelled';
  policy_decision: 'ALLOW' | 'REVIEW' | 'DENY' | 'HUMAN_APPROVAL_REQUIRED' | null;
  policy_checks: any[] | null;
  blocking_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalRequest {
  id: string;
  agreement_id: string;
  merchant_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  policy_decision: string;
  reason: string;
  resolution_reason: string | null;
  requested_at: string;
  resolved_at: string | null;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  negotiation_id: string | null;
  agreement_id: string | null;
  merchant_id: string | null;
  metadata: any;
  created_at: string;
}

export interface Policy {
  id: string;
  merchant_id: string;
  name: string;
  minimum_price: string;
  maximum_discount_percent: string;
  maximum_autonomous_transaction: string;
  human_approval_required: boolean;
  is_active: boolean;
  max_negotiation_rounds: number;
  max_delivery_days: number;
  min_warranty_months: number;
  created_at: string;
  updated_at: string;
}

export interface PolicyCreate {
  name?: string;
  minimum_price: string;
  maximum_discount_percent?: string;
  maximum_autonomous_transaction: string;
  human_approval_required?: boolean;
  is_active?: boolean;
  max_negotiation_rounds?: number;
  max_delivery_days?: number;
  min_warranty_months?: number;
}
