import React, { useEffect, useState } from 'react';

interface PixelSpeechBubbleProps {
  agent: "buyer" | "merchant";
  message: string;
  visible: boolean;
}

export const PixelSpeechBubble: React.FC<PixelSpeechBubbleProps> = ({ agent, message, visible }) => {
  const [shouldRender, setShouldRender] = useState(visible);

  useEffect(() => {
    if (visible) setShouldRender(true);
  }, [visible]);

  const handleAnimationEnd = () => {
    if (!visible) setShouldRender(false);
  };

  if (!shouldRender) return null;

  // Determine alignment and colors
  const isBuyer = agent === 'buyer';
  
  // The canvas game world is strictly centered in the screen.
  // At 1.25x scale: 50 * 1.25 = 62px. 120 * 1.25 = 150px.
  const style: React.CSSProperties = {
    position: 'absolute',
    left: isBuyer ? 'calc(50% - 62px)' : 'calc(50% + 62px)',
    top: 'calc(50% + 150px)',
    transform: 'translate(-50%, 0)', // Position BELOW the anchor point
    zIndex: 20,
    width: '450px', // Much wider to fit all text without scrolling
  };

  const agentName = isBuyer ? "BUYER AGENT" : "MERCHANT AGENT";
  const agentColor = isBuyer ? "text-[#5BC0DE]" : "text-[#D9534F]";
  const tailAlignment = isBuyer ? "left-[60%]" : "left-[40%]";

  return (
    <div 
      style={style} 
      className={`transition-all duration-300 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'}`}
      onTransitionEnd={handleAnimationEnd}
    >
      <div className="bg-[#FFFDF7] border-[3px] border-[#111111] shadow-[6px_6px_0_0_rgba(17,17,17,1)] relative p-0">
        
        {/* Tail pointing UP (since bubble is below agent) */}
        <div className={`absolute -top-[12px] ${tailAlignment} -translate-x-1/2 w-0 h-0 border-l-[10px] border-l-transparent border-r-[10px] border-r-transparent border-b-[12px] border-b-[#111111]`}></div>
        <div className={`absolute -top-[8px] ${tailAlignment} -translate-x-1/2 w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-b-[10px] border-b-[#FFFDF7]`}></div>

        {/* Header */}
        <div className="bg-[#111111] px-3 py-1 flex items-center justify-between">
           <span className={`${agentColor} font-bold text-[10px] uppercase tracking-widest`}>{agentName}</span>
           <div className="flex gap-1">
             <div className="w-2 h-2 bg-[#D9534F] border border-[#111111]"></div>
             <div className="w-2 h-2 bg-[#F0AD4E] border border-[#111111]"></div>
             <div className="w-2 h-2 bg-[#5CB85C] border border-[#111111]"></div>
           </div>
        </div>

        {/* Content (Removed max-height and scrolling to show full text) */}
        <div className="p-4 text-[#333333] font-mono text-xs leading-relaxed break-words">
          {message}
        </div>
      </div>
    </div>
  );
};
