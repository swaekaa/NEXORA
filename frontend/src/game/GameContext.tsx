import React, { createContext, useContext, useMemo } from 'react';
import { SimulationState } from './types';
import { useGameEngine } from './state/GameState';
import { NegotiationEventStream } from './state/EventStream';

interface GameContextProps {
  state: SimulationState;
  dispatch: React.Dispatch<any>;
}

const GameContext = createContext<GameContextProps | null>(null);

export const GameProvider: React.FC<{ stream: NegotiationEventStream; children: React.ReactNode }> = ({ stream, children }) => {
  const { state, dispatch } = useGameEngine(stream);

  const value = useMemo(() => ({ state, dispatch }), [state, dispatch]);

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
};

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};
