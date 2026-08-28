import React, { useCallback, useEffect, useState } from 'react';
import { Graphics } from '@pixi/react';
import { useGame } from '../GameContext';
import { LAYOUT } from '../constants';
import * as PIXI from 'pixi.js';

export const Document: React.FC = () => {
  const { state } = useGame();
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [active, setActive] = useState(false);
  
  useEffect(() => {
    if (state.movingDocument?.visible) {
      setActive(true);
      
      const getPos = (entity: string) => {
        if (entity === 'buyer') return LAYOUT.BUYER_DESK;
        if (entity === 'merchant') return LAYOUT.MERCHANT_DESK;
        if (entity === 'policy') return LAYOUT.POLICY_ENGINE;
        return { x: 0, y: 0 };
      };
      
      const start = getPos(state.movingDocument.from);
      const end = getPos(state.movingDocument.to);
      
      setPos(start);
      
      let startTime = performance.now();
      const duration = 1000;
      let animationFrame: number;
      
      const animate = (time: number) => {
        const progress = Math.min((time - startTime) / duration, 1);
        // Easing easeInOutQuad
        const ease = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;
        
        setPos({
          x: start.x + (end.x - start.x) * ease,
          y: start.y + (end.y - start.y) * ease
        });
        
        if (progress < 1) {
          animationFrame = requestAnimationFrame(animate);
        } else {
          setActive(false);
        }
      };
      
      animationFrame = requestAnimationFrame(animate);
      return () => cancelAnimationFrame(animationFrame);
    } else {
      setActive(false);
    }
  }, [state.movingDocument]);

  const drawDoc = useCallback((g: PIXI.Graphics) => {
    g.clear();
    if (!active) return;
    
    // Envelope / Document
    g.beginFill(0xFFFFFF);
    g.lineStyle(1, 0x000000);
    g.drawRect(-8, -6, 16, 12);
    
    // Flap
    g.moveTo(-8, -6);
    g.lineTo(0, 0);
    g.lineTo(8, -6);
    g.endFill();
    
    if (state.movingDocument?.type === 'result') {
      // Mark with color
      const color = state.policyStatus === 'approved' ? 0x22C55E : 0xEF4444;
      g.beginFill(color);
      g.drawCircle(0, 0, 3);
      g.endFill();
    }
  }, [active, state.movingDocument, state.policyStatus]);

  if (!active) return null;

  return <Graphics draw={drawDoc} x={pos.x} y={pos.y} />;
};
