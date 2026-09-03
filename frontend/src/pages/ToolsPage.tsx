import React, { useState } from 'react';

const TOOLS = [
  {
    name: "search_products",
    description: "Semantic search across the merchant's catalog to find items matching the buyer's query. Used when the buyer is figuring out what's available.",
    details: "The LLM generates a search query string. The LangGraph node then invokes the ProductService to query the database. It returns a list of candidate products back to the LLM context, which helps the Buyer choose a specific Product ID before starting a negotiation.",
    agent: "Buyer",
    color: "#5BC0DE"
  },
  {
    name: "get_product_inventory",
    description: "Check the exact stock levels and base price for a specific product ID. Used before making a firm offer to ensure the merchant can fulfill the order.",
    details: "The Merchant agent receives a product ID from the buyer's proposal. Before countering or accepting, it calls this tool to verify current warehouse stock levels in real-time, preventing the system from accepting deals for out-of-stock items.",
    agent: "Buyer",
    color: "#5BC0DE"
  },
  {
    name: "get_negotiation_history",
    description: "Retrieve the full chronological message log of the current negotiation. Used by both agents to analyze past offers and counteroffers and plan their next move.",
    details: "Instead of passing a massive continuous chat history in the prompt, agents can selectively call this tool to fetch the last N messages from the NegotiationMessage table to understand the flow and concessions of the current deal.",
    agent: "Both",
    color: "#9B59B6"
  },
  {
    name: "get_negotiation_status",
    description: "Check the current deterministic state of the negotiation (e.g. accepted, failed, in_progress). Used to determine if action is still needed.",
    details: "Agents use this to poll the backend state machine. If the state is TERMINAL (ACCEPTED or EXPIRED), the agent knows to STOP execution. This prevents runaway agent loops.",
    agent: "Buyer",
    color: "#5BC0DE"
  },
  {
    name: "evaluate_counteroffer",
    description: "Invoke the deterministic BuyerConstraintEngine to mathematically verify if a merchant's counteroffer fits within the buyer's strict budget limits.",
    details: "LLMs are notoriously bad at math. Instead of trusting the LLM to verify if a merchant's 14,500 INR counteroffer fits within a 15,000 INR budget, the Buyer agent passes the offer to this deterministic engine. It returns a boolean ALLOW or DENY.",
    agent: "Buyer",
    color: "#5BC0DE"
  },
  {
    name: "get_product_info",
    description: "Get detailed catalog information (SKU, description, base price, inventory) about the product currently being negotiated.",
    details: "The Merchant fetches authoritative product data directly from the catalog. This ensures the Merchant doesn't hallucinate features, warranties, or base prices while negotiating.",
    agent: "Merchant",
    color: "#D9534F"
  }
];

export default function ToolsPage() {
  const [selectedTool, setSelectedTool] = useState<typeof TOOLS[0] | null>(null);

  return (
    <div className="w-full h-full flex flex-col pt-16 font-sans relative">
      <div className="flex-1 overflow-auto custom-scrollbar p-8 pb-32">
        <div className="max-w-4xl mx-auto">
          {/* HEADER */}
          <div className="mb-10 flex flex-col gap-4">
            <h1 className="text-4xl font-black text-[#111111] uppercase tracking-tighter">
              Agentic Tools
            </h1>
            <p className="text-[#555555] text-lg font-medium leading-relaxed max-w-2xl">
              NEXORA's agents are not just glorified chatbots—they are autonomous actors equipped with specialized tools to gather context, check constraints, and execute complex logic during a negotiation. Click on a tool to see how it works under the hood.
            </p>
          </div>

          {/* TOOLS GRID */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {TOOLS.map((tool, idx) => (
              <div 
                key={idx}
                onClick={() => setSelectedTool(tool)}
                className="bg-[#FFFDF7] border-[3px] border-[#111111] p-6 shadow-[6px_6px_0_0_#111111] hover:-translate-y-1 hover:shadow-[8px_8px_0_0_#111111] transition-all flex flex-col group cursor-pointer"
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-bold text-lg font-mono text-[#111111] break-all">{tool.name}</h3>
                  <div 
                    className="px-2 py-1 border-2 border-[#333333] text-[10px] font-bold uppercase tracking-widest shadow-[2px_2px_0_0_rgba(17,17,17,1)] whitespace-nowrap"
                    style={{ backgroundColor: tool.color, color: tool.color === '#EAE8DD' ? '#333' : '#FFF' }}
                  >
                    {tool.agent}
                  </div>
                </div>
                <p className="text-[#444444] text-sm leading-relaxed mb-4 flex-1">
                  {tool.description}
                </p>
                <div className="mt-auto border-t-2 border-dashed border-[#DDDDDD] pt-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: tool.color }}></div>
                    <span className="text-xs font-bold text-[#888888] uppercase tracking-wider">Available to {tool.agent}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* HOW IT WORKS SECTION */}
          <div className="mt-16 bg-[#111111] text-[#FFFDF7] border-[3px] border-[#333333] p-8 shadow-[8px_8px_0_0_#5BC0DE]">
            <h2 className="text-2xl font-black uppercase tracking-tight mb-4 text-[#5BC0DE]">
              How it works
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="flex flex-col gap-2">
                <div className="text-4xl font-black text-[#333333] font-pixel">01</div>
                <h4 className="font-bold uppercase tracking-widest text-sm text-[#F0AD4E]">Reasoning</h4>
                <p className="text-sm text-[#AAAAAA] leading-relaxed">
                  The LLM analyzes the current state of the negotiation and decides if it needs more information before making a move.
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <div className="text-4xl font-black text-[#333333] font-pixel">02</div>
                <h4 className="font-bold uppercase tracking-widest text-sm text-[#F0AD4E]">Invocation</h4>
                <p className="text-sm text-[#AAAAAA] leading-relaxed">
                  Instead of generating a text response, the LLM outputs a structured tool call. LangGraph pauses execution and invokes the deterministic function.
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <div className="text-4xl font-black text-[#333333] font-pixel">03</div>
                <h4 className="font-bold uppercase tracking-widest text-sm text-[#F0AD4E]">Adaptation</h4>
                <p className="text-sm text-[#AAAAAA] leading-relaxed">
                  The tool results are fed back into the LLM's context, allowing the agent to adapt its strategy based on real-time data or constraint failures.
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* MODAL */}
      {selectedTool && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={() => setSelectedTool(null)}>
          <div 
            className="bg-[#FFFDF7] border-[3px] border-[#111111] p-8 shadow-[12px_12px_0_0_#111111] max-w-2xl w-full"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-6">
              <h2 className="text-2xl font-black font-mono text-[#111111]">{selectedTool.name}</h2>
              <button 
                onClick={() => setSelectedTool(null)}
                className="w-8 h-8 flex items-center justify-center border-2 border-[#111111] font-black hover:bg-[#111111] hover:text-white transition-colors"
              >
                ✕
              </button>
            </div>
            
            <div className="mb-6">
              <h4 className="font-bold uppercase tracking-widest text-xs text-[#888] mb-2">Primary Use</h4>
              <p className="text-[#333] font-medium leading-relaxed">{selectedTool.description}</p>
            </div>
            
            <div className="mb-8 p-4 border-2 border-dashed border-[#111111] bg-[#111111]/5">
              <h4 className="font-bold uppercase tracking-widest text-xs text-[#111] mb-2">Under the Hood</h4>
              <p className="text-[#333] text-sm leading-relaxed">{selectedTool.details}</p>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: selectedTool.color }}></div>
              <span className="text-sm font-bold text-[#111] uppercase tracking-wider">Available to {selectedTool.agent} Agent</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
