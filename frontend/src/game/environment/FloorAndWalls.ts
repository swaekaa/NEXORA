import * as PIXI from 'pixi.js';

export function createFloorAndWalls(width: number, height: number): PIXI.Container {
  const container = new PIXI.Container();
  const g = new PIXI.Graphics();
  container.addChild(g);

  // Base floor (warm wood/beige tiles)
  g.beginFill(0xD2B48C);
  g.drawRect(0, 0, width, height);
  g.endFill();

  // Floor tiles/planks pattern
  g.lineStyle(1, 0x8B4513, 0.15);
  for (let i = 0; i < width; i += 32) {
    g.moveTo(i, 0);
    g.lineTo(i, height);
  }
  for (let i = 0; i < height; i += 32) {
    g.moveTo(0, i);
    g.lineTo(width, i);
  }
  
  // Occasional darker/lighter tiles for variation
  g.lineStyle(0);
  for (let i = 0; i < 40; i++) {
    const tx = Math.floor(Math.random() * (width / 32)) * 32;
    const ty = Math.floor(Math.random() * (height / 32)) * 32;
    g.beginFill(Math.random() > 0.5 ? 0xDEB887 : 0xC19A6B, 0.4);
    g.drawRect(tx, ty, 32, 32);
    g.endFill();
  }

  // Rugs (Buyer)
  g.beginFill(0x5F9EA0, 0.4); // Teal rug
  g.drawRect(120, 200, 240, 180);
  g.endFill();

  // Rugs (Merchant)
  g.beginFill(0xCD5C5C, 0.4); // Red/Orange rug
  g.drawRect(width - 360, 200, 240, 180);
  g.endFill();

  // Center Rug (Negotiation table)
  g.beginFill(0x8FBC8F, 0.4); // Green rug
  g.drawRect(width / 2 - 180, 260, 360, 160);
  g.endFill();

  // Top Wall (3D perspective)
  g.beginFill(0xD3D3D3); // Wall base color
  g.drawRect(0, 0, width, 120);
  g.endFill();

  // Brick/Plaster texture lines on the wall
  g.lineStyle(1, 0xA9A9A9, 0.3);
  for (let i = 0; i < width; i += 64) {
    for (let j = 0; j < 120; j += 16) {
      if (Math.random() > 0.3) {
        g.moveTo(i + (j % 32 === 0 ? 0 : 32), j);
        g.lineTo(i + (j % 32 === 0 ? 0 : 32) + 32, j);
      }
    }
  }

  // Wall Baseboard
  g.lineStyle(0);
  g.beginFill(0x8B4513); // Dark wood trim
  g.drawRect(0, 110, width, 10);
  g.endFill();
  
  // Wall Top trim
  g.beginFill(0x696969);
  g.drawRect(0, 0, width, 8);
  g.endFill();

  // Windows
  const drawWindow = (x: number) => {
    // Frame
    g.beginFill(0x696969);
    g.drawRect(x, 20, 160, 80);
    // Glass
    g.beginFill(0x87CEEB);
    g.drawRect(x + 5, 25, 70, 70);
    g.drawRect(x + 85, 25, 70, 70);
    // City skyline silhouette
    g.beginFill(0x4682B4);
    g.drawRect(x + 5, 75, 20, 20);
    g.drawRect(x + 25, 60, 25, 35);
    g.drawRect(x + 50, 70, 25, 25);
    g.drawRect(x + 85, 65, 30, 30);
    g.drawRect(x + 115, 50, 25, 45);
    g.drawRect(x + 140, 80, 15, 15);
    g.endFill();
    // Window glare
    g.beginFill(0xFFFFFF, 0.2);
    g.moveTo(x + 15, 25); g.lineTo(x + 35, 25); g.lineTo(x + 5, 65); g.lineTo(x + 5, 45);
    g.moveTo(x + 95, 25); g.lineTo(x + 115, 25); g.lineTo(x + 85, 65); g.lineTo(x + 85, 45);
    g.endFill();
    // Window Sill
    g.beginFill(0xA9A9A9);
    g.drawRect(x - 5, 100, 170, 8);
    g.endFill();
  };

  drawWindow(60);
  drawWindow(width - 220);

  // Wall shadow (where wall meets floor)
  g.beginFill(0x000000, 0.15);
  g.drawRect(0, 120, width, 16);
  g.endFill();

  return container;
}
