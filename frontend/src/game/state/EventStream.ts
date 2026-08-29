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
  subscribe(callback: EventCallback) {}
  unsubscribe(callback: EventCallback) {}
  start(negotiationId?: string) {}
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

  start(negotiationId?: string) {
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
      const messages = await api.negotiations.getMessages(this.negotiationId);
      const negotiation = await api.negotiations.get(this.negotiationId);

      // Find truly new messages
      const newMessages = messages.filter(msg => !this.processedMessageIds.has(msg.id));

      // Convert backend messages to frontend events
      for (const msg of newMessages) {
        this.processedMessageIds.add(msg.id);

        let agentType: "buyer" | "merchant" | undefined = undefined;
        if (msg.sender_type === 'buyer_agent') agentType = 'buyer';
        else if (msg.sender_type === 'merchant_agent') agentType = 'merchant';

        let eventType: any = "message";
        let state: any = "sending";

        // Map backend message_type exactly
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
        };

        // Correctly parse payload values
        if (msg.payload && (msg.payload.unit_price || msg.payload.quantity)) {
          event.offer = {
            unitPrice: msg.payload.unit_price,
            quantity: msg.payload.quantity,
            total: msg.payload.total_amount,
            currency: msg.payload.currency,
          };
        }
        
        // Notify subscribers
        this.callbacks.forEach(cb => cb(event));

        // SYNTHESIZE POLICY CHECK FOR VISUALIZATION
        // When an offer is made, the opposing agent's deterministic policy engine evaluates it.
        // We trigger this visual sequence while the backend LLM is generating the next response.
        if (eventType === "offer" || eventType === "counteroffer") {
          setTimeout(() => {
             const policyCheck: NegotiationEvent = { 
               id: msg.id + '-pc', 
               timestamp: new Date().toISOString(), 
               type: 'policy_check', 
               state: 'policy_check' 
             };
             this.callbacks.forEach(cb => cb(policyCheck));
             
             setTimeout(() => {
                const policyResult: NegotiationEvent = { 
                  id: msg.id + '-pr', 
                  timestamp: new Date().toISOString(), 
                  type: 'policy_result', 
                  policy: { status: 'approved' } 
                };
                this.callbacks.forEach(cb => cb(policyResult));
             }, 1500); // Policy check takes 1.5s visually
          }, 1000); // Start policy check 1s after offer is received
        }
      }
      
      // Check for terminal state based on Backend enum
      if (negotiation.state === "accepted" || negotiation.state === "rejected" || negotiation.state === "expired") {
          const terminalEvent: NegotiationEvent = {
             id: "terminal-" + negotiation.id,
             timestamp: new Date().toISOString(),
             type: negotiation.state === "accepted" ? "agreement_created" : "negotiation_failed"
          };
          this.callbacks.forEach(cb => cb(terminalEvent));
          this.stop();
          return;
      }

    } catch (e) {
      console.error("Error polling live negotiation stream", e);
    }

    if (!this.isCompleted) {
       this.timer = window.setTimeout(() => this.poll(), 2000); // 2 second polling as requested
    }
  }
}

