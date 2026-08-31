import { NegotiationEvent } from '../types';
import { api } from '../../api';

export type EventCallback = (event: NegotiationEvent) => void;

export interface NegotiationEventStream {
  subscribe(callback: EventCallback): void;
  unsubscribe(callback: EventCallback): void;
  start(negotiationId?: string): void;
  stop(): void;
}

export class IdleEventStream implements NegotiationEventStream {
  subscribe(_callback: EventCallback) {}
  unsubscribe(_callback: EventCallback) {}
  start(_negotiationId?: string) {}
  stop() {}
}

export class MockEventStream implements NegotiationEventStream {
  private callbacks: EventCallback[] = [];
  private timer: number | null = null;
  private eventIndex = 0;

  // A predetermined sequence of events for the demo
  private demoEvents: NegotiationEvent[] = [
    { id: '1', timestamp: new Date().toISOString(), type: 'negotiation_started' },
    { id: '2', timestamp: new Date().toISOString(), type: 'message', agent: 'buyer', state: 'preparing_offer', message: 'I need 100 office chairs.' },
    { 
      id: '3', timestamp: new Date().toISOString(), type: 'offer', agent: 'buyer', state: 'sending', 
      offer: { unitPrice: '820.00', quantity: 100 } 
    },
    { id: '4', timestamp: new Date().toISOString(), type: 'message', agent: 'merchant', state: 'thinking' },
    { 
      id: '5', timestamp: new Date().toISOString(), type: 'counteroffer', agent: 'merchant', state: 'sending', 
      message: 'I can supply 100 units at 920 each.', offer: { unitPrice: '920.00', quantity: 100 } 
    },
    { id: '6', timestamp: new Date().toISOString(), type: 'message', agent: 'buyer', state: 'thinking', message: 'That is above my target. Can you do 850?' },
    { 
      id: '7', timestamp: new Date().toISOString(), type: 'counteroffer', agent: 'buyer', state: 'sending', 
      offer: { unitPrice: '850.00', quantity: 100 } 
    },
    { id: '8', timestamp: new Date().toISOString(), type: 'policy_check', state: 'policy_check' },
    { id: '9', timestamp: new Date().toISOString(), type: 'policy_result', policy: { status: 'approved' } },
    { id: '10', timestamp: new Date().toISOString(), type: 'message', agent: 'merchant', state: 'thinking', message: '850 works with 5-day delivery.' },
    { 
      id: '11', timestamp: new Date().toISOString(), type: 'counteroffer', agent: 'merchant', state: 'sending', 
      offer: { unitPrice: '850.00', quantity: 100, deliveryDays: 5 } 
    },
    { id: '12', timestamp: new Date().toISOString(), type: 'acceptance', agent: 'buyer', state: 'accepted' },
    { id: '13', timestamp: new Date().toISOString(), type: 'agreement_created' },
    { id: '14', timestamp: new Date().toISOString(), type: 'negotiation_completed', state: 'deal_complete' },
  ];

  subscribe(callback: EventCallback) {
    this.callbacks.push(callback);
  }

  unsubscribe(callback: EventCallback) {
    this.callbacks = this.callbacks.filter(cb => cb !== callback);
  }

  start(_negotiationId?: string) {
    this.eventIndex = 0;
    this.nextEvent();
  }

  stop() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private nextEvent() {
    if (this.eventIndex >= this.demoEvents.length) return;
    
    const event = this.demoEvents[this.eventIndex++];
    this.callbacks.forEach(cb => cb(event));

    // Delay next event by 5-7 seconds for realism so users can read
    const delay = 5000 + Math.random() * 2000;
    this.timer = window.setTimeout(() => this.nextEvent(), delay);
  }
}

export class LiveEventStream implements NegotiationEventStream {
  private callbacks: EventCallback[] = [];
  private timer: number | null = null;
  private negotiationId: string | null = null;
  private processedMessageIds = new Set<string>();
  private isCompleted = false;
  private isInitialFetch = true;

  subscribe(callback: EventCallback) {
    this.callbacks.push(callback);
  }

  unsubscribe(callback: EventCallback) {
    this.callbacks = this.callbacks.filter(cb => cb !== callback);
  }

  start(negotiationId?: string) {
    if (negotiationId) {
      this.negotiationId = negotiationId;
    }
    
    if (!this.negotiationId) {
      console.error("LiveEventStream requires a negotiationId");
      return;
    }
    
    this.processedMessageIds.clear();
    this.isCompleted = false;
    this.isInitialFetch = true;
    
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    
    // Initial fetch, then start polling
    this.poll();
  }

  stop() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.isCompleted = true;
  }

  private async poll() {
    if (!this.negotiationId || this.isCompleted) return;

    try {
      // Fetch messages and negotiation status
      const negotiation = await api.negotiations.get(this.negotiationId);
      const messages = await api.negotiations.getMessages(this.negotiationId);
      const auditEvents = await api.audit.listForMerchant(negotiation.merchant_id);

      // Filter audit events for this specific negotiation
      const negotiationAudits = auditEvents.filter(a => a.negotiation_id === this.negotiationId);

      // Create a combined array of new events
      const allEvents: any[] = [];
      
      messages.forEach(msg => {
        if (!this.processedMessageIds.has(msg.id)) {
          allEvents.push({ type: 'message_record', data: msg, timestamp: new Date(msg.created_at).getTime() });
        }
      });
      
      negotiationAudits.forEach(audit => {
        if (!this.processedMessageIds.has(audit.id)) {
          allEvents.push({ type: 'audit_record', data: audit, timestamp: new Date(audit.created_at).getTime() });
        }
      });

      // Sort by timestamp
      allEvents.sort((a, b) => a.timestamp - b.timestamp);

      // Convert backend records to frontend events
      for (const record of allEvents) {
        if (record.type === 'message_record') {
          const msg = record.data;
          this.processedMessageIds.add(msg.id);

          let agentType: "buyer" | "merchant" | undefined = undefined;
          if (msg.sender_type === 'buyer_agent') agentType = 'buyer';
          else if (msg.sender_type === 'merchant_agent') agentType = 'merchant';

          let eventType: any = "message";
          let state: any = "sending";

          if (msg.message_type === "offer") eventType = "offer";
          else if (msg.message_type === "counter_offer") eventType = "counteroffer";
          else if (msg.message_type === "accept") {
              eventType = "acceptance";
              state = "accepted";
          } else if (msg.message_type === "reject") {
              eventType = "rejection";
              state = "blocked";
          }

          const event: NegotiationEvent = {
            id: msg.id,
            timestamp: msg.created_at,
            agent: agentType,
            type: eventType,
            message: msg.content || undefined,
            state: state,
            isHistorical: this.isInitialFetch,
          };

          if (msg.payload && (msg.payload.unit_price || msg.payload.quantity)) {
            event.offer = {
              unitPrice: msg.payload.unit_price,
              quantity: msg.payload.quantity,
              total: msg.payload.total_amount,
              currency: msg.payload.currency,
            };
          }
          
          this.callbacks.forEach(cb => cb(event));
          
        } else if (record.type === 'audit_record') {
          const audit = record.data;
          this.processedMessageIds.add(audit.id);

          if (audit.event_type === 'POLICY_CHECK') {
            const policyCheck: NegotiationEvent = { 
              id: audit.id, 
              timestamp: audit.created_at, 
              type: 'policy_check', 
              state: 'policy_check',
              isHistorical: this.isInitialFetch,
            };
            this.callbacks.forEach(cb => cb(policyCheck));
            
            const decision = audit.metadata?.decision;
            if (decision) {
              const policyResult: NegotiationEvent = { 
                id: audit.id + '-result', 
                timestamp: audit.created_at, 
                type: 'policy_result', 
                policy: { status: decision.toLowerCase() },
                isHistorical: this.isInitialFetch,
              };
              this.callbacks.forEach(cb => cb(policyResult));
            }
          }
        }
      }
      
      // Check for terminal state based on Backend enum
      if (negotiation.state === "accepted" || negotiation.state === "rejected" || negotiation.state === "expired") {
          if (!this.processedMessageIds.has("terminal-" + negotiation.id)) {
            this.processedMessageIds.add("terminal-" + negotiation.id);
            const terminalEvent: NegotiationEvent = {
               id: "terminal-" + negotiation.id,
               timestamp: new Date().toISOString(),
               type: negotiation.state === "accepted" ? "agreement_created" : "negotiation_failed",
               state: negotiation.state === "accepted" ? "deal_complete" : "blocked",
               isHistorical: this.isInitialFetch,
            };
            this.callbacks.forEach(cb => cb(terminalEvent));
          }
          this.stop();
          return;
      }

      this.isInitialFetch = false;

    } catch (e) {
      console.error("Error polling live negotiation stream", e);
    }

    if (!this.isCompleted) {
       this.timer = window.setTimeout(() => this.poll(), 2000); // 2 second polling as requested
    }
  }
}

