import * as PIXI from 'pixi.js';

export function createDecorations(_width: number, _height: number): PIXI.Container {
  const container = new PIXI.Container();
  const g = new PIXI.Graphics();
  container.addChild(g);

  // ==========================================
  // HELPERS
  // ==========================================
  const drawPlant = (x: number, y: number, isFloorPlant: boolean = true) => {
    const potWidth = isFloorPlant ? 20 : 12;
    const potHeight = isFloorPlant ? 24 : 14;
    
    // Pot Shadow
    g.beginFill(0x000000, 0.2); g.drawEllipse(x, y + 2, potWidth/2 + 2, 4);
    
    // Pot
    g.beginFill(0x8B4513); g.lineStyle(1, 0x111111);
    g.drawRect(x - potWidth/2, y - potHeight, potWidth, potHeight);
    g.beginFill(0x5C3A21); g.lineStyle(0);
    g.drawRect(x - potWidth/2 + 2, y - potHeight, 4, potHeight); // shading
    g.endFill();
    
    // Leaves
    g.lineStyle(1, 0x002200);
    g.beginFill(0x228B22);
    if (isFloorPlant) {
      g.drawCircle(x, y - potHeight - 15, 16);
      g.drawCircle(x - 12, y - potHeight - 10, 12);
      g.drawCircle(x + 12, y - potHeight - 10, 12);
      g.drawCircle(x, y - potHeight - 25, 12);
      g.beginFill(0x32CD32); g.lineStyle(0); // leaf highlights
      g.drawCircle(x - 2, y - potHeight - 18, 6);
      g.drawCircle(x + 8, y - potHeight - 12, 4);
    } else {
      g.drawCircle(x, y - potHeight - 8, 8);
      g.drawCircle(x - 6, y - potHeight - 4, 6);
      g.drawCircle(x + 6, y - potHeight - 4, 6);
    }
    g.endFill();
  };

  // ==========================================
  // CHRISTMAS TREE
  // ==========================================
  const drawChristmasTree = (x: number, y: number) => {
    // Trunk
    g.beginFill(0x8B4513); g.lineStyle(1, 0x333333); g.drawRect(x - 8, y - 10, 16, 20); g.endFill();
    // Leaves (bottom to top)
    g.lineStyle(2, 0x006400);
    g.beginFill(0x228B22);
    g.moveTo(x - 30, y - 10); g.lineTo(x + 30, y - 10); g.lineTo(x, y - 40); g.lineTo(x - 30, y - 10);
    g.moveTo(x - 25, y - 30); g.lineTo(x + 25, y - 30); g.lineTo(x, y - 60); g.lineTo(x - 25, y - 30);
    g.moveTo(x - 20, y - 50); g.lineTo(x + 20, y - 50); g.lineTo(x, y - 80); g.lineTo(x - 20, y - 50);
    g.endFill();
    // Star
    g.beginFill(0xFFD700); g.lineStyle(1, 0xDAA520); 
    g.drawPolygon([
      x, y - 90, x + 3, y - 83, x + 10, y - 83, x + 4, y - 77, x + 6, y - 70,
      x, y - 74, x - 6, y - 70, x - 4, y - 77, x - 10, y - 83, x - 3, y - 83
    ]);
    g.endFill();
    // Baubles
    const colors = [0xFF0000, 0x00BFFF, 0xFF69B4, 0xFFFF00, 0xFF4500];
    const positions = [ [x-15, y-20], [x+10, y-25], [x, y-15], [x-10, y-40], [x+12, y-45], [x, y-35], [x-5, y-60], [x+8, y-55] ];
    positions.forEach(p => {
       g.beginFill(colors[Math.floor(Math.random() * colors.length)]); g.lineStyle(0);
       g.drawCircle(p[0], p[1], 3); g.endFill();
    });
  };

  // ==========================================
  // LOCKER WALL
  // ==========================================
  const drawLockers = (x: number, y: number) => {
    // Locker Block Shadow
    g.beginFill(0x000000, 0.3); g.drawRect(x - 5, y + 80, 160, 15);
    // Locker Body (Metal)
    g.beginFill(0x708090); g.lineStyle(2, 0x222222);
    g.drawRect(x, y, 150, 90);
    
    // 2 Rows x 6 Cols
    const lWidth = 25; const lHeight = 45;
    for (let row = 0; row < 2; row++) {
      for (let col = 0; col < 6; col++) {
        const lx = x + (col * lWidth);
        const ly = y + (row * lHeight);
        
        // Door
        g.beginFill(0x778899); g.lineStyle(1, 0x333333);
        g.drawRect(lx, ly, lWidth, lHeight);
        // Vents
        g.lineStyle(1, 0x222222); g.moveTo(lx + 5, ly + 5); g.lineTo(lx + 20, ly + 5);
        g.moveTo(lx + 5, ly + 8); g.lineTo(lx + 20, ly + 8);
        g.moveTo(lx + 5, ly + 11); g.lineTo(lx + 20, ly + 11);
        // Handle
        g.beginFill(0xAAAAAA); g.lineStyle(1, 0x111111);
        g.drawRect(lx + 18, ly + 20, 3, 10);
        // Number Plate
        g.beginFill(0xFFFFFF); g.lineStyle(0);
        g.drawRect(lx + 10, ly + 15, 6, 4);
        
        // Random Sticker
        if (Math.random() > 0.8) {
          g.beginFill(0xFF69B4); g.drawRect(lx + 6, ly + 25, 4, 4);
        }
      }
    }
    g.endFill();
    
    // Backpack on floor
    g.beginFill(0x4682B4); g.lineStyle(1, 0x111111);
    g.drawRect(x + 20, y + 75, 15, 15);
    g.drawCircle(x + 27, y + 75, 7);
    g.endFill();
    
    // Hanging Jacket
    g.beginFill(0x8B4513); g.lineStyle(1, 0x111111);
    g.drawRect(x - 5, y + 20, 10, 40);
    g.endFill();
  };

  // ==========================================
  // WHITEBOARD
  // ==========================================
  const drawWhiteboard = (x: number, y: number) => {
    // Board Body
    g.beginFill(0xF8F8F8); g.lineStyle(2, 0x555555); // Aluminum frame
    g.drawRect(x, y, 140, 90);
    g.beginFill(0xDDDDDD); g.lineStyle(0);
    g.drawRect(x, y + 86, 140, 4); // Marker tray
    
    // Board Scribbles (Replacing Text)
    g.beginFill(0x555555); g.lineStyle(0);
    g.drawRect(x + 25, y + 5, 40, 2); g.drawRect(x + 70, y + 5, 30, 2); // Title
    
    // Diagram Scribbles
    g.drawRect(x + 10, y + 20, 20, 2); g.drawRect(x + 40, y + 20, 30, 2);
    g.drawRect(x + 10, y + 27, 15, 2); g.drawRect(x + 60, y + 27, 15, 2);
    g.lineStyle(1, 0x555555);
    g.moveTo(x + 15, y + 32); g.lineTo(x + 35, y + 45);
    g.moveTo(x + 65, y + 32); g.lineTo(x + 45, y + 45);
    g.lineStyle(0);
    g.drawRect(x + 35, y + 50, 10, 2);
    
    g.drawRect(x + 10, y + 60, 20, 2); g.drawRect(x + 35, y + 60, 5, 2);
    g.drawRect(x + 10, y + 70, 15, 2);
    g.drawRect(x + 10, y + 75, 15, 2);
    g.endFill();
  };

  // ==========================================
  // PING PONG AREA
  // ==========================================
  const drawPingPong = (x: number, y: number) => {
    // Table Shadow
    g.beginFill(0x000000, 0.3); g.drawRect(x - 70, y + 25, 140, 20);
    // Legs
    g.beginFill(0x555555); g.lineStyle(2, 0x111111);
    g.drawRect(x - 60, y + 10, 5, 20); g.drawRect(x + 55, y + 10, 5, 20);
    g.drawRect(x - 5, y + 10, 10, 20); // center legs
    
    // Table Top (Green)
    g.beginFill(0x2E8B57); g.drawRect(x - 70, y - 10, 140, 25);
    // White Lines
    g.lineStyle(1, 0xFFFFFF); g.beginFill(0x2E8B57);
    g.drawRect(x - 68, y - 8, 136, 21); // outer border
    g.moveTo(x - 70, y + 2); g.lineTo(x + 70, y + 2); // center horizontal line
    
    // Net (White/Grey)
    g.lineStyle(1, 0x555555); g.beginFill(0xDDDDDD);
    g.drawRect(x - 2, y - 15, 4, 35);
    g.endFill();

    // Paddles & Ball
    g.beginFill(0xDC143C); g.lineStyle(1, 0x111111); // Red paddle
    g.drawCircle(x - 30, y - 2, 5); g.moveTo(x - 30, y + 3); g.lineTo(x - 35, y + 8);
    g.beginFill(0x4169E1); // Blue paddle
    g.drawCircle(x + 30, y + 5, 5); g.moveTo(x + 30, y + 0); g.lineTo(x + 35, y - 5);
    g.beginFill(0xFFFFFF); g.lineStyle(0); g.drawCircle(x - 15, y, 2); // ball
    g.endFill();

    // Scoreboard Scribbles
    g.beginFill(0x111111); g.lineStyle(2, 0x333333); g.drawRect(x - 30, y - 50, 60, 30); 
    g.beginFill(0xFFD700); g.lineStyle(0);
    g.drawRect(x - 15, y - 45, 30, 2); // title
    g.drawRect(x - 25, y - 35, 15, 2); g.drawRect(x + 10, y - 35, 10, 2); // left score
    g.drawRect(x - 25, y - 28, 20, 2); g.drawRect(x + 10, y - 28, 10, 2); // right score
    g.endFill();
  };

  // ==========================================
  // LOUNGE AREA
  // ==========================================
  const drawLounge = (x: number, y: number) => {
    // Couch Shadow
    g.beginFill(0x000000, 0.3); g.lineStyle(0); g.drawRect(x, y + 30, 100, 25);
    
    // Couch Body (Deep Teal)
    g.beginFill(0x008080); g.lineStyle(2, 0x111111);
    g.drawRect(x + 5, y - 10, 90, 40); // backrest
    g.drawRect(x, y + 10, 15, 30); // left arm
    g.drawRect(x + 85, y + 10, 15, 30); // right arm
    g.beginFill(0x006666); g.drawRect(x + 15, y + 20, 35, 20); // seat cushion 1
    g.drawRect(x + 50, y + 20, 35, 20); // seat cushion 2
    g.endFill();

    // Floor Lamp
    g.beginFill(0x333333); g.lineStyle(1, 0x111111); g.drawRect(x - 20, y + 45, 15, 5); // base
    g.drawRect(x - 13, y - 20, 2, 65); // pole
    g.beginFill(0xFFD700); g.drawPolygon([x - 23, y - 10, x - 3, y - 10, x - 8, y - 30, x - 18, y - 30]); // shade
    g.endFill();

    // Coffee Table
    g.beginFill(0x8B5A2B); g.lineStyle(2, 0x111111); g.drawRect(x + 15, y + 55, 70, 25);
    g.beginFill(0xFFFFFF); g.lineStyle(1, 0x111111); g.drawRect(x + 25, y + 60, 15, 10); // magazine
    g.beginFill(0x4682B4); g.lineStyle(0); g.drawRect(x + 27, y + 62, 11, 6); // magazine photo
    g.beginFill(0xFFFFFF); g.lineStyle(1, 0x111111); g.drawCircle(x + 70, y + 65, 4); // coffee cup
    g.endFill();

    // Bookshelf
    g.beginFill(0x5C3A21); g.lineStyle(2, 0x111111); g.drawRect(x + 110, y - 40, 50, 90);
    g.beginFill(0x3B2313); g.lineStyle(1, 0x111111);
    g.drawRect(x + 115, y - 15, 40, 5); // shelf 1
    g.drawRect(x + 115, y + 15, 40, 5); // shelf 2
    // Books
    g.beginFill(0xB22222); g.drawRect(x + 120, y - 30, 6, 15);
    g.beginFill(0x4682B4); g.drawRect(x + 128, y - 35, 8, 20);
    g.beginFill(0x2E8B57); g.drawRect(x + 138, y - 25, 5, 10);
    g.beginFill(0xDAA520); g.drawRect(x + 118, y, 7, 15);
    g.beginFill(0x8B008B); g.drawRect(x + 127, y + 5, 10, 10);
    g.endFill();
  };

  // ==========================================
  // PRINTER & STORAGE
  // ==========================================
  const drawPrinterArea = (x: number, y: number) => {
    // Printer Base
    g.beginFill(0xE0E0E0); g.lineStyle(2, 0x333333); g.drawRect(x, y, 50, 60);
    // Paper Trays
    g.beginFill(0xCCCCCC); g.lineStyle(1, 0x333333); 
    g.drawRect(x + 5, y + 20, 40, 10); g.drawRect(x + 5, y + 35, 40, 10);
    // Top Scanner / Output
    g.beginFill(0x555555); g.drawRect(x, y - 10, 50, 15);
    g.beginFill(0x333333); g.drawRect(x + 10, y - 5, 30, 5);
    // Printed Paper
    g.beginFill(0xFFFFFF); g.drawRect(x + 15, y - 5, 20, 15);
    // Tiny LED
    g.beginFill(0x5CB85C); g.lineStyle(0); g.drawCircle(x + 40, y - 5, 2);
    g.endFill();

    // Recycling Bin
    g.beginFill(0x4169E1); g.lineStyle(2, 0x111111); g.drawPolygon([x + 60, y + 10, x + 80, y + 10, x + 75, y + 40, x + 65, y + 40]);
    // Paper trash
    g.beginFill(0xFFFFFF); g.lineStyle(1, 0x999999);
    g.drawCircle(x + 65, y + 10, 4); g.drawCircle(x + 72, y + 8, 5);
    g.endFill();
  };

  // ==========================================
  // POSTERS
  // ==========================================
  const drawPoster = (x: number, y: number, color: string, w: number, h: number) => {
    g.beginFill(0x1A1A1A); g.lineStyle(2, 0x111111);
    g.drawRect(x, y, w, h);
    
    // Scribbles instead of text
    const numColor = parseInt(color.replace('#', '0x'), 16);
    g.beginFill(numColor); g.lineStyle(0);
    g.drawRect(x + 5, y + 5, w - 15, 4);
    g.drawRect(x + 5, y + 15, w - 25, 3);
    g.drawRect(x + 5, y + 22, w - 20, 3);
    g.drawRect(x + 5, y + 35, w - 30, 3);
    g.endFill();
  };

  // ==========================================
  // PLACEMENT / EXECUTION
  // ==========================================
  
  // Left Zone
  drawLockers(80, 140);
  drawWhiteboard(250, 60);
  drawPrinterArea(100, 480);
  
  // Center Zone
  drawPingPong(600, 520);
  
  // Right Zone
  drawLounge(950, 480);
  
  // Plants (Much denser foliage!)
  drawPlant(60, 460); // by printer
  drawPlant(350, 480); // mid-left floor
  drawPlant(920, 450); // by lounge
  drawPlant(1080, 280); // top right (moved left to not overlap HUD)
  drawPlant(450, 260); // by servers/buyer
  drawPlant(750, 260); // by servers/merchant
  drawPlant(450, 550); // ping pong left
  drawPlant(750, 550); // ping pong right
  drawPlant(1020, 360); // between lounge & desk
  drawPlant(250, 180); // near whiteboard (moved down)
  drawPlant(50, 250); // left wall center

  // Additional Trees
  drawChristmasTree(150, 260); // left side tree (moved left to not overlap whiteboard)
  drawChristmasTree(1020, 160); // top right corner tree (moved left to not overlap HUD)
  drawChristmasTree(80, 580); // bottom left corner tree
  
  // Posters
  drawPoster(420, 60, '#00CED1', 50, 50);
  drawPoster(840, 60, '#32CD32', 50, 60);

  return container;
}
