import * as PIXI from 'pixi.js';

export function createWorkstations(): PIXI.Container {
  return new PIXI.Container();
}

export function drawWorkstation(g: PIXI.Graphics, container: PIXI.Container, x: number, y: number, isBuyer: boolean) {
  // Desk Shadow
  g.beginFill(0x000000, 0.25);
  g.drawRect(x - 65, y - 10, 130, 60);
  g.endFill();
  
  // ==========================================
  // CHAIR (Drawn behind the desk)
  // ==========================================
  g.beginFill(0x2F4F4F); // Dark slate chair
  g.lineStyle(2, 0x111111);
  g.drawRect(x - 20, y + 25, 40, 35); // seat
  g.drawRect(x - 18, y + 15, 36, 15); // backrest
  // armrests
  g.drawRect(x - 24, y + 20, 6, 20);
  g.drawRect(x + 18, y + 20, 6, 20);
  // chair base/wheels
  g.beginFill(0x111111);
  g.drawRect(x - 2, y + 60, 4, 15);
  g.drawRect(x - 15, y + 70, 30, 4);
  g.drawRect(x - 15, y + 73, 6, 4);
  g.drawRect(x + 9, y + 73, 6, 4);
  g.endFill();

  // ==========================================
  // DESK BODY
  // ==========================================
  g.beginFill(0x8B5A2B); // Rich wood
  g.lineStyle(2, 0x222222);
  g.drawRect(x - 65, y - 35, 130, 65); // main top
  g.endFill();

  // Drawers / Cabinets
  g.beginFill(0x654321);
  g.lineStyle(2, 0x222222);
  g.drawRect(x - 60, y - 5, 35, 30); // left cabinet
  g.drawRect(x + 25, y - 5, 35, 30); // right cabinet
  // Drawer Handles
  g.beginFill(0xAAAAAA);
  g.lineStyle(1, 0x111111);
  g.drawRect(x - 50, y + 2, 15, 4);
  g.drawRect(x + 35, y + 2, 15, 4);
  g.drawRect(x - 50, y + 15, 15, 4);
  g.drawRect(x + 35, y + 15, 15, 4);
  g.endFill();

  // Edge highlight on desk top
  g.lineStyle(0);
  g.beginFill(0xA0522D);
  g.drawRect(x - 63, y - 33, 126, 2);
  g.endFill();

  // ==========================================
  // MONITORS
  // ==========================================
  // Monitor Stands
  g.beginFill(0x333333); g.lineStyle(1, 0x111111);
  g.drawRect(x - 20, y - 45, 12, 15); // main monitor stand
  g.drawRect(x + 10, y - 40, 10, 10); // side monitor stand
  g.endFill();

  // Main Monitor (CRT/Thick LCD style)
  g.beginFill(0x222222); g.lineStyle(2, 0x111111);
  g.drawRect(x - 40, y - 75, 50, 35);
  // Main Screen
  g.beginFill(0x001122); g.lineStyle(0);
  g.drawRect(x - 36, y - 71, 42, 27);
  
  // Side Monitor (Vertical for code/data)
  g.beginFill(0x333333); g.lineStyle(2, 0x111111);
  g.drawRect(x + 15, y - 70, 30, 40);
  // Side Screen
  g.beginFill(0x001111); g.lineStyle(0);
  g.drawRect(x + 18, y - 67, 24, 34);
  g.endFill();

  // Screen Text Scribbles (Side Monitor)
  g.beginFill(isBuyer ? 0x00FFFF : 0xFF4500); g.lineStyle(0);
  g.drawRect(x + 20, y - 65, 15, 2);
  g.drawRect(x + 20, y - 60, 20, 2);
  g.drawRect(x + 20, y - 55, 10, 2);
  g.drawRect(x + 20, y - 50, 18, 2);
  g.endFill();

  // Screen Code Lines (Main Monitor)
  g.beginFill(isBuyer ? 0x00CED1 : 0xFF6347, 0.7);
  g.drawRect(x - 32, y - 65, 20, 2);
  g.drawRect(x - 32, y - 60, 15, 2);
  g.drawRect(x - 32, y - 55, 30, 2);
  g.drawRect(x - 32, y - 50, 10, 2);
  if (!isBuyer) {
    g.beginFill(0x32CD32); g.drawRect(x - 5, y - 55, 4, 10); g.drawRect(x + 1, y - 58, 4, 13);
  }
  g.endFill();

  // ==========================================
  // CLUTTER
  // ==========================================
  // Keyboard
  g.beginFill(0xE0E0E0); g.lineStyle(1, 0x333333);
  g.drawRect(x - 25, y - 25, 30, 10);
  g.beginFill(0xCCCCCC); g.lineStyle(0);
  g.drawRect(x - 22, y - 23, 24, 2); g.drawRect(x - 22, y - 19, 24, 2); // keys
  g.endFill();

  // Mouse & Pad
  g.beginFill(0x333333); g.lineStyle(1, 0x111111);
  g.drawRect(x + 10, y - 27, 12, 12); // mousepad
  g.beginFill(0xAAAAAA); g.drawRect(x + 13, y - 24, 6, 8); // mouse
  g.endFill();

  // Coffee Mug
  g.beginFill(0xFFFFFF); g.lineStyle(1, 0x333333);
  g.drawRect(x - 45, y - 25, 10, 12); // mug
  g.beginFill(0x4B3621); g.lineStyle(0);
  g.drawRect(x - 43, y - 25, 6, 3); // coffee liquid
  g.endFill();

  // Documents
  g.beginFill(0xFFFFFF); g.lineStyle(1, 0x333333);
  g.drawRect(x + 35, y - 30, 20, 25);
  if (isBuyer) g.drawRect(x + 32, y - 28, 20, 25);
  // Text lines
  g.beginFill(0x999999); g.lineStyle(0);
  g.drawRect(x + 37, y - 25, 14, 2); g.drawRect(x + 37, y - 20, 10, 2); g.drawRect(x + 37, y - 15, 16, 2);
  g.endFill();

  // Calculator or Phone
  g.beginFill(0x444444); g.lineStyle(1, 0x111111);
  g.drawRect(x - 55, y - 10, 12, 18);
  g.beginFill(0x88FF88); g.lineStyle(0); g.drawRect(x - 53, y - 8, 8, 4); // screen
  g.endFill();

  // Small Desk Plant
  g.beginFill(0x8B4513); g.lineStyle(1, 0x111111); g.drawRect(x + 40, y - 45, 10, 8); // pot
  g.beginFill(0x228B22); g.lineStyle(1, 0x006400); g.drawCircle(x + 45, y - 50, 6); g.drawCircle(x + 41, y - 48, 4); // leaves
  g.endFill();

  // ==========================================
  // STICKY NOTES (Easter Eggs)
  // ==========================================
  const noteX = isBuyer ? x - 85 : x - 75;
  const noteY = y - 35;
  g.beginFill(0xFFEA00); g.lineStyle(1, 0xDDCC00); // Yellow note
  g.drawRect(noteX, noteY, 20, 20);
  g.beginFill(0x333333); g.lineStyle(0);
  g.drawRect(noteX + 3, noteY + 4, 10, 2);
  g.drawRect(noteX + 3, noteY + 9, 14, 2);
  g.drawRect(noteX + 3, noteY + 14, 8, 2);
  g.endFill();

  // Nameplate (Front of desk)
  g.beginFill(0x222222); g.lineStyle(1, 0x111111);
  g.drawRect(x - 30, y + 2, 60, 14);
  g.beginFill(0xFFFFFF); g.lineStyle(0);
  g.drawRect(x - 20, y + 7, 40, 4);
  g.endFill();
}
