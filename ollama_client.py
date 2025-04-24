import requests

def ask_ollama(message, ollama_url):
    payload = {"prompt": message}
    try:
        resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "No response from Ollama.")
    except Exception as e:
        return f"Error contacting Ollama: {e}"
