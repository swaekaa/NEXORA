import React, { useEffect, useRef, useState } from 'react';
import * as PIXI from 'pixi.js';

// Set global scale mode for crisp pixel art
PIXI.BaseTexture.defaultOptions.scaleMode = PIXI.SCALE_MODES.NEAREST;
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
  const [summaryAgent, setSummaryAgent] = useState<'buyer' | 'merchant' | null>(null);
  
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
    
    // Table Shadow
    tableG.beginFill(0x000000, 0.25);
    tableG.drawRect(tx - 110, ty - 10, 220, 60);
    tableG.endFill();
    
    // Pushed-in Chairs (Backside, bottom edge of table)
    const drawTableChair = (cx: number) => {
      tableG.beginFill(0x2F4F4F); tableG.lineStyle(2, 0x111111);
      tableG.drawRect(cx - 15, ty + 25, 30, 20); // seat
      tableG.drawRect(cx - 15, ty + 15, 30, 10); // backrest
      tableG.drawRect(cx - 18, ty + 20, 3, 15); // left arm
      tableG.drawRect(cx + 15, ty + 20, 3, 15); // right arm
    };
    drawTableChair(tx - 40);
    drawTableChair(tx + 40);

    // Main Table Body (Rich Mahogany)
    tableG.beginFill(0x5C3A21);
    tableG.lineStyle(2, 0x111111);
    tableG.drawRect(tx - 100, ty - 35, 200, 70);
    tableG.endFill();
    
    // Center Plant (Moved slightly up to keep animation path clear)
    tableG.beginFill(0x8B4513); tableG.lineStyle(1, 0x111111); tableG.drawRect(tx - 8, ty - 25, 16, 12); 
    tableG.beginFill(0x228B22); tableG.lineStyle(1, 0x006400); tableG.drawCircle(tx, ty - 30, 12); tableG.endFill();
    
    // Papers/Documents on table
    tableG.beginFill(0xFFFFFF); tableG.lineStyle(1, 0x333333); 
    tableG.drawRect(tx - 70, ty - 20, 20, 25); // buyer side doc
    tableG.drawRect(tx + 50, ty - 20, 20, 25); // merchant side doc
    
    // Central Contract Folder (Open)
    tableG.beginFill(0xD2B48C); tableG.lineStyle(1, 0x8B4513);
    tableG.drawRect(tx - 25, ty - 5, 50, 30); // folder
    tableG.beginFill(0xFFFFFF); tableG.lineStyle(1, 0x333333);
    tableG.drawRect(tx - 22, ty - 2, 20, 24); // left page
    tableG.drawRect(tx + 2, ty - 2, 20, 24); // right page
    tableG.beginFill(0x555555); tableG.lineStyle(0);
    tableG.drawRect(tx - 20, ty + 2, 16, 2); tableG.drawRect(tx - 20, ty + 6, 10, 2); // text
    tableG.drawRect(tx + 4, ty + 2, 16, 2); tableG.drawRect(tx + 4, ty + 6, 14, 2); // text
    tableG.endFill();

    // Coffee Mugs
    tableG.beginFill(0xFFFFFF); tableG.lineStyle(1, 0x333333); tableG.drawCircle(tx - 40, ty - 10, 4);
    tableG.beginFill(0x111111); tableG.lineStyle(1, 0x333333); tableG.drawCircle(tx + 35, ty + 10, 4);
    tableG.endFill();

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
    
    // Draw shadow for Buyer
    const buyerBase = new PIXI.Graphics();
    buyerBase.beginFill(0x000000, 0.2); buyerBase.lineStyle(0); buyerBase.drawEllipse(0, 32, 30, 8); buyerBase.endFill();
    buyerContainer.addChild(buyerBase);
    
    const buyerSprite = PIXI.Sprite.from('/buyer.png');
    buyerSprite.anchor.set(0.5, 0.85);
    buyerSprite.width = 96;
    buyerSprite.height = 96;
    buyerSprite.eventMode = 'static';
    buyerSprite.cursor = 'pointer';
    buyerSprite.on('pointerdown', () => setSummaryAgent('buyer'));
    buyerContainer.addChild(buyerSprite);

    const buyerName = new PIXI.Text('Jake', new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 16, fill: '#5BC0DE', fontWeight: '900', stroke: '#111111', strokeThickness: 4, letterSpacing: 1 }));
    buyerName.anchor.set(0.5); buyerName.y = -105; buyerContainer.addChild(buyerName);
    
    // Draw shadow for Merchant
    const merchantBase = new PIXI.Graphics();
    merchantBase.beginFill(0x000000, 0.2); merchantBase.lineStyle(0); merchantBase.drawEllipse(0, 32, 30, 8); merchantBase.endFill();
    merchantContainer.addChild(merchantBase);

    const merchantSprite = PIXI.Sprite.from('/merchant.png');
    merchantSprite.anchor.set(0.5, 0.85);
    merchantSprite.width = 96;
    merchantSprite.height = 96;
    merchantSprite.eventMode = 'static';
    merchantSprite.cursor = 'pointer';
    merchantSprite.on('pointerdown', () => setSummaryAgent('merchant'));
    merchantContainer.addChild(merchantSprite);

    const merchantName = new PIXI.Text('Holt', new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 16, fill: '#D9534F', fontWeight: '900', stroke: '#111111', strokeThickness: 4, letterSpacing: 1 }));
    merchantName.anchor.set(0.5); merchantName.y = -105; merchantContainer.addChild(merchantName);

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
      
      // Scale and center the game world
      // Offset by 150px to the right to visually center it in the remaining space (compensating for the 300px left panel)
      const scaleFactor = 1.25;
      gameWorld.scale.set(scaleFactor);
      gameWorld.x = Math.floor((app.screen.width - LAYOUT.OFFICE_WIDTH * scaleFactor) / 2) + 150;
      gameWorld.y = Math.floor((app.screen.height - LAYOUT.OFFICE_HEIGHT * scaleFactor) / 2);

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
      
      buyerContainer.x = Math.round(buyerPos.x);
      buyerContainer.y = Math.round(buyerPos.y + bIdleOffset);
      merchantContainer.x = Math.round(merchantPos.x);
      merchantContainer.y = Math.round(merchantPos.y + mIdleOffset);

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
          if (entity === 'buyer') return buyerPos;
          if (entity === 'merchant') return merchantPos;
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

        {summaryAgent && (
          <div className="absolute top-12 left-1/2 transform -translate-x-1/2 bg-[#111111] border-[3px] border-[#333333] shadow-[8px_8px_0_0_rgba(51,51,51,1)] p-6 z-50 text-white font-mono max-w-[400px]">
            <div className="flex justify-between items-center mb-4 border-b border-[#333333] pb-2">
              <span className={`font-bold text-sm tracking-widest uppercase ${summaryAgent === 'buyer' ? 'text-[#5BC0DE]' : 'text-[#D9534F]'}`}>
                {summaryAgent === 'buyer' ? 'JAKE (BUYER)' : 'HOLT (MERCHANT)'}
              </span>
              <button onClick={() => setSummaryAgent(null)} className="text-[#888888] hover:text-white hover:bg-[#333333] px-2 py-1 font-bold">[X]</button>
            </div>
            <div className="text-xs text-[#EAE8DD] leading-relaxed">
              {summaryAgent === 'buyer' 
                ? "Jake is a ruthless procurement optimizer designed to secure the lowest possible unit price while adhering to strict budget constraints. He uses data-driven arguments and aggressive negotiation tactics."
                : "Holt is a firm but fair sales veteran who defends the merchant's profit margins. He refuses to drop below the floor price and pushes for larger commitments to justify discounts."}
            </div>
            <div className="mt-4 text-[10px] text-[#888888] uppercase tracking-widest text-right">
              View full profile in Agent Roster
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
