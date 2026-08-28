import { useState, useEffect, useCallback, useRef } from 'react';

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number = 2000,
  stopCondition: (data: T) => boolean,
  maxDurationMs: number = 300000 // 5 minutes default timeout
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  
  // Use refs to avoid closures capturing stale state
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;
  
  const stopConditionRef = useRef(stopCondition);
  stopConditionRef.current = stopCondition;

  const startTimeRef = useRef(Date.now());

  const poll = useCallback(async () => {
    if (!isPolling) return;
    
    if (Date.now() - startTimeRef.current > maxDurationMs) {
      setIsPolling(false);
      setError(new Error('Negotiation is taking longer than expected.'));
      return;
    }
    try {
      const result = await fetchFnRef.current();
      setData(result);
      if (stopConditionRef.current(result)) {
        setIsPolling(false);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Polling failed'));
      console.error('Polling error:', err);
    }
  }, [isPolling]);

  useEffect(() => {
    poll();
    if (isPolling) {
      const intervalId = setInterval(poll, intervalMs);
      return () => clearInterval(intervalId);
    }
  }, [poll, intervalMs, isPolling]);

  return { data, error, isPolling, stopPolling: () => setIsPolling(false) };
}
