import * as PIXI from 'pixi.js';

export function createPolicyCore(container: PIXI.Container, x: number, y: number) {
  const g = new PIXI.Graphics();
  container.addChild(g);

  // Server Rack Shadow
  g.beginFill(0x000000, 0.2);
  g.drawRect(x - 45, y - 10, 90, 80);
  g.endFill();

  // Server Rack Body
  g.beginFill(0x2B2B2B); // Dark grey rack
  g.lineStyle(2, 0x1A1A1A);
  g.drawRect(x - 40, y - 50, 80, 100);
  g.endFill();

  // Server Slots (Servers)
  g.lineStyle(1, 0x111111);
  for(let i=0; i<4; i++) {
    g.beginFill(0x3A3A3A);
    g.drawRect(x - 30, y - 40 + (i * 12), 60, 8);
    g.endFill();
    
    // Server status lights (static idle lights)
    g.lineStyle(0);
    g.beginFill(0x5CB85C); // Green light
    g.drawCircle(x + 20, y - 36 + (i * 12), 2);
    g.beginFill(0x5BC0DE); // Blue blinker
    g.drawCircle(x + 10, y - 36 + (i * 12), 2);
    g.endFill();
  }

  // Large Monitor / Screen on top of rack
  g.beginFill(0x1F2937); // Dark casing
  g.lineStyle(2, 0x111111);
  g.drawRect(x - 35, y + 10, 70, 30);
  g.beginFill(0x064E3B); // Dark green screen
  g.lineStyle(0);
  g.drawRect(x - 32, y + 13, 64, 24);
  g.endFill();

  // Screen Text (POLICY CORE / STATUS)
  const screenTitle = new PIXI.Text('POLICY CORE', new PIXI.TextStyle({ fontFamily: 'monospace', fontSize: 6, fill: '#34D399', fontWeight: 'bold' }));
  screenTitle.x = x - 28;
  screenTitle.y = y + 16;
  container.addChild(screenTitle);

  const screenStatus = new PIXI.Text('STATUS: ONLINE', new PIXI.TextStyle({ fontFamily: 'monospace', fontSize: 5, fill: '#10B981' }));
  screenStatus.x = x - 28;
  screenStatus.y = y + 26;
  container.addChild(screenStatus);

  // Cables running from rack
  g.lineStyle(2, 0x111111);
  g.moveTo(x + 40, y + 20);
  g.lineTo(x + 50, y + 20);
  g.lineTo(x + 50, y + 40);
  
  // A small fan vent
  g.lineStyle(1, 0x111111);
  g.moveTo(x - 20, y + 42); g.lineTo(x + 20, y + 42);
  g.moveTo(x - 20, y + 45); g.lineTo(x + 20, y + 45);
}
