import { useState } from 'react';

const SESSION_KEY = 'nexora_active_negotiation_id';

export function useNegotiationSession() {
  const [activeNegotiationId, setActiveId] = useState<string | null>(() => {
    return localStorage.getItem(SESSION_KEY);
  });

  const setActiveNegotiationId = (id: string) => {
    localStorage.setItem(SESSION_KEY, id);
    setActiveId(id);
  };

  const clearSession = () => {
    localStorage.removeItem(SESSION_KEY);
    setActiveId(null);
  };

  return {
    activeNegotiationId,
    setActiveNegotiationId,
    clearSession,
  };
}
