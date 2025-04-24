import requests

def ask_ollama(messages, ollama_url):
    payload = {
        "model": "llama3",
        "messages": messages,
        "stream": False
    }
    try:
        resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if 'message' in data:
            return data['message'].get('content', 'No response from Ollama.')
        elif 'messages' in data and data['messages']:
            return data['messages'][-1].get('content', 'No response from Ollama.')
        return data.get("response", "No response from Ollama.")
    except Exception as e:
        return f"Error contacting Ollama: {e}"
