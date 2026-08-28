import { NegotiationEvent } from '../types';

export type EventCallback = (event: NegotiationEvent) => void;

export interface NegotiationEventStream {
  subscribe(callback: EventCallback): void;
  unsubscribe(callback: EventCallback): void;
  start(): void;
  stop(): void;
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

  start() {
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
