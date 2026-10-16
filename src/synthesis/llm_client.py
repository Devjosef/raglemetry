import os
import json
import urllib.request
import urllib.error
from typing import Optional

# Raglemetry's default local fallback model if OLLAMA_MODEL is unset
DEFAULT_OLLAMA_MODEL = "mistral"
DEFAULT_OLLAMA_HOST = "http://localhost:11434/api/generate"

def _invoke_ollama(prompt: str, model: str, host: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0}
    }
    
    req = urllib.request.Request(
        host,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        # This is a strict timeout so a stalled local model doesn't hang the CLI infinitely
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "Error: Empty response structure from Ollama.")
    except urllib.error.URLError as e:
        return f"Local LLM Execution Failed (Is Ollama running at {host}?): {e.reason}"
    except Exception as e:
        return f"Local LLM Execution Failed: {str(e)}"

def invoke_llm_synthesis(prompt: str) -> str:
    
    # Pluggable LLM call supporting local runtimes (Ollama is set as default) 
    # or use env-configured fallbacks.
    
    provider = os.getenv("RAGLEMETRY_LLM_PROVIDER", "ollama").lower()
    
    if provider == "ollama":
        model_name = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        return _invoke_ollama(prompt, model_name, host)
        
    elif provider in ("openai", "deepseek"):
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            return f"Error: Missing LLM_API_KEY for cloud provider '{provider}'."
        return f"Error: Cloud fallback for '{provider}' is disabled in local offline mode."
            
    return f"Error: Unsupported LLM provider '{provider}'."