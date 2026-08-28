import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("NO API KEY FOUND")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
    print("\n--- AVAILABLE MODELS ---")
    for model in data.get("models", []):
        if "generateContent" in model.get("supportedGenerationMethods", []):
            print(f"- {model.get('name').replace('models/', '')}")
            
except urllib.error.HTTPError as e:
    print(f"API Error: {e.code} - {e.read().decode()}")
except Exception as e:
    print(f"Error: {str(e)}")
