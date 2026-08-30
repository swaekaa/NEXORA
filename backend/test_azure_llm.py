import sys
import os
import asyncio
from dotenv import load_dotenv

# Ensure we can import app modules
sys.path.append(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from app.llm import get_llm
from app.agents.buyer.schemas import BuyerAgentAction

async def main():
    print("Testing Azure OpenAI Connection...")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    print(f"DEBUG: Using AZURE_OPENAI_ENDPOINT from .env: '{endpoint}'")
    
    if not endpoint.endswith("/openai/v1") and not endpoint.endswith("/v1"):
        print("\nWARNING: Your AZURE_OPENAI_ENDPOINT does not end in '/openai/v1' or '/v1'.")
        print("Based on your sample code, it must end in '/openai/v1' for ChatOpenAI to route correctly!")
        print("Please add '/openai/v1' to the end of your AZURE_OPENAI_ENDPOINT in the .env file.")
        
    try:
        # Step 1: Initialize model
        llm = get_llm(temperature=0.0)
        print("\nLangChain Model instantiated successfully.")
        print(f"LangChain Base URL: {llm.model_dump().get('openai_api_base')}")
        
        # Step 2: Test Structured Output
        print("\nTesting structured output generation (BuyerAgentAction)...")
        structured_llm = llm.with_structured_output(BuyerAgentAction)
        
        response = await structured_llm.ainvoke(
            "Take the STOP action because the negotiation is over. Provide a short reason."
        )
        print("\nStructured Response Received:")
        print(response.model_dump_json(indent=2))
        
        print("\nSUCCESS: Azure OpenAI structured output is working perfectly!")
    except Exception as e:
        print("\nERROR during Azure OpenAI invocation:")
        print(str(e))

if __name__ == "__main__":
    asyncio.run(main())
