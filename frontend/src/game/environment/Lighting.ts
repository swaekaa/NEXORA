import * as PIXI from 'pixi.js';

export function createLighting(width: number, height: number, buyerPos: {x: number, y: number}, merchantPos: {x: number, y: number}, policyPos: {x: number, y: number}): PIXI.Graphics {
  const g = new PIXI.Graphics();
  
  // Fill entire screen with a very subtle dark overlay
  g.beginFill(0x111111, 0.05);
  g.drawRect(0, 0, width, height);
  g.endFill();
  
  // Cut out light shapes using blending
  g.blendMode = PIXI.BLEND_MODES.ADD;
  
  // Screen Glows (subtle cyan / red)
  g.beginFill(0x00CED1, 0.1);
  g.drawCircle(buyerPos.x, buyerPos.y - 45, 60);
  g.endFill();

  g.beginFill(0xFF6347, 0.1);
  g.drawCircle(merchantPos.x, merchantPos.y - 45, 60);
  g.endFill();
  
  // Policy Core Glow (subtle yellow)
  g.beginFill(0xF0AD4E, 0.1);
  g.drawCircle(policyPos.x, policyPos.y + 10, 80);
  g.endFill();

  // Window Lights
  g.beginFill(0xFFFFFF, 0.05);
  g.moveTo(60, 100); g.lineTo(220, 100); g.lineTo(280, 250); g.lineTo(120, 250);
  g.moveTo(width - 220, 100); g.lineTo(width - 60, 100); g.lineTo(width, 250); g.lineTo(width - 160, 250);
  g.endFill();

  return g;
}
