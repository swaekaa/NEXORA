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
import { PixelSpeechBubble } from '../components/PixelSpeechBubble';

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
      resizeTo: canvasRef.current,
      backgroundColor: 0xEAE8DD,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true,
      antialias: false,
    });
    
    // Add canvas to DOM
    const canvas = app.view as HTMLCanvasElement;
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.display = 'block';
    canvas.style.imageRendering = 'pixelated';
    
    canvasRef.current.appendChild(canvas);
    appRef.current = app;

    // The main container that holds the entire 1200x600 logical scene
    const gameWorld = new PIXI.Container();
    app.stage.addChild(gameWorld);

    // ==========================================
    // STAGE 2 & 7: ENVIRONMENT (Bottom layer)
    // ==========================================
    const envContainer = createFloorAndWalls(LAYOUT.OFFICE_WIDTH, LAYOUT.OFFICE_HEIGHT);
    gameWorld.addChild(envContainer);
    
    const decContainer = createDecorations(LAYOUT.OFFICE_WIDTH, LAYOUT.OFFICE_HEIGHT);
    gameWorld.addChild(decContainer);

    // ==========================================
    // STAGE 3 & 4: WORKSTATIONS
    // ==========================================
    const stationsG = new PIXI.Graphics();
    gameWorld.addChild(stationsG);
    
    const stationsContainer = new PIXI.Container();
    gameWorld.addChild(stationsContainer);
    
    drawWorkstation(stationsG, stationsContainer, LAYOUT.BUYER_DESK.x, LAYOUT.BUYER_DESK.y, true);
    drawWorkstation(stationsG, stationsContainer, LAYOUT.MERCHANT_DESK.x, LAYOUT.MERCHANT_DESK.y, false);

    // ==========================================
    // STAGE 5: NEGOTIATION TABLE
    // ==========================================
    const tableG = new PIXI.Graphics();
    gameWorld.addChild(tableG);
    
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
    gameWorld.addChild(policyContainer);
    createPolicyCore(policyContainer, LAYOUT.POLICY_ENGINE.x, LAYOUT.POLICY_ENGINE.y);
    
    // Policy Core Status Light Graphic (Updated dynamically)
    const policyStatusG = new PIXI.Graphics();
    policyContainer.addChild(policyStatusG);

    // ==========================================
    // CHARACTERS & DIALOGUE (Top Layers)
    // ==========================================
    const buyerContainer = new PIXI.Container();
    const merchantContainer = new PIXI.Container();
    gameWorld.addChild(buyerContainer);
    gameWorld.addChild(merchantContainer);
    
    const buyerG = new PIXI.Graphics();
    buyerContainer.addChild(buyerG);
    const buyerName = new PIXI.Text('Alex', new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 10, fill: '#5BC0DE', fontWeight: 'bold', stroke: '#111111', strokeThickness: 2 }));
    buyerName.anchor.set(0.5); buyerName.y = 28; buyerContainer.addChild(buyerName);
    
    const merchantG = new PIXI.Graphics();
    merchantContainer.addChild(merchantG);
    const merchantName = new PIXI.Text('Morgan', new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 10, fill: '#D9534F', fontWeight: 'bold', stroke: '#111111', strokeThickness: 2 }));
    merchantName.anchor.set(0.5); merchantName.y = 28; merchantContainer.addChild(merchantName);

    // Dialogues moved to HTML DOM for crisp text rendering

    const renderAgent = (g: PIXI.Graphics, color: number, isBuyer: boolean) => {
      g.clear();
      // Chair shadow (blocky)
      g.beginFill(0x000000, 0.2); g.lineStyle(0); g.drawRect(-22, 32, 44, 12); g.endFill();
      
      // Chair backrest (dark grey/black)
      g.beginFill(0x222222); g.lineStyle(2, 0x111111);
      g.drawRect(-18, -10, 36, 40);
      g.endFill();
      
      // Arms (resting on desk or chair arms)
      g.beginFill(color); g.lineStyle(2, 0x111111);
      g.drawRect(-22, 5, 8, 16); // Left arm
      g.drawRect(14, 5, 8, 16); // Right arm
      g.endFill();

      // Hands (blocky)
      g.beginFill(0xF5DEB3); g.lineStyle(1, 0x111111);
      g.drawRect(-20, 20, 4, 4); // Left hand
      g.drawRect(16, 20, 4, 4); // Right hand
      g.endFill();

      // Body / Suit (shirt + tie for merchant, casual jacket for buyer)
      g.beginFill(color); g.lineStyle(2, 0x111111);
      g.drawRect(-14, -10, 28, 30); 
      g.endFill();
      
      // Shirt inner V
      g.beginFill(0xFFFFFF); g.lineStyle(0);
      g.drawPolygon([-6, -10, 6, -10, 0, 5]);
      g.endFill();

      if (!isBuyer) {
        // Red tie for Merchant
        g.beginFill(0xD9534F); g.lineStyle(1, 0x111111);
        g.drawPolygon([-2, -8, 2, -8, 0, 4]);
        g.endFill();
      } else {
        // Lanyard for Buyer
        g.beginFill(0x333333);
        g.drawRect(-5, -10, 2, 12);
        g.drawRect(3, -10, 2, 12);
        g.beginFill(0x5BC0DE); g.lineStyle(1, 0x111111);
        g.drawRect(-3, 2, 6, 8);
        g.endFill();
      }

      // Head
      g.beginFill(0xF5DEB3); g.lineStyle(2, 0x111111);
      g.drawRect(-10, -32, 20, 22);
      g.endFill();

      // Hair
      g.beginFill(isBuyer ? 0x8B4513 : 0x2F4F4F); g.lineStyle(2, 0x111111);
      if (isBuyer) {
        // Messy hair
        g.drawRect(-12, -36, 24, 8);
        g.drawRect(-14, -32, 4, 10);
        g.drawRect(10, -32, 4, 6);
      } else {
        // Neat hair
        g.drawRect(-10, -35, 20, 6);
        g.drawRect(-12, -32, 2, 12);
      }
      g.endFill();

      // Eyes
      g.beginFill(0x111111); g.lineStyle(0);
      g.drawRect(-5, -24, 3, 3);
      g.drawRect(2, -24, 3, 3);
      g.endFill();
      
      // Glasses for merchant
      if (!isBuyer) {
        g.lineStyle(1, 0x111111);
        g.drawRect(-6, -25, 5, 4);
        g.drawRect(1, -25, 5, 4);
        g.moveTo(-1, -23); g.lineTo(1, -23);
      }

      // Desk Nameplate (front)
      g.beginFill(0x222222); g.lineStyle(2, 0x111111); 
      g.drawRect(-25, 28, 50, 16); 
      g.endFill();
    };
    
    renderAgent(buyerG, 0x5BC0DE, true);
    renderAgent(merchantG, 0xD9534F, false);

    // Initial agent positions
    let buyerPos = { ...LAYOUT.BUYER_DESK };
    let merchantPos = { ...LAYOUT.MERCHANT_DESK };

    // ==========================================
    // DOCUMENT (Moving Envelope)
    // ==========================================
    const docContainer = new PIXI.Container();
    gameWorld.addChild(docContainer);
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
    gameWorld.addChild(lightingOverlay);

    // ==========================================
    // STAGE 8: TICKER / ANIMATION LOOP
    // ==========================================
    let frame = 0;

    app.ticker.add(() => {
      const s = stateRef.current;
      frame++;
      
      // Center the game world in the dynamically sized app screen
      gameWorld.x = Math.floor((app.screen.width - LAYOUT.OFFICE_WIDTH) / 2);
      gameWorld.y = Math.floor((app.screen.height - LAYOUT.OFFICE_HEIGHT) / 2);

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

  return (
    <div className="absolute inset-0 flex items-center justify-center overflow-hidden z-0">
      <div className="relative w-full h-full flex items-center justify-center">
        <div ref={canvasRef} className="absolute inset-0 w-full h-full" style={{ imageRendering: 'pixelated' }} />
        
        <PixelSpeechBubble 
           agent="buyer" 
           message={state.activeMessage?.text || ""} 
           visible={state.activeMessage?.visible === true && state.activeMessage.sender === 'buyer'} 
        />
        
        <PixelSpeechBubble 
           agent="merchant" 
           message={state.activeMessage?.text || ""} 
           visible={state.activeMessage?.visible === true && state.activeMessage.sender === 'merchant'} 
        />
      </div>
    </div>
  );
};
