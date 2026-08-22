/**
 * NEXORA Frontend Type Definitions
 * All monetary values are represented as strings to preserve decimal precision.
 * See docs/AGREEMENT_SPEC.md and docs/API_SPEC.md for schemas.
 */

// ── Enums ─────────────────────────────────────────────────────────────────────

export type NegotiationStatus =
  | "DISCOVER"
  | "REQUEST"
  | "OFFER"
  | "COUNTER_OFFER"
  | "ACCEPT"
  | "REJECT"
  | "EXPIRE"
  | "AGREEMENT_CREATED";

export type AgreementStatus =
  | "PENDING_VALIDATION"
  | "VALIDATED"
  | "VALIDATION_FAILED"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "PAYMENT_INITIATED"
  | "PAYMENT_CAPTURED"
  | "PAYMENT_FAILED"
  | "EXPIRED"
  | "CANCELLED";

export type MessageSender = "buyer_agent" | "merchant_agent" | "system";
export type MessageType = "request" | "offer" | "counteroffer" | "accept" | "reject" | "system_event";
export type PolicyDecision = "PASS" | "FAIL" | "REQUIRES_HUMAN_APPROVAL";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";
export type AuditAction =
  | "NEGOTIATION_STARTED" | "OFFER_GENERATED" | "COUNTEROFFER_SUBMITTED"
  | "OFFER_ACCEPTED" | "OFFER_REJECTED" | "AGREEMENT_CREATED"
  | "POLICY_VALIDATED" | "POLICY_BLOCKED"
  | "PAYMENT_AUTHORIZED" | "PAYMENT_BLOCKED" | "PAYMENT_CAPTURED" | "PAYMENT_FAILED"
  | "PAYMENT_AMOUNT_MISMATCH"
  | "HUMAN_APPROVAL_REQUESTED" | "HUMAN_APPROVED" | "HUMAN_REJECTED"
  | "WEBHOOK_RECEIVED" | "WEBHOOK_DUPLICATE" | "WEBHOOK_INVALID_SIGNATURE"
  | "INVALID_TOOL_ARGS";

// ── Core Entities ─────────────────────────────────────────────────────────────

export interface Product {
  id: string;
  merchant_id: string;
  name: string;
  description: string;
  base_price: string;   // Decimal as string
  currency: string;
  available_stock: number;
}

export interface NegotiationMessage {
  id: string;
  negotiation_id: string;
  sender: MessageSender;
  type: MessageType;
  content: string;
  structured_data?: {
    unit_price?: string;
    quantity?: number;
    delivery_days?: number;
    warranty_months?: number;
    payment_terms?: string;
  };
  tool_call?: string;
  policy_pre_check?: "PASS" | "FAIL" | null;
  round_number: number;
  created_at: string;
}

export interface Negotiation {
  id: string;
  merchant_id: string;
  buyer_id: string;
  product: Product;
  status: NegotiationStatus;
  round_count: number;
  max_rounds: number;
  messages: NegotiationMessage[];
  started_at: string;
  expires_at: string;
}

export interface PolicyCheck {
  rule_name: string;
  passed: boolean;
  expected: string;
  actual: string;
  reason: string;
}

export interface PolicyValidation {
  decision: PolicyDecision;
  checks: PolicyCheck[];
  blocking_reason?: string;
  validated_at?: string;
}

export interface CommercialAgreement {
  id: string;
  merchant_id: string;
  buyer_id: string;
  negotiation_id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;      // Decimal as string
  total_amount: string;    // Decimal as string
  currency: string;
  payment_terms: string;
  delivery_days: number;
  warranty_months: number;
  razorpay_order_id?: string;
  razorpay_payment_id?: string;
  payment_captured_at?: string;
  policy_validation?: PolicyValidation;
  status: AgreementStatus;
  expires_at: string;
  created_at: string;
}

export interface ApprovalRequest {
  id: string;
  agreement_id: string;
  merchant_id: string;
  reason: string;
  proposed_total: string;
  autonomous_limit: string;
  status: ApprovalStatus;
  reviewed_at?: string;
  review_note?: string;
  expires_at: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  session_id?: string;
  agreement_id?: string;
  agent_id: string;
  agent_type: string;
  action: AuditAction;
  input_summary?: string;
  decision?: string;
  policy_checked?: string;
  policy_result?: string;
  razorpay_reference?: string;
  result: string;
  failure_reason?: string;
}

export interface MerchantDashboard {
  active_negotiations: number;
  pending_approvals: number;
  total_agreements: number;
  paid_agreements: number;
  total_revenue: string;
  currency: string;
}

// ── API Request/Response Types ────────────────────────────────────────────────

export interface BuyerSessionResponse {
  session_id: string;
  status: string;
  created_at: string;
}

export interface BuyerMessageResponse {
  agent_response: string;
  negotiation_id?: string;
  negotiation_status?: NegotiationStatus;
  latest_offer?: Partial<CommercialAgreement>;
}

export interface PaymentInitiateResponse {
  razorpay_order_id: string;
  razorpay_key_id: string;
  amount_paise: number;
  currency: string;
  agreement_id: string;
}
