import * as PIXI from 'pixi.js';

export function createFloorAndWalls(width: number, height: number): PIXI.Container {
  const container = new PIXI.Container();
  const g = new PIXI.Graphics();
  container.addChild(g);

  // Extend coordinates safely off-screen to avoid gaps
  const startX = -200;
  const startY = -100;
  const endX = width + 200;
  const endY = height + 200;
  const wallY = 140; // The bottom edge of the wall (top of the floor)

  // ==========================================
  // FLOOR GRID (Detailed Wood/Tile Pattern)
  // ==========================================
  g.beginFill(0xC59A6F); // Base wood floor
  g.drawRect(startX, wallY, endX - startX, endY - wallY);
  g.endFill();

  // Create pixel-art floor tiles (32x32)
  g.lineStyle(1, 0x000000, 0.1); // subtle grid line
  for (let i = startX; i < endX; i += 32) {
    g.moveTo(i, wallY); g.lineTo(i, endY);
  }
  for (let j = wallY; j < endY; j += 32) {
    g.moveTo(startX, j); g.lineTo(endX, j);
  }

  // Randomize some tiles to break the repetition
  g.lineStyle(0);
  for (let i = 0; i < 400; i++) {
    const tx = Math.floor((startX + Math.random() * (endX - startX)) / 32) * 32;
    const ty = Math.floor((wallY + Math.random() * (endY - wallY)) / 32) * 32;
    g.beginFill(Math.random() > 0.5 ? 0xCE9F72 : 0xBB8F64, 0.6); // slight color variations
    g.drawRect(tx, ty, 32, 32);
    
    // Tiny pixel wood grain detail inside random tiles
    if (Math.random() > 0.7) {
      g.beginFill(0x9E754C, 0.3);
      g.drawRect(tx + 4, ty + 8, 24, 2);
      g.drawRect(tx + 8, ty + 16, 20, 2);
      g.drawRect(tx + 2, ty + 24, 18, 2);
    }
    g.endFill();
  }

  // ==========================================
  // RUGS & CARPET ZONES
  // ==========================================
  const drawRug = (rx: number, ry: number, rw: number, rh: number, color: number) => {
    // Shadow
    g.beginFill(0x000000, 0.15);
    g.drawRect(rx - 2, ry + 2, rw + 4, rh + 4);
    
    // Base Rug
    g.beginFill(color);
    g.drawRect(rx, ry, rw, rh);
    
    // Rug Inner Border
    g.beginFill(0x000000, 0.1);
    g.drawRect(rx + 4, ry + 4, rw - 8, rh - 8);
    g.beginFill(0xFFFFFF, 0.1);
    g.drawRect(rx + 6, ry + 6, rw - 12, rh - 12);
    
    // Fringes (Left and Right)
    g.beginFill(0xE8DCCC);
    for (let i = ry + 2; i < ry + rh - 2; i += 4) {
      g.drawRect(rx - 4, i, 4, 2);
      g.drawRect(rx + rw, i, 4, 2);
    }
    g.endFill();
  };

  // Ping Pong Area Rug (Bottom center)
  drawRug(450, 430, 300, 160, 0x4682B4); // Steel Blue

  // Lounge Area Rug (Bottom right)
  drawRug(850, 420, 300, 160, 0xA0522D); // Sienna / Dark Red

  // Workstation Mats (Buyer / Merchant)
  drawRug(240, 240, 220, 140, 0x2E8B57); // Sea Green
  drawRug(740, 240, 220, 140, 0x2E8B57); // Sea Green

  // ==========================================
  // WALLS & ARCHITECTURE
  // ==========================================
  // Main Wall Base (Light gray/beige)
  g.beginFill(0xDCDCDC);
  g.drawRect(startX, startY, endX - startX, wallY - startY);
  g.endFill();

  // Subtle vertical paneling or brick lines on the wall
  g.lineStyle(1, 0x000000, 0.05);
  for (let i = startX; i < endX; i += 48) {
    g.moveTo(i, startY); g.lineTo(i, wallY);
  }

  // Crown Molding (Top)
  g.lineStyle(0);
  g.beginFill(0xFFFFFF); g.drawRect(startX, startY, endX - startX, 12);
  g.beginFill(0xCCCCCC); g.drawRect(startX, startY + 12, endX - startX, 4);
  g.endFill();

  // Baseboards (Bottom where wall meets floor)
  g.beginFill(0x8B4513); // Dark wood baseboard
  g.drawRect(startX, wallY - 14, endX - startX, 14);
  g.beginFill(0x5C3A21); // Top edge of baseboard
  g.drawRect(startX, wallY - 14, endX - startX, 2);
  g.endFill();

  // Wall Shadow on the floor (Gradient-like via overlapping rects)
  g.beginFill(0x000000, 0.1); g.drawRect(startX, wallY, endX - startX, 4);
  g.beginFill(0x000000, 0.05); g.drawRect(startX, wallY + 4, endX - startX, 4);
  g.beginFill(0x000000, 0.02); g.drawRect(startX, wallY + 8, endX - startX, 8);
  g.endFill();

  // ==========================================
  // WINDOWS (Alive and Detailed)
  // ==========================================
  const drawWindow = (x: number, width: number) => {
    // Window Frame Shadow
    g.beginFill(0x000000, 0.2); g.drawRect(x + 2, 22, width, 90);
    // Outer Frame (Dark Metal)
    g.beginFill(0x2F4F4F); g.drawRect(x, 20, width, 90);
    // Inner Frame (Lighter Metal)
    g.beginFill(0x708090); g.drawRect(x + 4, 24, width - 8, 82);
    
    // Glass Background (Sky)
    g.beginFill(0x87CEFA); g.drawRect(x + 8, 28, width - 16, 74);
    
    // Clouds
    g.beginFill(0xFFFFFF, 0.8);
    g.drawRect(x + 15, 35, 30, 10); g.drawRect(x + 20, 30, 20, 5);
    g.drawRect(x + width - 40, 45, 25, 8); g.drawRect(x + width - 35, 42, 15, 3);
    
    // Distant Skyline (Light Blue)
    g.beginFill(0x4682B4);
    g.drawRect(x + 10, 60, 20, 42); g.drawRect(x + 30, 75, 15, 27);
    g.drawRect(x + 50, 50, 25, 52); g.drawRect(x + 80, 65, 30, 37);
    if (width > 120) g.drawRect(x + 115, 55, 35, 47);
    
    // Foreground Skyline (Dark Blue)
    g.beginFill(0x191970);
    g.drawRect(x + 8, 80, 15, 22); g.drawRect(x + 23, 70, 22, 32);
    g.drawRect(x + 55, 85, 20, 17); g.drawRect(x + 75, 60, 18, 42);
    if (width > 120) g.drawRect(x + 130, 80, 20, 22);

    // Glass Glare (Diagonal bands)
    g.beginFill(0xFFFFFF, 0.15);
    g.drawPolygon([x + 20, 28, x + 40, 28, x + 8, 70, x + 8, 50]);
    g.drawPolygon([x + width - 30, 28, x + width - 10, 28, x + 8, 90, x + 8 + 20, 90]);
    g.endFill();

    // Horizontal Blinds (Half drawn)
    g.beginFill(0xDDDDDD);
    for (let by = 30; by < 55; by += 4) {
      g.drawRect(x + 8, by, width - 16, 2);
    }
    // Blind pull cord
    g.beginFill(0xFFFFFF); g.drawRect(x + width - 14, 30, 1, 40);
    g.beginFill(0x888888); g.drawRect(x + width - 15, 70, 3, 6);
    g.endFill();

    // Window Divider (Mullion)
    g.beginFill(0x2F4F4F); g.drawRect(x + (width/2) - 2, 28, 4, 74);
    g.endFill();
  };

  // Draw 4 Large Office Windows
  drawWindow(100, 160);
  drawWindow(320, 160);
  drawWindow(720, 160);
  drawWindow(940, 160);

  // ==========================================
  // CABLE PIPES (Connecting Iris to Workstations)
  // ==========================================
  const drawPipe = (px: number, py: number, pwidth: number, pheight: number) => {
    g.beginFill(0x222222); g.drawRect(px, py, pwidth, pheight);
    g.beginFill(0x555555); g.drawRect(px + 1, py + 1, pwidth - 2, pheight - 2);
    g.beginFill(0x777777); 
    if (pwidth > pheight) g.drawRect(px + 1, py + 1, pwidth - 2, 1); // horizontal highlight
    else g.drawRect(px + 1, py + 1, 1, pheight - 2); // vertical highlight
    g.endFill();
  };

  // Main trunk from Iris down the wall
  drawPipe(595, wallY - 14, 10, 34); // down to floor
  // Split left and right on floor
  drawPipe(350, wallY + 10, 500, 10);
  // Down to buyer desk
  drawPipe(350, wallY + 10, 10, 120);
  // Down to merchant desk
  drawPipe(840, wallY + 10, 10, 120);

  return container;
}
