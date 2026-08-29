export type AgentType = "buyer" | "merchant";

export type AgentState =
  | "idle"
  | "thinking"
  | "preparing_offer"
  | "sending"
  | "waiting"
  | "negotiating"
  | "policy_check"
  | "accepted"
  | "blocked"
  | "deal_complete";

export type NegotiationEventType =
  | "negotiation_started"
  | "message"
  | "offer"
  | "counteroffer"
  | "policy_check"
  | "policy_result"
  | "approval_required"
  | "acceptance"
  | "rejection"
  | "agreement_created"
  | "payment_ready"
  | "negotiation_completed"
  | "negotiation_failed";

export interface NegotiationEvent {
  id: string;
  timestamp: string;
  agent?: AgentType;
  type: NegotiationEventType;
  message?: string;
  state?: AgentState;
  offer?: {
    unitPrice?: string;
    quantity?: number;
    discountPercent?: string;
    deliveryDays?: number;
    total?: string;
    currency?: string;
  };
  policy?: {
    status: "pending" | "approved" | "blocked";
    reasons?: string[];
  };
  negotiationId?: string;
  isHistorical?: boolean;
}

export interface SimulationState {
  buyerState: AgentState;
  merchantState: AgentState;
  policyStatus: "idle" | "validating" | "approved" | "blocked";
  currentOffer: NegotiationEvent["offer"] | null;
  dealStatus: "live" | "complete" | "failed";
  roundCount: number;
  events: NegotiationEvent[];
  activeMessage: {
    text: string;
    sender: AgentType;
    visible: boolean;
  } | null;
  movingDocument: {
    visible: boolean;
    from: AgentType | "policy";
    to: AgentType | "policy";
    type: "offer" | "counteroffer" | "result";
  } | null;
}
