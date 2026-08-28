import React, { useCallback } from 'react';
import { Graphics, Text } from '@pixi/react';
import { useGame } from '../GameContext';
import { LAYOUT } from '../constants';
import * as PIXI from 'pixi.js';

export const PolicyEngine: React.FC = () => {
  const { state } = useGame();

  const drawServer = useCallback((g: PIXI.Graphics) => {
    g.clear();
    
    // Shadow
    g.beginFill(0x000000, 0.2);
    g.drawEllipse(0, 30, 20, 8);
    g.endFill();
    
    // Body (Yellow)
    g.beginFill(0xF0AD4E);
    g.lineStyle(2, 0x333333);
    g.drawRect(-15, -15, 30, 30);
    g.endFill();
    
    // Head
    g.beginFill(0xF5DEB3);
    g.lineStyle(2, 0x333333);
    g.drawRect(-10, -35, 20, 20);
    g.endFill();
    
    // Eyes
    g.beginFill(0x333333);
    g.lineStyle(0, 0);
    g.drawRect(-4, -28, 3, 3);
    g.drawRect(4, -28, 3, 3);
    g.endFill();
    
    // Name Plate
    g.beginFill(0x333333);
    g.drawRect(-25, 20, 50, 24); // Taller for status
    g.endFill();
    
    // Status Indicator Square
    const isBlinking = state.policyStatus === 'validating';
    const isApproved = state.policyStatus === 'approved';
    const isBlocked = state.policyStatus === 'blocked';
    
    let color = 0x888888; // idle
    if (isBlinking && Math.floor(Date.now() / 200) % 2 === 0) color = 0xF0AD4E; 
    if (isApproved) color = 0x5CB85C; 
    if (isBlocked) color = 0xD9534F; 
    
    g.beginFill(color);
    g.lineStyle(1, 0x000000);
    g.drawRect(-20, 33, 40, 4);
    g.endFill();

  }, [state.policyStatus]);

  return (
    <>
      <Graphics draw={drawServer} x={LAYOUT.POLICY_ENGINE.x} y={LAYOUT.POLICY_ENGINE.y} />
      <Text 
        text="Iris" 
        x={LAYOUT.POLICY_ENGINE.x} 
        y={LAYOUT.POLICY_ENGINE.y + 26} 
        anchor={0.5} 
        style={new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 10, fill: '#F0AD4E', fontWeight: 'bold' })} 
      />
      <Text 
        text={state.policyStatus.toUpperCase()} 
        x={LAYOUT.POLICY_ENGINE.x} 
        y={LAYOUT.POLICY_ENGINE.y + 35} 
        anchor={0.5} 
        style={new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 6, fill: '#FFFFFF' })} 
      />
    </>
  );
};
