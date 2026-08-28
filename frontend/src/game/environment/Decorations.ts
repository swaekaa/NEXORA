import * as PIXI from 'pixi.js';

export function createDecorations(width: number, height: number): PIXI.Container {
  const container = new PIXI.Container();
  const g = new PIXI.Graphics();
  container.addChild(g);

  const drawPlant = (x: number, y: number) => {
    // Pot
    g.beginFill(0x8B4513);
    g.lineStyle(1, 0x333333);
    g.drawRect(x - 10, y - 10, 20, 15);
    g.endFill();
    // Leaves
    g.beginFill(0x228B22);
    g.lineStyle(1, 0x006400);
    g.drawCircle(x, y - 20, 12);
    g.drawCircle(x - 8, y - 15, 10);
    g.drawCircle(x + 8, y - 15, 10);
    g.drawCircle(x, y - 28, 8);
    g.endFill();
  };

  const drawFilingCabinet = (x: number, y: number) => {
    // Shadow
    g.beginFill(0x000000, 0.2);
    g.lineStyle(0);
    g.drawRect(x - 15, y - 5, 35, 55);
    g.endFill();
    // Body
    g.beginFill(0x778899); // Slate gray
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 15, y - 40, 30, 90);
    g.endFill();
    // Drawers
    g.lineStyle(1, 0x333333);
    g.beginFill(0x708090);
    for(let i=0; i<3; i++) {
      g.drawRect(x - 10, y - 35 + (i * 30), 20, 25);
      // Handles
      g.beginFill(0xC0C0C0);
      g.drawRect(x - 5, y - 25 + (i * 30), 10, 4);
      g.beginFill(0x708090);
    }
    g.endFill();
  };

  const drawBookshelf = (x: number, y: number) => {
    // Body
    g.beginFill(0x654321); // Dark brown wood
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 40, y - 50, 80, 100);
    g.endFill();
    // Shelves
    g.beginFill(0x4B3621);
    g.lineStyle(1, 0x333333);
    for(let i=1; i<4; i++) {
      g.drawRect(x - 35, y - 50 + (i * 25), 70, 5);
      
      // Books
      g.lineStyle(1, 0x111111);
      let bx = x - 30;
      while(bx < x + 30) {
        const bWidth = 4 + Math.random() * 6;
        if (bx + bWidth > x + 30) break;
        const bHeight = 10 + Math.random() * 10;
        const colors = [0xB22222, 0x4682B4, 0x2E8B57, 0xDAA520, 0x8B008B];
        g.beginFill(colors[Math.floor(Math.random() * colors.length)]);
        g.drawRect(bx, y - 50 + (i * 25) - bHeight, bWidth, bHeight);
        bx += bWidth + 1;
      }
      g.beginFill(0x4B3621);
    }
    g.endFill();
  };

  const drawWaterCooler = (x: number, y: number) => {
    // Body
    g.beginFill(0xE0E0E0);
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 12, y, 24, 40);
    // Bottle
    g.beginFill(0x87CEFA, 0.7);
    g.drawRect(x - 10, y - 30, 20, 30);
    g.endFill();
    // Faucets
    g.beginFill(0xFF0000); g.drawCircle(x - 4, y + 10, 2);
    g.beginFill(0x0000FF); g.drawCircle(x + 4, y + 10, 2);
    g.endFill();
  };

  const drawWhiteboard = (x: number, y: number) => {
    g.beginFill(0xFFFFFF);
    g.lineStyle(2, 0x696969); // Aluminum frame
    g.drawRect(x - 60, y - 35, 120, 70);
    g.endFill();
    
    // Some mock charts/graphs on whiteboard
    g.lineStyle(2, 0xFF0000);
    g.moveTo(x - 50, y); g.lineTo(x - 30, y - 20); g.lineTo(x - 10, y - 10); g.lineTo(x + 10, y - 25);
    g.lineStyle(2, 0x0000FF);
    g.moveTo(x + 20, y); g.lineTo(x + 40, y + 20);
    g.lineStyle(0);
    g.beginFill(0x228B22);
    g.drawRect(x - 45, y + 10, 10, 20);
    g.drawRect(x - 30, y + 5, 10, 25);
    g.drawRect(x - 15, y + 15, 10, 15);
    g.endFill();

    const title = new PIXI.Text('DATA BOARD', new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 8, fill: '#333333', fontWeight: 'bold' }));
    title.x = x - 55; title.y = y - 30;
    container.addChild(title);
  };
  
  const drawWallPoster = (x: number, y: number, text: string, color: number) => {
    g.beginFill(0x222222);
    g.lineStyle(3, 0x111111);
    g.drawRect(x - 35, y - 40, 70, 80);
    g.endFill();
    
    const posterTxt = new PIXI.Text(text, new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 10, fill: PIXI.utils.hex2string(color), wordWrap: true, wordWrapWidth: 60, align: 'left', lineHeight: 14 }));
    posterTxt.x = x - 25; posterTxt.y = y - 30;
    container.addChild(posterTxt);
  };
  
  const drawClock = (x: number, y: number) => {
    g.beginFill(0xFFFFFF);
    g.lineStyle(3, 0x333333);
    g.drawCircle(x, y, 15);
    g.lineStyle(2, 0x333333);
    g.moveTo(x, y); g.lineTo(x, y - 10);
    g.moveTo(x, y); g.lineTo(x + 8, y);
    g.endFill();
  };

  const drawCouch = (x: number, y: number) => {
    // Shadow
    g.beginFill(0x000000, 0.2);
    g.lineStyle(0);
    g.drawRect(x - 30, y - 10, 60, 40);
    g.endFill();
    // Body (Teal Leather)
    g.beginFill(0x008080);
    g.lineStyle(2, 0x111111);
    g.drawRect(x - 35, y - 25, 70, 50); // back
    g.drawRect(x - 35, y - 5, 15, 30); // left arm
    g.drawRect(x + 20, y - 5, 15, 30); // right arm
    g.drawRect(x - 20, y + 5, 40, 20); // seat
    g.endFill();
  };
  
  const drawCoffeeTable = (x: number, y: number) => {
    g.beginFill(0x8B5A2B);
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 25, y - 15, 50, 30);
    g.endFill();
    // A magazine
    g.beginFill(0xFFFFFF);
    g.lineStyle(1, 0x333333);
    g.drawRect(x - 10, y - 5, 12, 16);
    g.beginFill(0x4682B4); g.drawRect(x - 8, y - 3, 8, 8); // photo
    g.endFill();
  };

  // --- Placing Decorations in the Room ---

  // Top Left Area
  drawFilingCabinet(40, 250);
  drawPlant(110, 220);
  drawWhiteboard(100, 90);
  
  // Top Wall elements
  drawClock(280, 50);
  drawWallPoster(350, 60, "NEGOTIATE SMARTER.\nCLOSE BETTER.", 0x00CED1);
  drawWallPoster(width - 320, 60, "TRUST LAYER\n✓ COMPLIANCE\n✓ VERIFICATION\n✓ AUDIT TRAIL\n✓ SECURE", 0x32CD32);

  // Top Right Area
  drawBookshelf(width - 80, 220);
  drawPlant(width - 40, 280);
  
  // Left Area
  drawPlant(40, height - 120);
  drawWaterCooler(40, height - 160);
  
  // Right Area
  drawCouch(width - 60, height - 150);
  drawCoffeeTable(width - 60, height - 80);

  return container;
}
