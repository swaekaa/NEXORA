import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Graphics, Text } from '@pixi/react';
import { useGame } from '../GameContext';
import { LAYOUT } from '../constants';
import * as PIXI from 'pixi.js';

export const BuyerAgent: React.FC = () => {
  const { state } = useGame();
  const [pos, setPos] = useState(LAYOUT.BUYER_DESK);
  
  // Interpolation for smooth movement
  const targetPos = useRef(LAYOUT.BUYER_DESK);
  
  useEffect(() => {
    // Update target position based on state
    if (state.buyerState === 'sending' || state.buyerState === 'negotiating' || state.buyerState === 'accepted') {
      targetPos.current = LAYOUT.MEETING_BUYER_POS;
    } else {
      targetPos.current = LAYOUT.BUYER_DESK;
    }
  }, [state.buyerState]);

  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setPos(prev => {
        const dx = targetPos.current.x - prev.x;
        const dy = targetPos.current.y - prev.y;
        if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return targetPos.current;
        return {
          x: prev.x + dx * 0.05,
          y: prev.y + dy * 0.05
        };
      });
      animationFrame = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animationFrame);
  }, []);

  const drawAgent = useCallback((g: PIXI.Graphics) => {
    g.clear();
    // Shadow
    g.beginFill(0x000000, 0.2);
    g.drawEllipse(0, 30, 20, 8);
    g.endFill();
    
    // Body (Teal)
    g.beginFill(0x5BC0DE);
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
    g.drawRect(-25, 20, 50, 16);
    g.endFill();

    // Message Bubble Background if active
    if (state.activeMessage?.sender === 'buyer' && state.activeMessage.visible) {
      g.beginFill(0xFFFFFF);
      g.lineStyle(2, 0x333333);
      g.drawRect(-60, -110, 120, 45);
      
      // Bubble tail
      g.beginFill(0xFFFFFF);
      g.lineStyle(2, 0x333333);
      g.moveTo(-5, -65);
      g.lineTo(0, -50);
      g.lineTo(10, -65);
      g.endFill();
      
      // Clear line through tail base
      g.beginFill(0xFFFFFF);
      g.lineStyle(0, 0);
      g.moveTo(-4, -66);
      g.lineTo(9, -66);
      g.lineTo(9, -64);
      g.lineTo(-4, -64);
      g.endFill();
    }

  }, [state.buyerState, state.activeMessage]);

  return (
    <>
      <Graphics draw={drawAgent} x={pos.x} y={pos.y} />
      <Text 
        text="Alex" 
        x={pos.x} 
        y={pos.y + 28} 
        anchor={0.5} 
        style={new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 10, fill: '#5BC0DE', fontWeight: 'bold' })} 
      />
      
      {state.activeMessage?.sender === 'buyer' && state.activeMessage.visible && (
        <Text 
          text={state.activeMessage.text} 
          x={pos.x} 
          y={pos.y - 88} 
          anchor={0.5} 
          style={new PIXI.TextStyle({ 
            fontFamily: 'sans-serif', 
            fontSize: 10, 
            fill: '#333333',
            wordWrap: true,
            wordWrapWidth: 110,
            align: 'center'
          })} 
        />
      )}
    </>
  );
};
