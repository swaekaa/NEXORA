import * as PIXI from 'pixi.js';

export function createPolicyCore(container: PIXI.Container, x: number, y: number) {
  const g = new PIXI.Graphics();
  container.addChild(g);

  // Helper for drawing a server rack
  const drawRack = (rx: number, ry: number, isMain: boolean) => {
    const width = isMain ? 60 : 40;
    const height = isMain ? 120 : 100;
    const yOffset = isMain ? -60 : -50;
    
    // Shadow
    g.beginFill(0x000000, 0.3); g.drawRect(rx - (width/2) - 5, ry + yOffset + 20, width + 10, height);
    
    // Rack Body
    g.beginFill(0x222222); g.lineStyle(2, 0x111111);
    g.drawRect(rx - (width/2), ry + yOffset, width, height);
    
    // Inner Rails
    g.beginFill(0x333333); g.lineStyle(0);
    g.drawRect(rx - (width/2) + 4, ry + yOffset + 4, 4, height - 8);
    g.drawRect(rx + (width/2) - 8, ry + yOffset + 4, 4, height - 8);

    // Blades/Servers
    g.lineStyle(1, 0x111111);
    const bladeCount = isMain ? 6 : 8;
    for(let i=0; i<bladeCount; i++) {
      g.beginFill(0x444444);
      g.drawRect(rx - (width/2) + 8, ry + yOffset + 10 + (i * 12), width - 16, 8);
      // Lights
      g.lineStyle(0);
      g.beginFill(0x5CB85C); // Green
      g.drawRect(rx + (width/2) - 16, ry + yOffset + 12 + (i * 12), 2, 4);
      g.beginFill(Math.random() > 0.5 ? 0x5BC0DE : 0xF0AD4E); // Blue or Orange
      g.drawRect(rx + (width/2) - 20, ry + yOffset + 12 + (i * 12), 2, 4);
      g.lineStyle(1, 0x111111);
    }
  };

  // Draw 3 Racks
  drawRack(x - 55, y, false); // Left Rack
  drawRack(x + 55, y, false); // Right Rack
  drawRack(x, y, true);       // Center Rack

  // Center Terminal (Iris Display)
  g.beginFill(0x1F2937); g.lineStyle(2, 0x111111);
  g.drawRect(x - 30, y + 10, 60, 35);
  g.beginFill(0x064E3B); g.lineStyle(0);
  g.drawRect(x - 26, y + 14, 52, 27);
  g.endFill();

  // Screen Scribbles
  g.beginFill(0x34D399); g.lineStyle(0);
  g.drawRect(x - 22, y + 18, 35, 3);
  g.drawRect(x - 22, y + 28, 20, 2);
  g.drawRect(x + 2, y + 28, 15, 2);
  g.endFill();

  // Cables running between racks
  g.lineStyle(2, 0x111111);
  g.moveTo(x - 35, y - 40); g.lineTo(x - 20, y - 40); // Left to center
  g.moveTo(x + 35, y - 30); g.lineTo(x + 20, y - 30); // Right to center
  
  // Large Wall Sign (POLICY CHECKLIST)
  const signX = x + 90;
  const signY = y - 80;
  g.beginFill(0x222222); g.lineStyle(2, 0x111111);
  g.drawRect(signX, signY, 110, 70);
  
  // Sign Scribbles
  g.beginFill(0xFFFFFF); g.lineStyle(0);
  g.drawRect(signX + 5, signY + 5, 40, 3);
  g.drawRect(signX + 5, signY + 15, 60, 2);
  g.beginFill(0x5CB85C);
  // list items
  for(let i = 0; i < 4; i++) {
    const ly = signY + 30 + (i * 8);
    g.drawRect(signX + 5, ly, 4, 3); // checkmark scribble
    g.drawRect(signX + 15, ly + 1, 25 + Math.random() * 20, 2); // text line
  }
  g.endFill();
}
