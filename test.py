import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# List available models
print("🔍 Available Gemini Models:\n")

for m in genai.list_models():
    # Show only text-capable models
    if "generateContent" in m.supported_generation_methods:
        print(f"- {m.name}")
