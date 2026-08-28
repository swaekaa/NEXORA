import * as PIXI from 'pixi.js';

export function createWorkstations(): PIXI.Container {
  const container = new PIXI.Container();
  const g = new PIXI.Graphics();
  container.addChild(g);

  // Helper to draw a desk setup
  const drawDesk = (x: number, y: number, isBuyer: boolean) => {
    // Desk Shadow
    g.beginFill(0x000000, 0.2);
    g.drawRect(x - 65, y - 10, 130, 60);
    g.endFill();

    // Main Desk Body (Wood)
    g.beginFill(0x8B5A2B); // Darker wood for retro feel
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 60, y - 35, 120, 60);
    g.endFill();

    // Desk Drawers (Left and Right)
    g.beginFill(0xA0522D);
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 55, y - 5, 30, 25);
    g.drawRect(x + 25, y - 5, 30, 25);
    // Handles
    g.lineStyle(0);
    g.beginFill(0x333333);
    g.drawRect(x - 45, y + 5, 10, 2);
    g.drawRect(x + 35, y + 5, 10, 2);
    g.endFill();

    // Monitor Stand
    g.beginFill(0x404040);
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 10, y - 40, 20, 10);
    g.endFill();

    // Monitor
    g.beginFill(0x2F4F4F);
    g.lineStyle(2, 0x333333);
    g.drawRect(x - 25, y - 60, 50, 30);
    // Screen
    g.beginFill(isBuyer ? 0x00CED1 : 0xFF6347); // Blue for buyer, Red for merchant
    g.lineStyle(0);
    g.drawRect(x - 21, y - 56, 42, 22);
    // Code/Graph lines on screen
    g.beginFill(0xFFFFFF, 0.5);
    g.drawRect(x - 18, y - 52, 20, 2);
    g.drawRect(x - 18, y - 48, 15, 2);
    g.drawRect(x - 18, y - 44, 25, 2);
    if (!isBuyer) {
      // Small chart for merchant
      g.beginFill(0x32CD32);
      g.drawRect(x + 5, y - 44, 4, 10);
      g.drawRect(x + 11, y - 48, 4, 14);
      g.drawRect(x + 17, y - 52, 4, 18);
    }
    g.endFill();

    // Keyboard
    g.beginFill(0xE0E0E0);
    g.lineStyle(1, 0x333333);
    g.drawRect(x - 15, y - 25, 30, 8);
    g.endFill();

    // Mouse
    g.beginFill(0x808080);
    g.lineStyle(1, 0x333333);
    g.drawRect(x + 20, y - 25, 6, 8);
    g.endFill();

    // Coffee Mug
    g.beginFill(0xFFFFFF);
    g.lineStyle(1, 0x333333);
    g.drawCircle(x - 40, y - 25, 4);
    // Coffee liquid
    g.beginFill(0x4B3621);
    g.lineStyle(0);
    g.drawCircle(x - 40, y - 25, 2);
    g.endFill();

    // Papers / Documents
    g.beginFill(0xFFFFFF);
    g.lineStyle(1, 0x333333);
    g.drawRect(x + 35, y - 30, 15, 20);
    if (isBuyer) g.drawRect(x + 30, y - 28, 15, 20); // slightly offset stack
    // Text lines
    g.lineStyle(0);
    g.beginFill(0x999999);
    g.drawRect(x + 37, y - 26, 10, 1);
    g.drawRect(x + 37, y - 22, 8, 1);
    g.drawRect(x + 37, y - 18, 11, 1);
    g.endFill();
    
    // Sign / Nameplate on front of desk
    g.beginFill(0x333333);
    g.lineStyle(1, 0x000000);
    g.drawRect(x - 25, y - 8, 50, 14);
    g.endFill();

    // Create a text label for the desk
    const label = new PIXI.Text(isBuyer ? 'BUYER OPS' : 'MERCHANT OPS', 
      new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 6, fill: '#FFFFFF', fontWeight: 'bold' })
    );
    label.anchor.set(0.5);
    label.x = x;
    label.y = y - 1;
    container.addChild(label);
  };

  // Assuming standard LAYOUT positions from OfficeScene, but we'll export layout constants differently or pass them in.
  // We'll just hardcode typical coordinates based on typical 1024x768 or pass them in.
  // For now, let's export a generic function that takes the coordinates.
  return container;
}

export function drawWorkstation(g: PIXI.Graphics, container: PIXI.Container, x: number, y: number, isBuyer: boolean) {
  // Desk Shadow
  g.beginFill(0x000000, 0.2);
  g.drawRect(x - 65, y - 10, 130, 60);
  g.endFill();

  // Main Desk Body (Wood)
  g.beginFill(0x8B5A2B); // Darker wood for retro feel
  g.lineStyle(2, 0x333333);
  g.drawRect(x - 60, y - 35, 120, 60);
  g.endFill();

  // Desk Drawers (Left and Right)
  g.beginFill(0xA0522D);
  g.lineStyle(2, 0x333333);
  g.drawRect(x - 55, y - 5, 30, 25);
  g.drawRect(x + 25, y - 5, 30, 25);
  // Handles
  g.lineStyle(0);
  g.beginFill(0x333333);
  g.drawRect(x - 45, y + 5, 10, 2);
  g.drawRect(x + 35, y + 5, 10, 2);
  g.endFill();

  // Monitor Stand
  g.beginFill(0x404040);
  g.lineStyle(2, 0x333333);
  g.drawRect(x - 10, y - 40, 20, 10);
  g.endFill();

  // Monitor
  g.beginFill(0x2F4F4F);
  g.lineStyle(2, 0x333333);
  g.drawRect(x - 25, y - 60, 50, 30);
  // Screen
  g.beginFill(isBuyer ? 0x00CED1 : 0xFF6347); // Blue for buyer, Red for merchant
  g.lineStyle(0);
  g.drawRect(x - 21, y - 56, 42, 22);
  // Code/Graph lines on screen
  g.beginFill(0xFFFFFF, 0.5);
  g.drawRect(x - 18, y - 52, 20, 2);
  g.drawRect(x - 18, y - 48, 15, 2);
  g.drawRect(x - 18, y - 44, 25, 2);
  if (!isBuyer) {
    // Small chart for merchant
    g.beginFill(0x32CD32);
    g.drawRect(x + 5, y - 44, 4, 10);
    g.drawRect(x + 11, y - 48, 4, 14);
    g.drawRect(x + 17, y - 52, 4, 18);
  }
  g.endFill();

  // Keyboard
  g.beginFill(0xE0E0E0);
  g.lineStyle(1, 0x333333);
  g.drawRect(x - 15, y - 25, 30, 8);
  g.endFill();

  // Mouse
  g.beginFill(0x808080);
  g.lineStyle(1, 0x333333);
  g.drawRect(x + 20, y - 25, 6, 8);
  g.endFill();

  // Coffee Mug
  g.beginFill(0xFFFFFF);
  g.lineStyle(1, 0x333333);
  g.drawCircle(x - 40, y - 25, 4);
  // Coffee liquid
  g.beginFill(0x4B3621);
  g.lineStyle(0);
  g.drawCircle(x - 40, y - 25, 2);
  g.endFill();

  // Papers / Documents
  g.beginFill(0xFFFFFF);
  g.lineStyle(1, 0x333333);
  g.drawRect(x + 35, y - 30, 15, 20);
  if (isBuyer) g.drawRect(x + 30, y - 28, 15, 20); // slightly offset stack
  // Text lines
  g.lineStyle(0);
  g.beginFill(0x999999);
  g.drawRect(x + 37, y - 26, 10, 1);
  g.drawRect(x + 37, y - 22, 8, 1);
  g.drawRect(x + 37, y - 18, 11, 1);
  g.endFill();
  
  // Sign / Nameplate on front of desk
  g.beginFill(0x333333);
  g.lineStyle(1, 0x000000);
  g.drawRect(x - 25, y - 8, 50, 14);
  g.endFill();

  // Create a text label for the desk
  const label = new PIXI.Text(isBuyer ? 'BUYER OPS' : 'MERCHANT OPS', 
    new PIXI.TextStyle({ fontFamily: 'sans-serif', fontSize: 6, fill: '#FFFFFF', fontWeight: 'bold' })
  );
  label.anchor.set(0.5);
  label.x = x;
  label.y = y - 1;
  container.addChild(label);
}
