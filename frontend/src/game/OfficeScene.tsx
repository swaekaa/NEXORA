import React, { useEffect, useRef } from 'react';
import * as PIXI from 'pixi.js';
import { useGame } from './GameContext';
import { LAYOUT } from './constants';
import { SimulationState } from './types';
import { createFloorAndWalls } from './environment/FloorAndWalls';
import { drawWorkstation } from './environment/Workstations';
import { createPolicyCore } from './environment/PolicyCoreVisuals';
import { createDecorations } from './environment/Decorations';
import { createLighting } from './environment/Lighting';

export const OfficeScene: React.FC = () => {
  const { state } = useGame();
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<PIXI.Application | null>(null);
  
  const stateRef = useRef<SimulationState>(state);
  
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    if (!canvasRef.current) return;

    // Initialize raw Pixi Application
    const app = new PIXI.Application({
      width: LAYOUT.OFFICE_WIDTH,
      height: LAYOUT.OFFICE_HEIGHT,
      backgroundColor: 0xEAE8DD,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true,
      antialias: false,
    });
    
    // Add canvas to DOM
    const canvas = app.view as HTMLCanvasElement;
    
    // Make the canvas responsive to fill the parent while maintaining aspect ratio
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.objectFit = 'contain';
    canvas.style.imageRendering = 'pixelated';
    
    canvasRef.current.appendChild(canvas);
    appRef.current = app;

    // ==========================================
    // STAGE 2 & 7: ENVIRONMENT (Bottom layer)
    // ==========================================
    const envContainer = createFloorAndWalls(LAYOUT.OFFICE_WIDTH, LAYOUT.OFFICE_HEIGHT);
    app.stage.addChild(envContainer);
    
    const decContainer = createDecorations(LAYOUT.OFFICE_WIDTH, LAYOUT.OFFICE_HEIGHT);
    app.stage.addChild(decContainer);

    // ==========================================
    // STAGE 3 & 4: WORKSTATIONS
    // ==========================================
    const stationsG = new PIXI.Graphics();
    app.stage.addChild(stationsG);
    
    const stationsContainer = new PIXI.Container();
    app.stage.addChild(stationsContainer);
    
    drawWorkstation(stationsG, stationsContainer, LAYOUT.BUYER_DESK.x, LAYOUT.BUYER_DESK.y, true);
    drawWorkstation(stationsG, stationsContainer, LAYOUT.MERCHANT_DESK.x, LAYOUT.MERCHANT_DESK.y, false);

    // ==========================================
    // STAGE 5: NEGOTIATION TABLE
    // ==========================================
    const tableG = new PIXI.Graphics();
    app.stage.addChild(tableG);
    
    const tx = LAYOUT.MEETING_TABLE.x;
    const ty = LAYOUT.MEETING_TABLE.y;
    
    // Shadow
    tableG.beginFill(0x000000, 0.2);
    tableG.drawRect(tx - 110, ty - 10, 220, 60);
    tableG.endFill();
    
    // Main Table Body (Rich Mahogany)
    tableG.beginFill(0x5C3A21);
    tableG.lineStyle(2, 0x111111);
    tableG.drawRect(tx - 100, ty - 35, 200, 70);
    tableG.endFill();
    
    // Center Plant
    tableG.beginFill(0x8B4513); tableG.drawRect(tx - 10, ty - 10, 20, 15);
    tableG.beginFill(0x228B22); tableG.lineStyle(1, 0x006400); tableG.drawCircle(tx, ty - 20, 15); tableG.endFill();
    
    // Papers/Documents on table
    tableG.beginFill(0xFFFFFF); tableG.lineStyle(1, 0x333333); tableG.drawRect(tx - 70, ty - 20, 20, 30); tableG.endFill();
    tableG.beginFill(0xFFFFFF); tableG.lineStyle(1, 0x333333); tableG.drawRect(tx + 50, ty - 20, 20, 30); tableG.endFill();

    // ==========================================
    // STAGE 6: POLICY CORE
    // ==========================================
    const policyContainer = new PIXI.Container();
    app.stage.addChild(policyContainer);
    createPolicyCore(policyContainer, LAYOUT.POLICY_ENGINE.x, LAYOUT.POLICY_ENGINE.y);
    
    // Policy Core Status Light Graphic (Updated dynamically)
    const policyStatusG = new PIXI.Graphics();
    policyContainer.addChild(policyStatusG);

    // ==========================================
    // CHARACTERS & DIALOGUE (Top Layers)
    // ==========================================
    const buyerContainer = new PIXI.Container();
    const merchantContainer = new PIXI.Container();
    app.stage.addChild(buyerContainer);
    app.stage.addChild(merchantContainer);
    
    const buyerG = new PIXI.Graphics();
    buyerContainer.addChild(buyerG);
    const buyerName = new PIXI.Text('Alex', new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 10, fill: '#5BC0DE', fontWeight: 'bold', stroke: '#111111', strokeThickness: 2 }));
    buyerName.anchor.set(0.5); buyerName.y = 28; buyerContainer.addChild(buyerName);
    
    const merchantG = new PIXI.Graphics();
    merchantContainer.addChild(merchantG);
    const merchantName = new PIXI.Text('Morgan', new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 10, fill: '#D9534F', fontWeight: 'bold', stroke: '#111111', strokeThickness: 2 }));
    merchantName.anchor.set(0.5); merchantName.y = 28; merchantContainer.addChild(merchantName);

    // Dialogues moved to HTML DOM for crisp text rendering

    const renderAgent = (g: PIXI.Graphics, color: number) => {
      g.clear();
      g.beginFill(0x000000, 0.15); g.lineStyle(0); g.drawEllipse(0, 35, 20, 8); g.endFill(); // shadow
      g.beginFill(color); g.lineStyle(2, 0x111111); g.drawRect(-15, -15, 30, 30); g.endFill(); // body
      g.beginFill(0xF5DEB3); g.lineStyle(2, 0x111111); g.drawRect(-10, -35, 20, 20); g.endFill(); // head
      g.beginFill(0x111111); g.lineStyle(0); g.drawRect(-4, -28, 3, 3); g.drawRect(4, -28, 3, 3); g.endFill(); // eyes
      g.beginFill(0x222222); g.lineStyle(2, 0x111111); g.drawRect(-25, 20, 50, 16); g.endFill(); // plate
    };
    
    // (Bubbles rendered in React DOM)

    renderAgent(buyerG, 0x5BC0DE);
    renderAgent(merchantG, 0xD9534F);

    // Initial agent positions
    let buyerPos = { ...LAYOUT.BUYER_DESK };
    let merchantPos = { ...LAYOUT.MERCHANT_DESK };

    // ==========================================
    // DOCUMENT (Moving Envelope)
    // ==========================================
    const docContainer = new PIXI.Container();
    app.stage.addChild(docContainer);
    const docG = new PIXI.Graphics();
    docContainer.addChild(docG);
    
    const renderDoc = (g: PIXI.Graphics, isResult: boolean, isApproved: boolean) => {
      g.clear();
      g.beginFill(0xFFFFFF); g.lineStyle(2, 0x111111); g.drawRect(-12, -8, 24, 16);
      g.moveTo(-12, -8); g.lineTo(0, 0); g.lineTo(12, -8); g.endFill();
      if (isResult) {
        g.beginFill(isApproved ? 0x5CB85C : 0xD9534F); g.lineStyle(0); g.drawCircle(0, 0, 4); g.endFill();
      }
    };

    // ==========================================
    // LIGHTING (Topmost layer, blend mode)
    // ==========================================
    const lightingOverlay = createLighting(LAYOUT.OFFICE_WIDTH, LAYOUT.OFFICE_HEIGHT, LAYOUT.BUYER_DESK, LAYOUT.MERCHANT_DESK, LAYOUT.POLICY_ENGINE);
    app.stage.addChild(lightingOverlay);

    // ==========================================
    // STAGE 8: TICKER / ANIMATION LOOP
    // ==========================================
    let frame = 0;

    app.ticker.add(() => {
      const s = stateRef.current;
      frame++;
      
      // Idle Animations (Subtle bobbing)
      const bIdleOffset = (s.buyerState === 'idle') ? Math.sin(frame * 0.05) * 2 : 0;
      const mIdleOffset = (s.merchantState === 'idle') ? Math.sin(frame * 0.05 + 1) * 2 : 0;

      // Determine Target Positions
      const tBuyerPos = (s.buyerState === 'sending' || s.buyerState === 'negotiating' || s.buyerState === 'accepted') 
        ? LAYOUT.MEETING_BUYER_POS : LAYOUT.BUYER_DESK;
        
      const tMerchantPos = (s.merchantState === 'sending' || s.merchantState === 'negotiating' || s.merchantState === 'accepted')
        ? LAYOUT.MEETING_MERCHANT_POS : LAYOUT.MERCHANT_DESK;
        
      // Interpolate Positions
      buyerPos.x += (tBuyerPos.x - buyerPos.x) * 0.05;
      buyerPos.y += (tBuyerPos.y - buyerPos.y) * 0.05;
      merchantPos.x += (tMerchantPos.x - merchantPos.x) * 0.05;
      merchantPos.y += (tMerchantPos.y - merchantPos.y) * 0.05;
      
      buyerContainer.x = buyerPos.x;
      buyerContainer.y = buyerPos.y + bIdleOffset;
      merchantContainer.x = merchantPos.x;
      merchantContainer.y = merchantPos.y + mIdleOffset;

      // Update Policy Core Lights
      policyStatusG.clear();
      const isBlinking = s.policyStatus === 'validating';
      const isApproved = s.policyStatus === 'approved';
      const isBlocked = s.policyStatus === 'blocked';
      let pColor = 0x888888;
      if (isBlinking && Math.floor(frame / 10) % 2 === 0) pColor = 0xF0AD4E;
      if (isApproved) pColor = 0x5CB85C;
      if (isBlocked) pColor = 0xD9534F;
      
      policyStatusG.beginFill(pColor);
      policyStatusG.lineStyle(1, 0x111111);
      policyStatusG.drawRect(LAYOUT.POLICY_ENGINE.x - 20, LAYOUT.POLICY_ENGINE.y + 45, 40, 6);
      policyStatusG.endFill();

      // Update Dialogues (handled by React state now)

      // Update Document
      if (s.movingDocument?.visible) {
        docContainer.visible = true;
        const getPos = (entity: string) => {
          if (entity === 'buyer') return LAYOUT.BUYER_DESK;
          if (entity === 'merchant') return LAYOUT.MERCHANT_DESK;
          if (entity === 'policy') return LAYOUT.POLICY_ENGINE;
          return { x: 0, y: 0 };
        };
        const start = getPos(s.movingDocument.from);
        const end = getPos(s.movingDocument.to);
        
        const dx = end.x - docContainer.x;
        const dy = end.y - docContainer.y;
        
        if (Math.abs(docContainer.x - end.x) > 400 && Math.abs(docContainer.x - start.x) > 10) {
           docContainer.x = start.x;
           docContainer.y = start.y;
        } else {
           docContainer.x += dx * 0.05;
           docContainer.y += dy * 0.05;
        }

        renderDoc(docG, s.movingDocument.type === 'result', s.policyStatus === 'approved');
      } else {
        docContainer.visible = false;
        docContainer.x = -100;
      }
    });

    return () => {
      app.destroy(true, true);
    };
  }, []);

  // Calculate DOM overlay percentages based on 1200x600 layout
  const buyerBubbleStyle = {
    left: '45.83%', // (550 / 1200)
    top: '44.16%',  // ((350 - 85) / 600)
    transform: 'translate(-50%, -50%)',
  };

  const merchantBubbleStyle = {
    left: '54.16%', // (650 / 1200)
    top: '44.16%',
    transform: 'translate(-50%, -50%)',
  };

  return (
    <div className="absolute inset-0 flex items-center justify-center overflow-hidden z-0">
      <div className="relative w-full max-h-full aspect-[2/1] flex items-center justify-center">
        <div ref={canvasRef} className="absolute inset-0 w-full h-full" style={{ imageRendering: 'pixelated' }} />
        
        {/* HTML DOM Dialogue Bubbles for crystal clear text */}
        {state.activeMessage?.visible && state.activeMessage.sender === 'buyer' && (
          <div className="absolute z-10 w-48 bg-white border-2 border-[#111111] p-3 text-sm font-sans text-center text-[#333333] shadow-[4px_4px_0_0_rgba(17,17,17,1)]" style={buyerBubbleStyle}>
            {state.activeMessage.text}
            <div className="absolute -bottom-[10px] left-1/2 -translate-x-1/2 w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[10px] border-t-[#111111]"></div>
            <div className="absolute -bottom-[6px] left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-white"></div>
          </div>
        )}

        {state.activeMessage?.visible && state.activeMessage.sender === 'merchant' && (
          <div className="absolute z-10 w-48 bg-white border-2 border-[#111111] p-3 text-sm font-sans text-center text-[#333333] shadow-[4px_4px_0_0_rgba(17,17,17,1)]" style={merchantBubbleStyle}>
            {state.activeMessage.text}
            <div className="absolute -bottom-[10px] left-1/2 -translate-x-1/2 w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[10px] border-t-[#111111]"></div>
            <div className="absolute -bottom-[6px] left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-white"></div>
          </div>
        )}
      </div>
    </div>
  );
};
