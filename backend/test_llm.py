import asyncio
import time
from app.llm import get_llm
from app.agents.buyer.schemas import BuyerAgentAction

async def main():
    print("Initializing LLM...")
    llm = get_llm()
    print(f"Model configured as: {llm.model}")
    
    print("\n--- TEST 1: MINIMAL PLAIN-TEXT CALL ---")
    start = time.time()
    try:
        response = await llm.ainvoke("Respond with exactly: OK")
        elapsed = time.time() - start
        print(f"Success! Time taken: {elapsed:.2f} seconds")
        print(f"Response: {response.content}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Failed! Time taken: {elapsed:.2f} seconds")
        print(f"Error: {e}")
        return

    print("\n--- TEST 2: MINIMAL STRUCTURED OUTPUT CALL ---")
    start = time.time()
    try:
        structured_llm = llm.with_structured_output(BuyerAgentAction)
        response = await structured_llm.ainvoke("The user wants a laptop. What is the action you should take? (Hint: SEARCH_PRODUCTS)")
        elapsed = time.time() - start
        print(f"Success! Time taken: {elapsed:.2f} seconds")
        print(f"Parsed Action: {response.action.value}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Failed! Time taken: {elapsed:.2f} seconds")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
