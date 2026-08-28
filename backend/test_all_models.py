import asyncio
import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

from langchain_google_genai import ChatGoogleGenerativeAI
from app.agents.buyer.schemas import BuyerAgentAction

async def main():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
    models = [m.get("name").replace("models/", "") for m in data.get("models", []) 
              if "generateContent" in m.get("supportedGenerationMethods", []) 
              and ("flash" in m.get("name").lower() or "pro" in m.get("name").lower())]
    
    print(f"Testing {len(models)} flash/pro models to find a working one...\n")
    
    for m in models:
        print(f"--- Testing {m} ---")
        llm = ChatGoogleGenerativeAI(model=m, api_key=api_key, max_retries=0, timeout=10.0)
        
        try:
            # 1. Test basic text
            res = await llm.ainvoke("Respond with: OK")
            print(f"  [+] Plain text OK: {res.content}")
            
            # 2. Test structured output (which LangGraph uses)
            structured_llm = llm.with_structured_output(BuyerAgentAction)
            res2 = await structured_llm.ainvoke("SEARCH_PRODUCTS")
            print(f"  [+] Structured output OK: {res2.action.value}")
            
            print(f"\n✅ SUCCESS! Use this model in .env: GEMINI_MODEL={m}")
            return
            
        except Exception as e:
            print(f"  [-] Failed: {str(e)[:100]}")
            
    print("\n❌ All flash models failed on this API key.")

if __name__ == "__main__":
    asyncio.run(main())
