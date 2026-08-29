import { createContext, useContext, useEffect, useReducer, useState } from 'react';
import { NegotiationEvent, SimulationState, AgentState } from '../types';
import { NegotiationEventStream } from './EventStream';

const initialState: SimulationState = {
  buyerState: 'idle',
  merchantState: 'idle',
  policyStatus: 'idle',
  currentOffer: null,
  dealStatus: 'live',
  roundCount: 0,
  events: [],
  activeMessage: null,
  movingDocument: null,
};

type Action = 
  | { type: 'ADD_EVENT'; payload: NegotiationEvent }
  | { type: 'SET_ACTIVE_MESSAGE'; payload: { text: string; sender: 'buyer' | 'merchant' } | null }
  | { type: 'START_DOCUMENT_MOVE'; payload: { from: any; to: any; type: any } }
  | { type: 'END_DOCUMENT_MOVE' }
  | { type: 'RESET' };

function gameReducer(state: SimulationState, action: Action): SimulationState {
  switch (action.type) {
    case 'ADD_EVENT': {
      const event = action.payload;
      const newState = { ...state, events: [...state.events, event] };
      
      if (event.offer) {
        newState.currentOffer = event.offer;
      }
      
      if (event.agent === 'buyer' && event.state) {
        newState.buyerState = event.state;
      }
      
      if (event.agent === 'merchant' && event.state) {
        newState.merchantState = event.state;
      }
      
      if (event.type === 'policy_check') {
        newState.policyStatus = 'validating';
        newState.buyerState = 'policy_check';
        newState.merchantState = 'policy_check';
      }
      
      if (event.type === 'policy_result' && event.policy) {
        newState.policyStatus = event.policy.status as 'approved' | 'blocked';
        newState.buyerState = 'idle';
        newState.merchantState = 'idle';
      }

      if (event.type === 'offer' || event.type === 'counteroffer') {
        newState.roundCount += 1;
      }

      if (event.state === 'deal_complete') {
        newState.dealStatus = 'complete';
        newState.buyerState = 'deal_complete';
        newState.merchantState = 'deal_complete';
      }
      
      if (event.type === 'negotiation_failed') {
        newState.dealStatus = 'failed';
      }

      return newState;
    }
    case 'SET_ACTIVE_MESSAGE':
      return { ...state, activeMessage: action.payload ? { ...action.payload, visible: true } : null };
    case 'START_DOCUMENT_MOVE':
      return { ...state, movingDocument: { ...action.payload, visible: true } };
    case 'END_DOCUMENT_MOVE':
      return { ...state, movingDocument: null };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useGameEngine(stream: NegotiationEventStream) {
  const [state, dispatch] = useReducer(gameReducer, initialState);

  useEffect(() => {
    const handleEvent = (event: NegotiationEvent) => {
      dispatch({ type: 'ADD_EVENT', payload: event });
      
      // Auto-trigger visual side-effects based on events
      if (!event.isHistorical) {
        if (event.message && event.agent) {
          dispatch({ type: 'SET_ACTIVE_MESSAGE', payload: { text: event.message, sender: event.agent } });
          // Hide message after a few seconds (increased to 7s for readability)
          setTimeout(() => dispatch({ type: 'SET_ACTIVE_MESSAGE', payload: null }), 7000);
        }

        if (event.type === 'offer' || event.type === 'counteroffer') {
          const from = event.agent === 'buyer' ? 'buyer' : 'merchant';
          const to = event.agent === 'buyer' ? 'merchant' : 'buyer';
          dispatch({ type: 'START_DOCUMENT_MOVE', payload: { from, to, type: 'offer' } });
          setTimeout(() => dispatch({ type: 'END_DOCUMENT_MOVE' }), 1500); // Animation duration
        }

        if (event.type === 'policy_check') {
          // Document travels to policy engine
          dispatch({ type: 'START_DOCUMENT_MOVE', payload: { from: 'merchant', to: 'policy', type: 'offer' } });
          setTimeout(() => dispatch({ type: 'END_DOCUMENT_MOVE' }), 1000);
        }
        
        if (event.type === 'policy_result') {
          // Document returns from policy engine
          dispatch({ type: 'START_DOCUMENT_MOVE', payload: { from: 'policy', to: 'merchant', type: 'result' } });
          setTimeout(() => dispatch({ type: 'END_DOCUMENT_MOVE' }), 1000);
        }
      }
    };

    stream.subscribe(handleEvent);
    stream.start();

    return () => {
      stream.stop();
      stream.unsubscribe(handleEvent);
    };
  }, [stream]);

  return { state, dispatch };
}
