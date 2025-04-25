import re
import requests

def ask_ollama(messages, ollama_url):
    payload = {
        "model": "llama3",
        "messages": messages,
        "stream": False
    }
    try:
        resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        if 'message' in data:
            content = data['message'].get('content', 'No response from the llama.')
        elif 'messages' in data and data['messages']:
            content = data['messages'][-1].get('content', 'No response from the llama.')
        else:
            content = data.get("response", "No response from the llama.")
        # Remove <think>...</think> or leading <think> tags
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = re.sub(r'^<think>.*', '', content, flags=re.DOTALL)
        return content.strip()
    except Exception as e:
        return f"Error contacting the llama: {e}"
