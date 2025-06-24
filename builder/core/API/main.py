# main.py
# ARCHITECT-Generated Secure API Bridge for Gemini Integration
# v1.0

import os
import uvicorn
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Load environment variables from a .env file for security
load_dotenv()

# Retrieve the Gemini API key from environment variables.
# This is a critical security measure. The script will fail if the key is not set.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL FAILURE: GEMINI_API_KEY environment variable not found.")

genai.configure(api_key=GEMINI_API_KEY)

# Simple bearer token for securing your bridge service itself.
# Claude will need to send this token in its request headers.
BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY")
if not BRIDGE_API_KEY:
    print("WARNING: BRIDGE_API_KEY not set. The bridge endpoint is unprotected.")

# --- API DEFINITION ---
app = FastAPI(title="ARCHITECT Gemini Bridge", version="1.0")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Pydantic models for structured, validated request/response data
class GeminiRequest(BaseModel):
    prompt: str

class GeminiResponse(BaseModel):
    response_text: str

# --- SECURITY FUNCTION ---
async def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validates the bearer token sent from Claude to this bridge."""
    if not BRIDGE_API_KEY: # Allow unprotected access if no key is set
        return True
    if api_key_header == BRIDGE_API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Forbidden: Could not validate credentials")

# --- API ENDPOINT ---
@app.post("/invoke_gemini", response_model=GeminiResponse, dependencies=[Security(get_api_key)])
async def invoke_gemini_model(request: GeminiRequest):
    """
    Receives a prompt, sends it to the Gemini 1.5 Pro model,
    and returns the generated text.
    """
    print(f"[INFO] Received prompt: '{request.prompt[:50]}...'")
    try:
        # Initialize the Gemini model
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Generate content
        response = await model.generate_content_async(request.prompt)

        # Robustly handle the response object
        if response.parts:
            response_text = response.text
        else:
            # Handle cases where the model refuses to answer (e.g., safety blocks)
            print("[WARN] Gemini response contained no valid parts.")
            response_text = "Error: Model returned no valid content, possibly due to safety settings or an empty prompt."

        print(f"[INFO] Returning response: '{response_text[:50]}...'")
        return {"response_text": response_text}

    except Exception as e:
        print(f"[ERROR] An exception occurred while invoking Gemini: {e}")
        # Do not expose detailed internal errors to the client.
        raise HTTPException(status_code=500, detail="Internal Server Error: Failed to process request with Gemini API.")

# --- FOR LOCAL TESTING ---
if __name__ == "__main__":
    print("--- ARCHITECT Gemini Bridge Local Test Server ---")
    print("Starting server on http://127.0.0.1:8000")
    print("Ensure GEMINI_API_KEY is set in your environment.")
    uvicorn.run(app, host="0.0.0.0", port=8000)
